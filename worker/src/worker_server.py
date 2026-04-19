import asyncio
import logging
import os

from fastapi import FastAPI
from pydantic import BaseModel, Field
import uvicorn

from src.agent import SessionRuntimeHandler
from src.backend_client import BackendClient
from src.config import WorkerConfig


logger = logging.getLogger(__name__)


class DispatchSessionRequest(BaseModel):
    session_id: str = Field(min_length=1)
    room_name: str = Field(min_length=1)
    opening_question: str = Field(min_length=1)
    worker_token: str = Field(min_length=1)
    jd_id: str = Field(min_length=1)


class DispatchSessionResponse(BaseModel):
    accepted: bool
    session_id: str
    status: str


class WorkerService:
    def __init__(self, config: WorkerConfig) -> None:
        self._config = config
        self._backend = BackendClient(config.backend_base_url, config.backend_callback_secret)
        self._tasks: dict[str, asyncio.Task[None]] = {}

    async def dispatch(self, payload: DispatchSessionRequest) -> DispatchSessionResponse:
        logger.info(
            "dispatch requested for session_id=%s room_name=%s",
            payload.session_id,
            payload.room_name,
        )
        existing_task = self._tasks.get(payload.session_id)
        if existing_task is not None and not existing_task.done():
            logger.info("session_id=%s already running", payload.session_id)
            return DispatchSessionResponse(
                accepted=True,
                session_id=payload.session_id,
                status="already_running",
            )

        task = asyncio.create_task(self._run_session(payload))
        self._tasks[payload.session_id] = task
        task.add_done_callback(lambda _: self._tasks.pop(payload.session_id, None))
        logger.info("session_id=%s queued for execution", payload.session_id)
        return DispatchSessionResponse(
            accepted=True,
            session_id=payload.session_id,
            status="queued",
        )

    async def _run_session(self, payload: DispatchSessionRequest) -> None:
        logger.info(
            "starting runtime for session_id=%s room_name=%s",
            payload.session_id,
            payload.room_name,
        )
        handler = SessionRuntimeHandler(
            room_name=payload.room_name,
            opening_question=payload.opening_question,
            session_id=payload.session_id,
            jd_id=payload.jd_id,
            livekit_url=self._config.livekit_url,
            worker_token=payload.worker_token,
            backend_client=self._backend,
            config=self._config,
        )
        try:
            await handler.run()
            logger.info("runtime finished for session_id=%s", payload.session_id)
        except Exception:
            logger.exception("runtime failed for session_id=%s", payload.session_id)
            raise


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
    worker_host=os.getenv("INTERVIEW_WORKER_HOST", "127.0.0.1"),
    worker_port=int(os.getenv("INTERVIEW_WORKER_PORT", "8765")),
)
service = WorkerService(config)
app = FastAPI(title="Interview Worker Service")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/dispatch-session", response_model=DispatchSessionResponse)
async def dispatch_session(payload: DispatchSessionRequest) -> DispatchSessionResponse:
    logger.info(
        "received /dispatch-session request session_id=%s room_name=%s",
        payload.session_id,
        payload.room_name,
    )
    response = await service.dispatch(payload)
    logger.info(
        "returning /dispatch-session response session_id=%s status=%s",
        response.session_id,
        response.status,
    )
    return response


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    logger.info(
        "starting worker service host=%s port=%s livekit_url=%s backend_base_url=%s",
        config.worker_host,
        config.worker_port,
        config.livekit_url,
        config.backend_base_url,
    )
    uvicorn.run(app, host=config.worker_host, port=config.worker_port)


if __name__ == "__main__":
    main()
