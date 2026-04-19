import asyncio
import json
import logging
import os
from collections.abc import Awaitable, Callable
from contextlib import suppress
from typing import Any

from google.genai import types as genai_types
from livekit import rtc
from livekit.agents import Agent, AgentSession, function_tool
from livekit.agents.voice import room_io
from livekit.plugins import google

from src.backend_client import BackendClient
from src.config import WorkerConfig


logger = logging.getLogger(__name__)

VIETNAMESE_LANGUAGE_CODE = "vi-VN"
INTERRUPTION_MIN_DURATION_SECONDS = 0.8
INTERRUPTION_MIN_WORDS = 2
FALSE_INTERRUPTION_TIMEOUT_SECONDS = 2.0
CONTEXT_WINDOW_TRIGGER_TOKENS = 24000
CONTEXT_WINDOW_TARGET_TOKENS = 12000
FINAL_QNA_QUESTION_MARKERS = (
    "?",
    "cho em hỏi",
    "cho tôi hỏi",
    "cho mình hỏi",
    "em muốn hỏi",
    "tôi muốn hỏi",
    "mình muốn hỏi",
    "xin hỏi",
    "could i ask",
    "can i ask",
    "what ",
    "how ",
    "why ",
    "when ",
    "where ",
)
FINAL_QNA_CLOSING_MARKERS = (
    "không còn câu hỏi",
    "không có câu hỏi",
    "không hỏi thêm",
    "hết câu hỏi",
    "hết rồi",
    "vậy thôi",
    "ổn rồi",
    "em rõ rồi",
    "em hiểu rồi",
    "ok rồi",
    "được rồi",
    "cảm ơn",
    "xin cảm ơn",
)


def required_runtime_env() -> tuple[str, ...]:
    return (
        "INTERVIEW_ROOM_NAME",
        "OPENING_QUESTION",
        "INTERVIEW_SESSION_ID",
        "LIVEKIT_WORKER_TOKEN",
    )


def build_audio_transcription_config() -> genai_types.AudioTranscriptionConfig:
    return genai_types.AudioTranscriptionConfig()


def model_supports_prompted_turns(model_name: str) -> bool:
    return "3.1" not in model_name


def normalize_transcript_text(text: str) -> str:
    return " ".join(text.casefold().split())


def is_final_qna_closing_reply(text: str) -> bool:
    normalized = normalize_transcript_text(text)
    if not normalized:
        return False
    if any(marker in normalized for marker in FINAL_QNA_QUESTION_MARKERS):
        return False
    return any(marker in normalized for marker in FINAL_QNA_CLOSING_MARKERS)


def build_realtime_model(config: WorkerConfig) -> google.realtime.RealtimeModel:
    transcription_config = build_audio_transcription_config()
    return google.realtime.RealtimeModel(
        api_key=config.gemini_api_key,
        model=config.gemini_model,
        voice=config.gemini_voice,
        language=VIETNAMESE_LANGUAGE_CODE,
        input_audio_transcription=transcription_config,
        output_audio_transcription=build_audio_transcription_config(),
        context_window_compression=genai_types.ContextWindowCompressionConfig(
            trigger_tokens=CONTEXT_WINDOW_TRIGGER_TOKENS,
            sliding_window=genai_types.SlidingWindow(target_tokens=CONTEXT_WINDOW_TARGET_TOKENS),
        ),
        thinking_config=genai_types.ThinkingConfig(include_thoughts=False),
    )


def build_turn_handling() -> dict[str, Any]:
    return {
        "interruption": {
            "enabled": True,
            "mode": "vad",
            "min_duration": INTERRUPTION_MIN_DURATION_SECONDS,
            "min_words": INTERRUPTION_MIN_WORDS,
            "resume_false_interruption": True,
            "false_interruption_timeout": FALSE_INTERRUPTION_TIMEOUT_SECONDS,
        }
    }


class TranscriptForwarder:
    def __init__(
        self,
        backend_client: BackendClient,
        session_id: str,
        on_candidate_turn: Callable[[str], Awaitable[None]] | None = None,
        on_agent_turn: Callable[[str], Awaitable[None]] | None = None,
        candidate_turn_debounce_seconds: float = 1.8,
        skip_initial_candidate_turn: bool = False,
    ) -> None:
        self._backend = backend_client
        self._session_id = session_id
        self._on_candidate_turn = on_candidate_turn
        self._on_agent_turn = on_agent_turn
        self._candidate_turn_settle_seconds = candidate_turn_debounce_seconds
        self._skip_initial_candidate_turn = skip_initial_candidate_turn
        self._sequence_number = 0
        self._seen_message_ids: set[str] = set()
        self._seen_text_keys: set[tuple[str, str]] = set()
        self._pending_candidate_turn_task: asyncio.Task[None] | None = None
        self._pending_forward_tasks: set[asyncio.Task[None]] = set()
        self._has_forwarded_agent_turn = False
        self._initial_candidate_turn_skipped = False

    def attach(self, session: AgentSession) -> None:
        def _handle(event: Any) -> None:
            task = asyncio.create_task(
                self.handle_conversation_item(getattr(event, "item", event))
            )
            self._pending_forward_tasks.add(task)
            task.add_done_callback(self._pending_forward_tasks.discard)

        def _handle_user_state_change(event: Any) -> None:
            if getattr(event, "new_state", None) == "speaking":
                self._cancel_pending_candidate_turn_trigger("user_started_speaking")

        def _handle_close(_: Any) -> None:
            self._cancel_pending_candidate_turn_trigger("session_closed")

        session.on("conversation_item_added", _handle)
        session.on("user_state_changed", _handle_user_state_change)
        session.on("close", _handle_close)

    async def handle_conversation_item(self, item: Any) -> None:
        message_id = getattr(item, "id", None)
        if message_id and message_id in self._seen_message_ids:
            logger.info("skipping duplicate transcript item id=%s", message_id)
            return

        role = getattr(item, "role", None)
        text = (getattr(item, "text_content", None) or "").strip()
        if not text:
            logger.info("ignoring conversation item without text role=%s id=%s", role, message_id)
            return

        speaker = self._map_speaker(role)
        if speaker is None:
            logger.info("ignoring conversation item with unmapped role=%s id=%s", role, message_id)
            return

        if not self._is_final_item(item):
            logger.info("ignoring non-final transcript item role=%s id=%s", role, message_id)
            return

        if (
            speaker == "candidate"
            and self._skip_initial_candidate_turn
            and not self._has_forwarded_agent_turn
            and not self._initial_candidate_turn_skipped
        ):
            self._initial_candidate_turn_skipped = True
            logger.info(
                "using first candidate transcript as session start trigger role=%s id=%s text=%r",
                role,
                message_id,
                text,
            )
            return

        text_key = (speaker, text.casefold())
        if text_key in self._seen_text_keys:
            logger.info("skipping duplicate transcript text role=%s id=%s", role, message_id)
            return

        if message_id:
            self._seen_message_ids.add(message_id)
        self._seen_text_keys.add(text_key)

        logger.info(
            "transcript item speaker=%s role=%s id=%s text=%r",
            speaker,
            role,
            message_id,
            text,
        )

        try:
            await self._backend.post_turn(
                self._session_id,
                self._backend.build_turn_payload(
                    speaker=speaker,
                    sequence_number=self._next_sequence_number(),
                    transcript_text=text,
                    provider_event_id=message_id,
                )
                | {
                    "event_payload": {
                        "item_type": getattr(item, "type", None),
                        "role": role,
                        "interrupted": bool(getattr(item, "interrupted", False)),
                        "transcript_confidence": getattr(item, "transcript_confidence", None),
                        "created_at": getattr(item, "created_at", None),
                    }
                },
            )
            if speaker == "agent":
                self._has_forwarded_agent_turn = True
            if speaker == "agent" and self._on_agent_turn is not None:
                await self._on_agent_turn(text)
            if speaker == "candidate" and self._on_candidate_turn is not None:
                self._schedule_candidate_turn_trigger(message_id, text)
        except Exception:
            logger.exception("failed to forward transcript turn id=%s role=%s", message_id, role)

    def _map_speaker(self, role: str | None) -> str | None:
        if role == "assistant":
            return "agent"
        if role == "user":
            return "candidate"
        return None

    def _is_final_item(self, item: Any) -> bool:
        if getattr(item, "type", None) != "message":
            return False
        extra = getattr(item, "extra", {}) or {}
        is_partial = bool(extra.get("is_partial") or extra.get("partial"))
        return not is_partial

    def _next_sequence_number(self) -> int:
        current = self._sequence_number
        self._sequence_number += 1
        return current

    def _schedule_candidate_turn_trigger(self, message_id: str | None, text: str) -> None:
        self._cancel_pending_candidate_turn_trigger("new_candidate_transcript")
        self._pending_candidate_turn_task = asyncio.create_task(
            self._emit_candidate_turn_if_settled(message_id, text)
        )

    def _cancel_pending_candidate_turn_trigger(self, reason: str) -> None:
        if self._pending_candidate_turn_task is None:
            return
        self._pending_candidate_turn_task.cancel()
        self._pending_candidate_turn_task = None
        logger.info("cancelled pending candidate turn trigger reason=%s", reason)

    async def _emit_candidate_turn_if_settled(self, message_id: str | None, text: str) -> None:
        try:
            await asyncio.sleep(self._candidate_turn_settle_seconds)
            if self._on_candidate_turn is not None:
                await self._on_candidate_turn(text)
        except asyncio.CancelledError:
            logger.info("candidate turn trigger cancelled id=%s", message_id)
        except Exception:
            logger.exception("failed to emit settled candidate turn id=%s", message_id)
        finally:
            if asyncio.current_task() is self._pending_candidate_turn_task:
                self._pending_candidate_turn_task = None

    async def aclose(self) -> None:
        self._cancel_pending_candidate_turn_trigger("forwarder_closed")
        while self._pending_forward_tasks:
            pending = tuple(self._pending_forward_tasks)
            await asyncio.gather(*pending, return_exceptions=True)


class SessionRuntimeController:
    def __init__(self, backend_client: BackendClient, session_id: str, room_name: str) -> None:
        self._backend = backend_client
        self._session_id = session_id
        self._room_name = room_name
        self._completed = False

    async def mark_connected(self) -> None:
        logger.info("posting runtime event worker.connected room_name=%s", self._room_name)
        await self._backend.post_runtime_event(
            self._session_id,
            self._backend.build_runtime_event_payload(
                event_type="worker.connected",
                event_source="worker",
                session_status="in_progress",
                worker_status="room_connected",
                provider_status="livekit_connected",
                payload={"room_name": self._room_name},
            ),
        )

    async def mark_agent_session_started(self) -> None:
        logger.info("posting runtime event agent.session_started room_name=%s", self._room_name)
        await self._backend.post_runtime_event(
            self._session_id,
            self._backend.build_runtime_event_payload(
                event_type="agent.session_started",
                event_source="worker",
                session_status="in_progress",
                worker_status="responding",
                provider_status="gemini_live",
                payload={"room_name": self._room_name},
            ),
        )

    async def handle_candidate_left(self, participant_identity: str) -> None:
        if self._completed:
            logger.info("candidate left ignored because session already completed participant=%s", participant_identity)
            return
        logger.info("posting runtime event candidate.left participant=%s", participant_identity)
        await self._backend.post_runtime_event(
            self._session_id,
            self._backend.build_runtime_event_payload(
                event_type="candidate.left",
                event_source="worker",
                session_status="reconnecting",
                worker_status="waiting_for_candidate",
                provider_status="gemini_live",
                payload={
                    "participant_identity": participant_identity,
                    "reason": "candidate_left",
                },
            ),
        )

    async def handle_failure(self, error: Exception) -> None:
        logger.exception("posting runtime event worker.failed session_id=%s", self._session_id)
        await self._backend.post_runtime_event(
            self._session_id,
            self._backend.build_runtime_event_payload(
                event_type="worker.failed",
                event_source="worker",
                session_status="failed",
                worker_status="failed",
                provider_status="failed",
                payload={"message": str(error)},
            ),
        )

    async def mark_followed_plan_question(
        self,
        *,
        question_type: str | None,
        question_index: int,
        decision_status: str | None,
    ) -> None:
        await self._backend.post_runtime_event(
            self._session_id,
            self._backend.build_runtime_event_payload(
                event_type="worker.followed_plan_question",
                event_source="worker",
                session_status="in_progress",
                worker_status="responding",
                provider_status="gemini_live",
                payload={
                    "question_type": question_type,
                    "question_index": question_index,
                    "decision_status": decision_status,
                },
            ),
        )

    async def mark_wrap_up_started(self) -> None:
        await self._backend.post_runtime_event(
            self._session_id,
            self._backend.build_runtime_event_payload(
                event_type="worker.wrap_up_started",
                event_source="worker",
                session_status="finishing",
                worker_status="responding",
                provider_status="gemini_live",
                payload={"room_name": self._room_name},
            ),
        )

    async def mark_escalated_to_hr_boundary(self) -> None:
        await self._backend.post_runtime_event(
            self._session_id,
            self._backend.build_runtime_event_payload(
                event_type="worker.escalated_to_hr_boundary",
                event_source="worker",
                session_status="finishing",
                worker_status="responding",
                provider_status="gemini_live",
                payload={"room_name": self._room_name},
            ),
        )


class InterviewRealtimeAgent(Agent):
    def __init__(
        self,
        opening_question: str,
        llm_model: google.realtime.RealtimeModel,
        backend_client: BackendClient,
        session_id: str,
    ) -> None:
        self._supports_prompted_turns = model_supports_prompted_turns(llm_model.model)
        super().__init__(
            instructions=self._build_instructions(opening_question),
            llm=llm_model,
        )
        self._opening_question = opening_question
        self._backend = backend_client
        self._session_id = session_id
        self._final_qna_active = False
        self._final_qna_completed = False

    def _build_instructions(self, opening_question: str) -> str:
        base = (
            "Bạn là AI interviewer nói tiếng Việt. "
            "Phỏng vấn ngắn gọn, lịch sự, hỏi từng ý một, chờ ứng viên nói xong rồi mới tiếp tục. "
            "Nếu ứng viên hỏi về công ty, team, benefits, policy, process hoặc sản phẩm, "
            "hãy gọi tool lấy tài liệu nội bộ trước khi trả lời. "
            "Chỉ trả lời theo tài liệu đã truy xuất, trả lời ngắn gọn và nêu nguồn tự nhiên. "
            "Nếu tài liệu không có thông tin rõ ràng, hãy nói bạn chưa thấy thông tin đó trong tài liệu được cung cấp. "
        )
        if self._supports_prompted_turns:
            return (
                base
                + "Sau khi trả lời câu hỏi về công ty, quay lại flow phỏng vấn. "
                + f"Câu mở đầu mặc định là: {opening_question}"
            )
        return (
            base
            + "Model hiện tại không hỗ trợ cập nhật prompt giữa phiên, nên bạn phải điều phối bằng tool ngay từ đầu. "
            + "Ứng viên sẽ nói trước để bắt đầu. Ở lượt phản hồi đầu tiên của bạn, hãy chào rất ngắn gọn rồi hỏi đúng câu mở đầu này: "
            + f"{opening_question}. "
            + "Từ lượt trả lời thứ hai của ứng viên trở đi, trước khi hỏi tiếp, hãy gọi tool fetch_interview_runtime_state để lấy đúng trạng thái hiện tại. "
            + "Nếu decision_status là continue, adjust, hoặc continue_with_hr_flag và current_question_vi có giá trị, hãy hỏi đúng current_question_vi, không tự viết lại ý. "
            + "Nếu decision_status là ready_to_wrap và company_knowledge_available là true, đừng kết thúc ngay. "
            + "Hãy hỏi ứng viên xem còn muốn hỏi gì thêm về công ty, vị trí, team hoặc bất cứ điều gì khác không. "
            + "Nếu ứng viên hỏi thêm, hãy trả lời tự nhiên bằng tiếng Việt; câu nào liên quan công ty/team/benefits/policy/process/sản phẩm thì gọi lookup_company_knowledge trước khi trả lời. "
            + "Sau mỗi câu trả lời, hãy hỏi lại xem ứng viên còn muốn hỏi gì thêm không. "
            + "Chỉ gọi end_interview khi ứng viên nói rõ là không còn câu hỏi, hoặc chỉ cảm ơn/chào kết thúc mà không hỏi gì thêm. "
            + "Nếu decision_status là ready_to_wrap và needs_hr_review là false, hãy kết thúc lịch sự bằng tiếng Việt rồi gọi tool end_interview với reason='agent_wrap_up'. "
            + "Nếu decision_status là ready_to_wrap và needs_hr_review là true, hãy cảm ơn ứng viên, nói ngắn gọn rằng HR sẽ xem xét thêm sau buổi này, rồi gọi tool end_interview với reason='agent_wrap_up'. "
            + "Nếu bạn vừa trả lời câu hỏi về công ty, hãy gọi fetch_interview_runtime_state rồi quay lại flow phỏng vấn."
        )

    @function_tool()
    async def lookup_company_knowledge(self, query: str) -> str:
        """Tra cứu tài liệu công ty nội bộ để trả lời câu hỏi của ứng viên.

        Args:
            query: Câu hỏi hoặc truy vấn cần tra cứu trong tài liệu công ty.
        """
        payload = await self._backend.query_company_knowledge(self._session_id, query)
        citations = payload.get("citations", [])
        if not isinstance(citations, list) or not citations:
            return "Không tìm thấy trích dẫn phù hợp trong tài liệu công ty."

        formatted_chunks: list[str] = []
        for item in citations[:4]:
            if not isinstance(item, dict):
                continue
            file_name = str(item.get("file_name", "Unknown file"))
            section_title = item.get("section_title")
            excerpt = str(item.get("excerpt", "")).strip()
            if not excerpt:
                continue
            citation = file_name
            if isinstance(section_title, str) and section_title.strip():
                citation = f"{citation} · {section_title.strip()}"
            formatted_chunks.append(f"[{citation}] {excerpt}")
        return "\n\n".join(formatted_chunks) or "Không tìm thấy trích dẫn phù hợp trong tài liệu công ty."

    @function_tool()
    async def fetch_interview_runtime_state(self) -> str:
        """Lấy trạng thái phỏng vấn hiện tại để quyết định câu hỏi hoặc kết thúc phiên."""
        payload = await self._backend.get_runtime_state(self._session_id)
        current_question = payload.get("current_question")
        prompt_payload = current_question.get("prompt") if isinstance(current_question, dict) else None
        current_question_vi = prompt_payload.get("vi") if isinstance(prompt_payload, dict) else None
        response_payload = {
            "session_id": self._session_id,
            "status": payload.get("status"),
            "worker_status": payload.get("worker_status"),
            "provider_status": payload.get("provider_status"),
            "current_question_index": payload.get("current_question_index"),
            "decision_status": payload.get("interview_decision_status"),
            "needs_hr_review": payload.get("needs_hr_review"),
            "current_phase": payload.get("current_phase"),
            "company_knowledge_available": payload.get("company_knowledge_available"),
            "current_question_vi": current_question_vi,
            "opening_question_vi": self._opening_question,
        }
        return json.dumps(response_payload, ensure_ascii=False)

    @function_tool()
    async def end_interview(self, reason: str) -> str:
        """Kết thúc phiên phỏng vấn, lưu summary và đóng room để không thể vào lại."""
        normalized_reason = reason.strip() or "agent_wrap_up"
        await self._backend.complete_session(
            self._session_id,
            {"reason": normalized_reason},
        )
        return f"Interview session marked complete with reason={normalized_reason}."

    async def on_enter(self) -> None:
        logger.info("agent entering session")
        if not self._supports_prompted_turns:
            logger.info("waiting for candidate speech to start interview because model requires user-initiated turns")
            return
        try:
            runtime_state = await self._backend.get_runtime_state(self._session_id)
        except Exception:
            logger.exception("failed to fetch runtime state on enter; falling back to opening question")
            runtime_state = {}

        decision_status = runtime_state.get("interview_decision_status")
        needs_hr_review = bool(runtime_state.get("needs_hr_review"))
        if decision_status == "ready_to_wrap":
            if self.should_offer_final_qna(runtime_state):
                self.begin_final_qna()
                return
            self.ask_wrap_up(needs_hr_review=needs_hr_review)
            return

        current_question = runtime_state.get("current_question")
        prompt_payload = current_question.get("prompt") if isinstance(current_question, dict) else None
        current_question_vi = prompt_payload.get("vi") if isinstance(prompt_payload, dict) else None
        current_question_index = runtime_state.get("current_question_index")

        if isinstance(current_question_vi, str) and current_question_vi.strip():
            if isinstance(current_question_index, int) and current_question_index > 0:
                self.ask_follow_up(
                    current_question_vi,
                    preamble="Tiếp tục, hãy hỏi đúng câu sau bằng tiếng Việt:",
                )
                return
            self.session.generate_reply(
                instructions=(
                    "Chào ứng viên ngắn gọn bằng tiếng Việt, rồi hỏi đúng câu mở đầu sau: "
                    f"{current_question_vi}"
                ),
                input_modality="audio",
            )
            return

        self.session.generate_reply(
            instructions=(
                "Chào ứng viên ngắn gọn bằng tiếng Việt, rồi hỏi đúng câu mở đầu sau: "
                f"{self._opening_question}"
            ),
            input_modality="audio",
        )

    def ask_follow_up(self, prompt: str, *, preamble: str | None = None) -> None:
        question = prompt.strip()
        if not question:
            return
        instruction = question if preamble is None else f"{preamble} {question}"
        self.session.generate_reply(instructions=instruction, input_modality="audio")

    def should_offer_final_qna(self, runtime_state: dict[str, object]) -> bool:
        return (
            bool(runtime_state.get("company_knowledge_available"))
            and not self._final_qna_active
            and not self._final_qna_completed
        )

    def begin_final_qna(self) -> None:
        self._final_qna_active = True
        self.session.generate_reply(
            instructions=(
                "Phần đánh giá chính đã xong. Trước khi kết thúc, hãy hỏi tự nhiên bằng tiếng Việt "
                "xem ứng viên còn muốn hỏi thêm gì về công ty, vị trí, team hoặc bất cứ điều gì khác không."
            ),
            input_modality="audio",
        )

    def answer_final_qna(self) -> None:
        self._final_qna_active = True
        self.session.generate_reply(
            instructions=(
                "Bạn đang ở pha hỏi đáp cuối. Hãy trả lời trực tiếp câu hỏi vừa rồi của ứng viên "
                "một cách ngắn gọn, tự nhiên bằng tiếng Việt. Nếu câu hỏi liên quan công ty, team, "
                "benefits, policy, process hoặc sản phẩm, hãy gọi lookup_company_knowledge trước khi trả lời. "
                "Bạn có thể trả lời ngoài luồng khi phù hợp. Sau khi trả lời xong, hãy hỏi lại ứng viên "
                "xem còn muốn hỏi gì thêm không."
            ),
            input_modality="audio",
        )

    def mark_final_qna_completed(self) -> None:
        self._final_qna_active = False
        self._final_qna_completed = True

    def ask_wrap_up(self, *, needs_hr_review: bool = False) -> None:
        self.mark_final_qna_completed()
        instructions = (
            "Hãy tóm tắt ngắn gọn rằng bạn đã thu thập đủ tín hiệu chính, hỏi một câu kết nhẹ nếu cần, rồi lịch sự kết thúc buổi phỏng vấn bằng tiếng Việt."
        )
        if needs_hr_review:
            instructions = (
                "Hãy cảm ơn ứng viên, tóm tắt ngắn gọn rằng bạn đã thu thập đủ tín hiệu chính, "
                "nói tự nhiên bằng tiếng Việt rằng HR sẽ xem xét thêm sau buổi này, rồi lịch sự kết thúc buổi phỏng vấn."
            )
        self.session.generate_reply(
            instructions=instructions,
            input_modality="audio",
        )

    def ask_hr_escalation_close(self) -> None:
        self.session.generate_reply(
            instructions=(
                "Hãy nói ngắn gọn bằng tiếng Việt rằng bạn đã ghi nhận các tín hiệu cần HR xem xét thêm, cảm ơn ứng viên, và kết thúc buổi phỏng vấn một cách lịch sự."
            ),
            input_modality="audio",
        )


class SessionRuntimeHandler:
    def __init__(
        self,
        room_name: str,
        opening_question: str,
        session_id: str,
        jd_id: str,
        livekit_url: str,
        worker_token: str,
        backend_client: BackendClient,
        config: WorkerConfig,
        room: rtc.Room | None = None,
        close_backend_on_exit: bool = False,
    ) -> None:
        self._room_name = room_name
        self._opening_question = opening_question
        self._session_id = session_id
        self._jd_id = jd_id
        self._livekit_url = livekit_url
        self._worker_token = worker_token
        self._backend = backend_client
        self._config = config
        self._room = room or rtc.Room()
        self._close_backend_on_exit = close_backend_on_exit
        self._candidate_disconnect_tasks: dict[str, asyncio.Task[None]] = {}

    async def run(self) -> None:
        controller = SessionRuntimeController(
            backend_client=self._backend,
            session_id=self._session_id,
            room_name=self._room_name,
        )
        completion_fut: asyncio.Future[None] = asyncio.get_running_loop().create_future()
        active_agent: InterviewRealtimeAgent | None = None
        sync_runtime_plan_lock = asyncio.Lock()
        pending_completion_reason: str | None = None
        supports_prompted_turns = model_supports_prompted_turns(self._config.gemini_model)

        async def _complete_after_agent_closing_turn(text: str) -> None:
            nonlocal pending_completion_reason
            if pending_completion_reason is None or not text.strip():
                return
            completion_reason = pending_completion_reason
            pending_completion_reason = None
            await self._backend.complete_session(
                self._session_id,
                {"reason": completion_reason},
            )
            if not completion_fut.done():
                completion_fut.set_result(None)

        async def _sync_runtime_plan(candidate_text: str) -> None:
            nonlocal pending_completion_reason
            if active_agent is None or sync_runtime_plan_lock.locked():
                return
            async with sync_runtime_plan_lock:
                runtime_state = await self._backend.get_runtime_state(self._session_id)
                decision_status = runtime_state.get("interview_decision_status")
                needs_hr_review = bool(runtime_state.get("needs_hr_review"))
                current_question_index = runtime_state.get("current_question_index", 0)
                current_question = runtime_state.get("current_question")
                if bool(getattr(active_agent, "_final_qna_active", False)):
                    if pending_completion_reason is not None:
                        return
                    if is_final_qna_closing_reply(candidate_text):
                        pending_completion_reason = "agent_wrap_up"
                        await controller.mark_wrap_up_started()
                        active_agent.ask_wrap_up(needs_hr_review=needs_hr_review)
                        return
                    if hasattr(active_agent, "answer_final_qna"):
                        active_agent.answer_final_qna()
                    return
                if decision_status == "ready_to_wrap":
                    should_offer_final_qna = getattr(active_agent, "should_offer_final_qna", None)
                    if callable(should_offer_final_qna) and should_offer_final_qna(runtime_state):
                        active_agent.begin_final_qna()
                        return
                    if pending_completion_reason is not None:
                        return
                    pending_completion_reason = "agent_wrap_up"
                    await controller.mark_wrap_up_started()
                    active_agent.ask_wrap_up(needs_hr_review=needs_hr_review)
                    return
                if not isinstance(current_question, dict):
                    return
                prompt_payload = current_question.get("prompt")
                prompt = prompt_payload.get("vi") if isinstance(prompt_payload, dict) else None
                if not isinstance(prompt, str) or not prompt.strip():
                    return
                question_type = current_question.get("question_type")
                if question_type in {"clarification", "recovery"}:
                    preamble = "Tiếp theo, hãy hỏi đúng câu sau bằng tiếng Việt:"
                else:
                    preamble = "Tiếp theo, hãy hỏi đúng câu sau bằng tiếng Việt:"
                await controller.mark_followed_plan_question(
                    question_type=question_type if isinstance(question_type, str) else None,
                    question_index=current_question_index if isinstance(current_question_index, int) else 0,
                    decision_status=decision_status if isinstance(decision_status, str) else None,
                )
                active_agent.ask_follow_up(prompt, preamble=preamble)

        transcript_forwarder = TranscriptForwarder(
            backend_client=self._backend,
            session_id=self._session_id,
            on_candidate_turn=_sync_runtime_plan if supports_prompted_turns else None,
            on_agent_turn=_complete_after_agent_closing_turn if supports_prompted_turns else None,
            skip_initial_candidate_turn=not supports_prompted_turns,
        )

        def _cancel_pending_disconnect(identity: str) -> None:
            task = self._candidate_disconnect_tasks.pop(identity, None)
            if task is not None:
                task.cancel()
                logger.info("cancelled pending disconnect for participant=%s", identity)

        def _on_participant_connected(participant: rtc.RemoteParticipant) -> None:
            logger.info("participant connected identity=%s", participant.identity)
            _cancel_pending_disconnect(participant.identity)

        def _on_participant_disconnected(participant: rtc.RemoteParticipant) -> None:
            if participant.identity == self._room.local_participant.identity:
                return

            logger.info("participant disconnected identity=%s", participant.identity)

            async def _complete_after_grace_period() -> None:
                nonlocal pending_completion_reason
                try:
                    await asyncio.sleep(10)
                except asyncio.CancelledError:
                    logger.info(
                        "disconnect grace period cancelled for participant=%s",
                        participant.identity,
                    )
                    return

                if participant.identity in self._room.remote_participants:
                    logger.info(
                        "participant=%s reconnected before grace period expired",
                        participant.identity,
                    )
                    return

                try:
                    if pending_completion_reason is not None:
                        completion_reason = pending_completion_reason
                        pending_completion_reason = None
                        await self._backend.complete_session(
                            self._session_id,
                            {"reason": completion_reason},
                        )
                        return
                    await controller.handle_candidate_left(participant.identity)
                except Exception:
                    logger.exception(
                        "failed to complete disconnect flow for participant=%s",
                        participant.identity,
                    )
                finally:
                    if not completion_fut.done():
                        completion_fut.set_result(None)
                    self._candidate_disconnect_tasks.pop(participant.identity, None)

            _cancel_pending_disconnect(participant.identity)
            self._candidate_disconnect_tasks[participant.identity] = asyncio.create_task(
                _complete_after_grace_period()
            )

        def _on_room_disconnected(reason: object) -> None:
            logger.info(
                "room disconnected room_name=%s session_id=%s reason=%s",
                self._room_name,
                self._session_id,
                reason,
            )
            if not completion_fut.done():
                completion_fut.set_result(None)

        session: AgentSession | None = None
        try:
            logger.info(
                "connecting to livekit room_name=%s livekit_url=%s session_id=%s",
                self._room_name,
                self._livekit_url,
                self._session_id,
            )
            await self._room.connect(self._livekit_url, self._worker_token)
            logger.info(
                "connected to livekit room_name=%s local_participant=%s",
                self._room_name,
                self._room.local_participant.identity,
            )
            self._room.on("participant_connected", _on_participant_connected)
            self._room.on("participant_disconnected", _on_participant_disconnected)
            self._room.on("disconnected", _on_room_disconnected)
            await controller.mark_connected()

            realtime_model = build_realtime_model(self._config)
            session = AgentSession(
                llm=realtime_model,
                user_away_timeout=None,
                turn_handling=build_turn_handling(),
            )
            logger.info("created agent session for session_id=%s", self._session_id)
            transcript_forwarder.attach(session)
            logger.info("starting agent session for room_name=%s", self._room_name)
            active_agent = InterviewRealtimeAgent(
                self._opening_question,
                realtime_model,
                self._backend,
                self._session_id,
            )
            await session.start(
                active_agent,
                room=self._room,
                room_options=room_io.RoomOptions(
                    audio_input=True,
                    video_input=False,
                    text_input=False,
                    audio_output=True,
                    text_output=room_io.TextOutputOptions(sync_transcription=False),
                    close_on_disconnect=False,
                ),
            )
            logger.info("agent session started for room_name=%s", self._room_name)
            await controller.mark_agent_session_started()
            await completion_fut
            logger.info("completion received for session_id=%s", self._session_id)
        except Exception as exc:
            logger.exception("session runtime failed for session_id=%s", self._session_id)
            await controller.handle_failure(exc)
            raise
        finally:
            for task in self._candidate_disconnect_tasks.values():
                task.cancel()
            self._candidate_disconnect_tasks.clear()
            if session is not None:
                with suppress(Exception):
                    await session.aclose()
            with suppress(Exception):
                await transcript_forwarder.aclose()
            with suppress(Exception):
                await self._room.disconnect()
            if self._close_backend_on_exit:
                with suppress(Exception):
                    await self._backend.aclose()
            logger.info("runtime cleanup finished room_name=%s session_id=%s", self._room_name, self._session_id)


async def main() -> None:
    config = WorkerConfig(
        backend_base_url=os.getenv("BACKEND_BASE_URL", "http://localhost:8000"),
        backend_callback_secret=os.getenv("BACKEND_CALLBACK_SECRET", ""),
        gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
        gemini_model=os.getenv(
            "GEMINI_LIVE_MODEL",
            os.getenv("GEMINI_MODEL", "gemini-2.5-flash-native-audio-preview-12-2025"),
        ),
        gemini_voice=os.getenv("GEMINI_LIVE_VOICE", "Aoede"),
        livekit_url=os.getenv("LIVEKIT_URL", "wss://your-project.livekit.cloud"),
    )

    missing = [name for name in required_runtime_env() if not os.getenv(name)]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

    backend = BackendClient(config.backend_base_url, config.backend_callback_secret)
    handler = SessionRuntimeHandler(
        room_name=os.environ["INTERVIEW_ROOM_NAME"],
        opening_question=os.environ["OPENING_QUESTION"],
        session_id=os.environ["INTERVIEW_SESSION_ID"],
        jd_id=os.environ.get("JD_ID", ""),
        livekit_url=config.livekit_url,
        worker_token=os.environ["LIVEKIT_WORKER_TOKEN"],
        backend_client=backend,
        config=config,
        close_backend_on_exit=True,
    )
    await handler.run()


if __name__ == "__main__":
    asyncio.run(main())
