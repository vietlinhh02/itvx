"use client"

import { useState } from "react"

import { CollapsibleSection } from "@/components/interview/live-room/live-room-shell-parts"
import { formatLabel } from "@/components/interview/live-room/live-room-utils"
import type { InterviewSessionDetailResponse } from "@/components/interview/interview-types"
import { usePageScrollRestore } from "@/hooks/use-persisted-ui-state"
import { resolveApiBaseUrl } from "@/lib/api"

export function InterviewSessionDetail({
  initialSession,
  accessToken,
  backendBaseUrl,
}: {
  initialSession: InterviewSessionDetailResponse
  accessToken: string
  backendBaseUrl: string
}) {
  const [session, setSession] = useState(initialSession)
  const [answerText, setAnswerText] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const apiBaseUrl = resolveApiBaseUrl(backendBaseUrl)
  usePageScrollRestore(`interviewx:interview-session-detail:${initialSession.session_id}:scroll-y`)

  const planQuestions = session.plan?.questions ?? []
  const planCompetencies = session.plan?.competencies ?? []
  const planEvents = session.plan?.plan_events ?? []
  const nextQuestion = planQuestions[session.current_question_index] ?? null
  const goalLabel = session.plan?.session_goal.vi ?? session.plan?.session_goal.en ?? "Phiên phỏng vấn"
  const nextIntendedStep = session.plan?.next_intended_step?.vi ?? session.plan?.next_intended_step?.en ?? null
  const decisionStatus = session.plan?.interview_decision_status ?? "continue"

  async function handleSubmit() {
    if (!answerText.trim()) {
      setError("Vui lòng nhập câu trả lời của ứng viên trước khi tiếp tục.")
      return
    }

    setIsSubmitting(true)
    setError(null)
    try {
      const response = await fetch(`${apiBaseUrl}/interviews/${session.session_id}/answer`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ answer_text: answerText }),
      })
      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as { detail?: string } | null
        setError(payload?.detail ?? "Không thể gửi câu trả lời của ứng viên.")
        return
      }

      const detailResponse = await fetch(`${apiBaseUrl}/interviews/${session.session_id}`, {
        headers: { Authorization: `Bearer ${accessToken}` },
        cache: "no-store",
      })
      if (!detailResponse.ok) {
        setError("Không thể làm mới phiên phỏng vấn.")
        return
      }
      const nextSession = (await detailResponse.json()) as InterviewSessionDetailResponse
      setSession(nextSession)
      setAnswerText("")
    } catch {
      setError("Không thể kết nối tới backend. Hãy kiểm tra URL API rồi thử lại.")
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <main className="flex w-full flex-col gap-6 py-6">
      <section className="rounded-[24px] bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
        <p className="text-sm font-medium text-[var(--color-brand-text-muted)]">Phiên phỏng vấn</p>
        <h1 className="mt-2 text-3xl font-semibold text-[var(--color-brand-text-primary)]">{goalLabel}</h1>
        <p className="mt-2 text-sm text-[var(--color-brand-text-body)]">
          Trạng thái: {session.status} · Câu hỏi {Math.min(session.current_question_index + 1, Math.max(session.total_questions, 1))} / {session.total_questions}
        </p>
        {session.recommendation ? (
          <p className="mt-2 text-sm text-[var(--color-brand-text-body)]">Khuyến nghị: {session.recommendation}</p>
        ) : null}
      </section>

      {session.plan ? (
        <section className="rounded-[24px] bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
          <h2 className="text-xl font-semibold text-[var(--color-brand-text-primary)]">Tổng quan kế hoạch</h2>
          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <article className="rounded-[16px] border border-[var(--color-brand-input-border)] p-4">
              <p className="text-xs text-[var(--color-brand-text-muted)]">Mục tiêu</p>
              <p className="mt-2 text-sm font-medium text-[var(--color-brand-text-primary)]">{session.plan.session_goal.vi ?? session.plan.session_goal.en}</p>
              {session.plan.overall_strategy ? (
                <p className="mt-2 text-sm text-[var(--color-brand-text-body)]">{session.plan.overall_strategy.vi ?? session.plan.overall_strategy.en}</p>
              ) : null}
            </article>
            <article className="rounded-[16px] border border-[var(--color-brand-input-border)] p-4">
              <p className="text-xs text-[var(--color-brand-text-muted)]">Thực thi</p>
              <p className="mt-2 text-sm text-[var(--color-brand-text-body)]">
                Giai đoạn: {formatLabel(session.plan.current_phase ?? "planned")}
              </p>
              <p className="mt-1 text-sm text-[var(--color-brand-text-body)]">
                Năng lực: {planCompetencies.length} · Câu hỏi: {planQuestions.length}
              </p>
              <p className="mt-1 text-sm text-[var(--color-brand-text-body)]">Quyết định: {formatLabel(decisionStatus)}</p>
              {nextIntendedStep ? (
                <p className="mt-2 text-sm text-[var(--color-brand-text-body)]">Bước tiếp theo: {nextIntendedStep}</p>
              ) : null}
              {session.plan.question_selection_policy ? (
                <p className="mt-2 text-sm text-[var(--color-brand-text-body)]">
                  {session.plan.question_selection_policy.vi ?? session.plan.question_selection_policy.en}
                </p>
              ) : null}
            </article>
          </div>

          {planCompetencies.length ? (
            <div className="mt-6">
              <CollapsibleSection
                title="Ưu tiên năng lực"
                persistKey={`interviewx:interview-session-detail:${session.session_id}:competencies`}
              >
                <ul className="mt-1 space-y-3">
                  {planCompetencies.map((competency) => (
                    <li key={`${competency.name.en}-${competency.priority}`} className="rounded-[16px] border border-[var(--color-brand-input-border)] p-4">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">{competency.name.vi ?? competency.name.en}</p>
                        <span className="rounded-full bg-[var(--color-primary-50)] px-3 py-1 text-xs font-semibold text-[var(--color-brand-primary)]">
                          Ưu tiên {competency.priority}
                        </span>
                      </div>
                      <p className="mt-2 text-sm text-[var(--color-brand-text-body)]">
                        Câu hỏi mục tiêu: {competency.target_question_count} · Độ phủ: {Math.round(competency.current_coverage * 100)}% · Trạng thái: {formatLabel(competency.status ?? "not_started")}
                      </p>
                      <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-[var(--color-primary-50)]">
                        <div
                          className="h-full rounded-full bg-[var(--color-brand-primary)]"
                          style={{ width: `${Math.round(competency.current_coverage * 100)}%` }}
                        />
                      </div>
                      <p className="mt-2 text-sm text-[var(--color-brand-text-body)]">
                        Số bằng chứng đã thu: {competency.evidence_collected_count ?? 0}
                      </p>
                      {competency.evidence_needed.length ? (
                        <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-[var(--color-brand-text-body)]">
                          {competency.evidence_needed.map((evidence) => (
                            <li key={evidence.en}>{evidence.vi ?? evidence.en}</li>
                          ))}
                        </ul>
                      ) : null}
                      {competency.stop_condition ? (
                        <p className="mt-2 text-sm text-[var(--color-brand-text-body)]">Điều kiện dừng: {competency.stop_condition.vi ?? competency.stop_condition.en}</p>
                      ) : null}
                    </li>
                  ))}
                </ul>
              </CollapsibleSection>
            </div>
          ) : null}

          {planQuestions.length ? (
            <div className="mt-6">
              <CollapsibleSection
                title="Kế hoạch câu hỏi"
                persistKey={`interviewx:interview-session-detail:${session.session_id}:questions`}
              >
              <ul className="mt-1 space-y-3">
                {planQuestions.map((question, index) => (
                  <li
                    key={question.question_index}
                    className={`rounded-[16px] border p-4 ${
                      index === session.current_question_index
                        ? "border-[var(--color-brand-primary)] bg-[var(--color-primary-50)]"
                        : "border-[var(--color-brand-input-border)]"
                    }`}
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-[var(--color-brand-primary)]">
                        Q{question.question_index + 1}
                      </span>
                      {question.source ? (
                        <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-[var(--color-brand-text-muted)]">
                          {formatLabel(question.source)}
                        </span>
                      ) : null}
                      {question.question_type ? (
                        <span
                          className={`rounded-full px-3 py-1 text-xs font-semibold ${
                            question.question_type === "recovery"
                              ? "bg-amber-100 text-amber-800"
                              : question.question_type === "clarification"
                                ? "bg-sky-100 text-sky-800"
                                : "bg-white text-[var(--color-brand-text-muted)]"
                          }`}
                        >
                          {formatLabel(question.question_type)}
                        </span>
                      ) : null}
                    </div>
                    <p className="mt-3 text-xs text-[var(--color-brand-text-muted)]">
                      {question.dimension_name.vi ?? question.dimension_name.en}
                    </p>
                    <p className="mt-2 text-sm font-medium text-[var(--color-brand-text-primary)]">{question.prompt.vi ?? question.prompt.en}</p>
                    <p className="mt-1 text-sm text-[var(--color-brand-text-body)]">{question.purpose.vi ?? question.purpose.en}</p>
                    {question.selection_reason ? (
                      <p className="mt-2 text-sm text-[var(--color-brand-text-body)]">Lý do hỏi lúc này: {question.selection_reason.vi ?? question.selection_reason.en}</p>
                    ) : null}
                    {question.evidence_gap ? (
                      <p className="mt-1 text-sm text-[var(--color-brand-text-body)]">Khoảng trống bằng chứng: {question.evidence_gap.vi ?? question.evidence_gap.en}</p>
                    ) : null}
                    {question.rationale ? <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">Lý giải: {question.rationale}</p> : null}
                  </li>
                ))}
              </ul>
              </CollapsibleSection>
            </div>
          ) : null}

          {planEvents.length ? (
            <div className="mt-6">
              <CollapsibleSection
                title="Quyết định của agent"
                persistKey={`interviewx:interview-session-detail:${session.session_id}:agent-decisions`}
              >
              <p className="mt-1 text-sm text-[var(--color-brand-text-body)]">
                Các sự kiện này giải thích kế hoạch phỏng vấn đã thay đổi ra sao và vì sao agent chọn hành động tiếp theo.
              </p>
              <ul className="mt-4 space-y-3">
                {planEvents.map((event, index) => (
                  <li key={`${event.event_type}-${event.created_at}-${index}`} className="rounded-[16px] border border-[var(--color-brand-input-border)] p-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">{formatLabel(event.event_type)}</p>
                      <span className="text-xs text-[var(--color-brand-text-muted)]">{event.created_at}</span>
                    </div>
                    <p className="mt-2 text-sm text-[var(--color-brand-text-body)]">{event.reason.vi ?? event.reason.en}</p>
                    <p className="mt-1 text-sm text-[var(--color-brand-text-body)]">Hành động: {formatLabel(event.chosen_action)}</p>
                    {event.confidence != null ? (
                      <p className="mt-1 text-sm text-[var(--color-brand-text-body)]">Độ tin cậy: {Math.round(event.confidence * 100)}%</p>
                    ) : null}
                    {event.decision_rule ? (
                      <p className="mt-1 text-sm text-[var(--color-brand-text-body)]">Luật: {formatLabel(event.decision_rule)}</p>
                    ) : null}
                    {event.next_question_type ? (
                      <p className="mt-1 text-sm text-[var(--color-brand-text-body)]">Loại câu hỏi tiếp theo: {formatLabel(event.next_question_type)}</p>
                    ) : null}
                    {event.evidence_excerpt ? (
                      <p className="mt-1 text-sm text-[var(--color-brand-text-body)]">Bằng chứng: {event.evidence_excerpt.vi ?? event.evidence_excerpt.en}</p>
                    ) : null}
                    {event.affected_competency ? (
                      <p className="mt-1 text-sm text-[var(--color-brand-text-body)]">Năng lực: {event.affected_competency.vi ?? event.affected_competency.en}</p>
                    ) : null}
                  </li>
                ))}
              </ul>
              </CollapsibleSection>
            </div>
          ) : null}
        </section>
      ) : null}

      <section className="rounded-[24px] bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
        <h2 className="text-xl font-semibold text-[var(--color-brand-text-primary)]">Sự kiện hệ thống/runtime</h2>
        <p className="mt-2 text-sm text-[var(--color-brand-text-body)]">
          Các sự kiện này theo dõi thay đổi vòng đời vận hành như lịch hẹn, worker dispatch, trạng thái phòng và cập nhật kết nối.
        </p>
        <div className="mt-4 space-y-3">
          {session.runtime_events.length ? (
            session.runtime_events.map((event, index) => (
              <article
                key={`${event.event_type}-${event.event_source}-${index}`}
                className="rounded-[16px] border border-[var(--color-brand-input-border)] p-4"
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">{formatLabel(event.event_type)}</p>
                  <span className="rounded-full bg-[var(--color-primary-50)] px-3 py-1 text-xs font-semibold text-[var(--color-brand-primary)]">
                    {formatLabel(event.event_source)}
                  </span>
                </div>
                <p className="mt-2 text-sm text-[var(--color-brand-text-body)]">
                  Phiên {formatLabel(event.session_status ?? "unknown")} · Worker {formatLabel(event.worker_status ?? "unknown")} · Provider {formatLabel(event.provider_status ?? "unknown")}
                </p>
              </article>
            ))
          ) : (
            <p className="text-sm text-[var(--color-brand-text-body)]">Chưa có sự kiện runtime nào được ghi lại.</p>
          )}
        </div>
      </section>

      <section className="rounded-[24px] bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
        <CollapsibleSection
          title="Bản ghi"
          persistKey={`interviewx:interview-session-detail:${session.session_id}:transcript`}
        >
          <div className="mt-1 space-y-3">
            {session.transcript_turns.map((turn) => (
              <article
                key={`${turn.speaker}-${turn.sequence_number}`}
                className="rounded-[16px] border border-[var(--color-brand-input-border)] p-4"
              >
                <p className="text-xs text-[var(--color-brand-text-muted)]">{formatLabel(turn.speaker)}</p>
                <p className="mt-2 text-sm text-[var(--color-brand-text-primary)]">{turn.transcript_text}</p>
              </article>
            ))}
          </div>
        </CollapsibleSection>
      </section>

      {session.status !== "completed" && nextQuestion ? (
        <section className="rounded-[24px] bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
          <h2 className="text-xl font-semibold text-[var(--color-brand-text-primary)]">Gửi câu trả lời</h2>
          <p className="mt-2 text-sm text-[var(--color-brand-text-body)]">Câu hỏi hiện tại: {nextQuestion.prompt.vi ?? nextQuestion.prompt.en}</p>
          <textarea
            className="mt-4 min-h-32 w-full rounded-[16px] border border-[var(--color-brand-input-border)] p-4 text-sm outline-none"
            onChange={(event) => setAnswerText(event.target.value)}
            value={answerText}
          />
          <div className="mt-4 flex items-center gap-3">
            <button
              className="rounded-full bg-[var(--color-brand-primary)] px-5 py-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
              disabled={isSubmitting}
              onClick={() => void handleSubmit()}
              type="button"
            >
              {isSubmitting ? "Đang gửi..." : "Gửi câu trả lời"}
            </button>
            {error ? <p className="text-sm text-red-700">{error}</p> : null}
          </div>
        </section>
      ) : null}
    </main>
  )
}
