import type { InterviewSessionDetailResponse } from "@/components/interview/interview-types"
import {
  CollapsibleSection,
  CoverageBar,
  StatusChip,
} from "@/components/interview/live-room/live-room-shell-parts"
import { formatLabel } from "@/components/interview/live-room/live-room-utils"

export function ConversationPanel({ sessionDetail }: { sessionDetail?: InterviewSessionDetailResponse | null }) {
  const turns = sessionDetail?.transcript_turns ?? []
  const questions = sessionDetail?.plan?.questions ?? []
  const planEvents = sessionDetail?.plan?.plan_events ?? []
  const competencies = sessionDetail?.plan?.competencies ?? []
  const nextQuestion = sessionDetail?.plan?.questions?.[sessionDetail.current_question_index ?? 0] ?? null
  const nextIntendedStep = sessionDetail?.plan?.next_intended_step?.vi ?? sessionDetail?.plan?.next_intended_step?.en ?? null
  const decisionStatus = sessionDetail?.plan?.interview_decision_status ?? "continue"
  const currentQuestionIndex = sessionDetail?.current_question_index ?? 0
  const upcomingQuestions = questions.slice(currentQuestionIndex, currentQuestionIndex + 3)
  const planningRuntimeEvents = (sessionDetail?.runtime_events ?? []).filter((event) =>
    event.event_type.startsWith("planning."),
  )

  return (
    <section className="rounded-[24px] bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-[var(--color-brand-text-muted)]">Hội thoại trực tiếp</p>
          <h2 className="mt-2 text-2xl font-semibold text-[var(--color-brand-text-primary)]">Bản ghi</h2>
        </div>
        <span className="rounded-full bg-[var(--color-primary-50)] px-3 py-1 text-xs font-semibold text-[var(--color-brand-primary)]">
          {turns.length} lượt
        </span>
      </div>

      {sessionDetail ? (
        <div className="mt-5 grid gap-3 sm:grid-cols-3">
          <StatusChip label="Phiên" value={formatLabel(sessionDetail.status)} />
          <StatusChip label="Worker" value={formatLabel(sessionDetail.worker_status)} />
          <StatusChip label="Provider" value={formatLabel(sessionDetail.provider_status)} />
        </div>
      ) : null}

      {sessionDetail?.plan ? (
        <div className="mt-5 space-y-4">
          <CollapsibleSection title="Tóm tắt buổi phỏng vấn">
            <p className="text-sm font-medium text-[var(--color-brand-text-primary)]">
              {sessionDetail.plan.session_goal.vi || sessionDetail.plan.session_goal.en}
            </p>
            {sessionDetail.plan.overall_strategy ? (
              <p className="mt-2 text-sm text-[var(--color-brand-text-body)]">
                {sessionDetail.plan.overall_strategy.vi || sessionDetail.plan.overall_strategy.en}
              </p>
            ) : null}
            <div className="mt-3 flex flex-wrap gap-3">
              <StatusChip label="Giai đoạn" value={formatLabel(sessionDetail.plan.current_phase ?? "planned")} />
              <StatusChip
                label="Tiến độ"
                value={`${Math.min(sessionDetail.current_question_index + 1, Math.max(sessionDetail.total_questions, 1))}/${sessionDetail.total_questions}`}
              />
              <StatusChip label="Quyết định" value={formatLabel(decisionStatus)} />
            </div>
            {nextIntendedStep ? (
              <p className="mt-3 text-sm text-[var(--color-brand-text-body)]">Bước tiếp theo: {nextIntendedStep}</p>
            ) : null}
          </CollapsibleSection>

          {nextQuestion ? (
            <CollapsibleSection title="Vì sao chọn câu này?">
              <p className="text-sm font-medium text-[var(--color-brand-text-primary)]">
                {nextQuestion.prompt.vi || nextQuestion.prompt.en}
              </p>
              <p className="mt-2 text-sm text-[var(--color-brand-text-body)]">
                {nextQuestion.purpose.vi || nextQuestion.purpose.en}
              </p>
              <div className="mt-3 flex flex-wrap gap-3">
                {nextQuestion.source ? <StatusChip label="Nguồn" value={formatLabel(nextQuestion.source)} /> : null}
                {nextQuestion.question_type ? (
                  <StatusChip label="Loại" value={formatLabel(nextQuestion.question_type)} />
                ) : null}
              </div>
              {nextQuestion.selection_reason ? (
                <p className="mt-3 text-sm text-[var(--color-brand-text-body)]">
                  {nextQuestion.selection_reason.vi || nextQuestion.selection_reason.en}
                </p>
              ) : null}
              {nextQuestion.evidence_gap ? (
                <p className="mt-2 text-sm text-[var(--color-brand-text-body)]">
                  Khoảng trống bằng chứng: {nextQuestion.evidence_gap.vi || nextQuestion.evidence_gap.en}
                </p>
              ) : null}
            </CollapsibleSection>
          ) : null}

          {competencies.length ? (
            <CollapsibleSection title="Tiến độ bao phủ">
              <div className="space-y-3">
                {competencies.slice(0, 3).map((competency) => (
                  <article
                    key={`${competency.name.en}-${competency.priority}`}
                    className="rounded-[14px] bg-[var(--color-primary-50)]/50 p-3"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">
                        {competency.name.vi || competency.name.en}
                      </p>
                      <span className="text-xs text-[var(--color-brand-text-muted)]">
                        {formatLabel(competency.status ?? "not_started")}
                      </span>
                    </div>
                    <div className="mt-3">
                      <CoverageBar value={competency.current_coverage} />
                    </div>
                  </article>
                ))}
              </div>
            </CollapsibleSection>
          ) : null}

          {upcomingQuestions.length ? (
            <CollapsibleSection title="Kế hoạch tiếp theo">
              <div className="space-y-3">
                {upcomingQuestions.map((question, index) => (
                  <article
                    key={`${question.question_index}-${question.prompt.en}`}
                    className="rounded-[14px] bg-[var(--color-primary-50)]/50 p-3"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-xs font-semibold text-[var(--color-brand-primary)]">
                        {index === 0 ? "Hiện tại" : "Sắp tới"}
                      </span>
                      <span className="text-xs text-[var(--color-brand-text-muted)]">
                        {question.dimension_name.vi || question.dimension_name.en}
                      </span>
                    </div>
                    <p className="mt-2 text-sm text-[var(--color-brand-text-primary)]">
                      {question.prompt.vi || question.prompt.en}
                    </p>
                  </article>
                ))}
              </div>
            </CollapsibleSection>
          ) : null}

          {planEvents.length || planningRuntimeEvents.length ? (
            <CollapsibleSection title="Sự kiện từ agent và hệ thống">
              <div className="grid gap-4 lg:grid-cols-2">
                <div className="space-y-3">
                  <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">Quyết định của agent</p>
                  {planEvents.slice(-3).map((event, index) => (
                    <article
                      key={`${event.event_type}-${event.created_at}-${index}`}
                      className="rounded-[14px] bg-[var(--color-primary-50)]/50 p-3"
                    >
                      <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">
                        {formatLabel(event.event_type)}
                      </p>
                      <p className="mt-1 text-sm text-[var(--color-brand-text-body)]">
                        {event.reason.vi || event.reason.en}
                      </p>
                      <p className="mt-1 text-xs text-[var(--color-brand-text-muted)]">
                        Hành động: {formatLabel(event.chosen_action)}
                        {event.confidence != null ? ` · Độ tin cậy ${Math.round(event.confidence * 100)}%` : ""}
                      </p>
                      {event.decision_rule ? (
                        <p className="mt-1 text-xs text-[var(--color-brand-text-muted)]">
                          Luật: {formatLabel(event.decision_rule)}
                        </p>
                      ) : null}
                      {event.next_question_type ? (
                        <p className="mt-1 text-xs text-[var(--color-brand-text-muted)]">
                          Loại câu hỏi tiếp theo: {formatLabel(event.next_question_type)}
                        </p>
                      ) : null}
                      {event.evidence_excerpt ? (
                        <p className="mt-1 text-sm text-[var(--color-brand-text-body)]">
                          Bằng chứng: {event.evidence_excerpt.vi || event.evidence_excerpt.en}
                        </p>
                      ) : null}
                    </article>
                  ))}
                </div>
                <div className="space-y-3">
                  <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">Sự kiện hệ thống</p>
                  {planningRuntimeEvents.slice(-3).map((event, index) => (
                    <article
                      key={`${event.event_type}-${index}`}
                      className="rounded-[14px] bg-[var(--color-primary-50)]/50 p-3"
                    >
                      <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">
                        {formatLabel(event.event_type)}
                      </p>
                      <p className="mt-1 text-sm text-[var(--color-brand-text-body)]">
                        Giai đoạn hiện tại: {formatLabel(String(event.payload.current_phase ?? "planned"))}
                      </p>
                      <p className="mt-1 text-xs text-[var(--color-brand-text-muted)]">
                        Phiên {formatLabel(event.session_status ?? "unknown")} · Worker{" "}
                        {formatLabel(event.worker_status ?? "unknown")} · Provider{" "}
                        {formatLabel(event.provider_status ?? "unknown")}
                      </p>
                    </article>
                  ))}
                </div>
              </div>
            </CollapsibleSection>
          ) : null}
        </div>
      ) : null}

      <CollapsibleSection title="Bản ghi hội thoại">
        <div className="mt-1 space-y-3">
          {turns.length ? (
            turns.slice(-8).map((turn) => {
              const isCandidate = turn.speaker.toLowerCase().includes("candidate")

              return (
                <article
                  key={`${turn.speaker}-${turn.sequence_number}`}
                  className={`rounded-[16px] border p-4 ${
                    isCandidate
                      ? "border-[var(--color-brand-primary)] bg-[var(--color-primary-50)]"
                      : "border-[var(--color-brand-input-border)] bg-white"
                  }`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-xs font-semibold text-[var(--color-brand-text-muted)]">
                      {formatLabel(turn.speaker)}
                    </p>
                    <span className="text-xs text-[var(--color-brand-text-muted)]">#{turn.sequence_number}</span>
                  </div>
                  <p className="mt-2 text-sm text-[var(--color-brand-text-body)]">{turn.transcript_text}</p>
                </article>
              )
            })
          ) : (
            <div className="rounded-[16px] border border-dashed border-[var(--color-brand-input-border)] p-4 text-sm text-[var(--color-brand-text-muted)]">
              Bản ghi sẽ xuất hiện tại đây khi phòng bắt đầu nhận được sự kiện giọng nói.
            </div>
          )}
        </div>
      </CollapsibleSection>

      {sessionDetail?.last_error_message ? (
        <div className="mt-5 rounded-[16px] bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {sessionDetail.last_error_message}
        </div>
      ) : null}
    </section>
  )
}
