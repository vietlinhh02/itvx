import type { InterviewFeedbackSummaryResponse } from "@/components/interview/interview-types"
import { EmptyValue, ReviewSection } from "@/components/jd/cv-screening-ui"

function formatPercent(value: number) {
  return `${Math.round(value * 100)}%`
}

export function InterviewFeedbackAnalytics({
  summary,
}: {
  summary: InterviewFeedbackSummaryResponse | null
}) {
  return (
    <div id="feedback-analytics">
      <ReviewSection
        title="Phân tích phản hồi"
        description="Theo dõi mức đồng thuận AI-HR, chênh lệch điểm năng lực và các mẫu lỗi lặp lại của JD này."
      >
      {!summary ? (
        <EmptyValue text="Chưa có dữ liệu phân tích phản hồi." />
      ) : (
        <div className="space-y-6">
          <div className="grid gap-4 md:grid-cols-4">
            <article className="rounded-[16px] border border-[var(--color-brand-input-border)] p-4">
              <p className="text-xs text-[var(--color-brand-text-muted)]">Số phản hồi</p>
              <p className="mt-2 text-2xl font-semibold text-[var(--color-brand-text-primary)]">{summary.feedback_count}</p>
            </article>
            <article className="rounded-[16px] border border-[var(--color-brand-input-border)] p-4">
              <p className="text-xs text-[var(--color-brand-text-muted)]">Tỷ lệ đồng thuận</p>
              <p className="mt-2 text-2xl font-semibold text-[var(--color-brand-text-primary)]">{formatPercent(summary.agreement_rate)}</p>
            </article>
            <article className="rounded-[16px] border border-[var(--color-brand-input-border)] p-4">
              <p className="text-xs text-[var(--color-brand-text-muted)]">Khớp khuyến nghị</p>
              <p className="mt-2 text-2xl font-semibold text-[var(--color-brand-text-primary)]">{formatPercent(summary.recommendation_agreement_rate)}</p>
            </article>
            <article className="rounded-[16px] border border-[var(--color-brand-input-border)] p-4">
              <p className="text-xs text-[var(--color-brand-text-muted)]">Chênh lệch điểm trung bình</p>
              <p className="mt-2 text-2xl font-semibold text-[var(--color-brand-text-primary)]">{formatPercent(summary.average_score_delta)}</p>
            </article>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <section>
              <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">Biểu đồ chênh lệch theo năng lực</p>
              <div className="mt-3 space-y-3">
                {summary.competency_deltas.length ? (
                  summary.competency_deltas.map((item) => (
                    <article key={item.label} className="rounded-[16px] border border-[var(--color-brand-input-border)] p-4">
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-sm font-medium text-[var(--color-brand-text-primary)]">{item.label}</p>
                        <span className="text-sm font-semibold text-[var(--color-brand-primary)]">{formatPercent(item.value)}</span>
                      </div>
                      <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-[var(--color-primary-50)]">
                        <div
                          className="h-full rounded-full bg-[var(--color-brand-primary)]"
                          style={{ width: `${Math.max(6, Math.min(100, Math.round(item.value * 100)))}%` }}
                        />
                      </div>
                    </article>
                  ))
                ) : (
                  <EmptyValue text="Chưa có dữ liệu chênh lệch theo năng lực." />
                )}
              </div>
            </section>

            <section>
              <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">Lý do lỗi nổi bật</p>
              <div className="mt-3 space-y-3">
                {summary.failure_reasons.length ? (
                  summary.failure_reasons.map((item) => (
                    <article key={`${item.reason}-${item.count}`} className="rounded-[16px] border border-[var(--color-brand-input-border)] p-4">
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-sm text-[var(--color-brand-text-body)]">{item.reason}</p>
                        <span className="rounded-full bg-[var(--color-primary-50)] px-3 py-1 text-xs font-semibold text-[var(--color-brand-primary)]">
                          {item.count}
                        </span>
                      </div>
                    </article>
                  ))
                ) : (
                  <EmptyValue text="Chưa có lý do lỗi." />
                )}
              </div>
            </section>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <section>
              <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">Phân rã kết luận</p>
              <div className="mt-3 space-y-3">
                {summary.judgement_breakdown.length ? (
                  summary.judgement_breakdown.map((item) => (
                    <article key={item.label} className="rounded-[16px] border border-[var(--color-brand-input-border)] p-4">
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-sm text-[var(--color-brand-text-body)]">{item.label}</p>
                        <span className="text-sm font-semibold text-[var(--color-brand-primary)]">{item.value}</span>
                      </div>
                    </article>
                  ))
                ) : (
                  <EmptyValue text="Chưa có phân rã kết luận." />
                )}
              </div>
            </section>

            <section>
              <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">Các phiên có độ lệch cao nhất</p>
              <div className="mt-3 space-y-3">
                {summary.disagreement_sessions.length ? (
                  summary.disagreement_sessions.map((item) => (
                    <article key={item.session_id} className="rounded-[16px] border border-[var(--color-brand-input-border)] p-4">
                      <p className="text-sm font-medium text-[var(--color-brand-text-primary)]">{item.candidate_name ?? item.session_id}</p>
                      <p className="mt-1 text-sm text-[var(--color-brand-text-body)]">Đồng thuận {formatPercent(item.overall_agreement_score)} · Độ lệch {formatPercent(item.delta_magnitude)}</p>
                      <p className="mt-1 text-xs text-[var(--color-brand-text-muted)]">{item.created_at}</p>
                    </article>
                  ))
                ) : (
                  <EmptyValue text="Chưa có phiên nào có độ lệch cao." />
                )}
              </div>
            </section>
          </div>
        </div>
      )}
      </ReviewSection>
    </div>
  )
}
