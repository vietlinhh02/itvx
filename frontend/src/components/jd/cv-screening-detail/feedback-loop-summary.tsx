import type {
  InterviewFeedbackPolicyCollectionResponse,
  InterviewFeedbackResponse,
  InterviewFeedbackSummaryResponse,
  InterviewSessionDetailResponse,
} from "@/components/interview/interview-types"

type FeedbackLoopSummaryProps = {
  interviewDetail: InterviewSessionDetailResponse
  interviewFeedback: InterviewFeedbackResponse | null
  feedbackSummary: InterviewFeedbackSummaryResponse | null
  feedbackPolicy: InterviewFeedbackPolicyCollectionResponse | null
}

function formatPercent(value: number | null | undefined) {
  if (value == null) {
    return "Chưa có dữ liệu"
  }

  return `${Math.round(value * 100)}%`
}

function buildScopedListKey(scope: string, value: string, index: number) {
  return `${scope}-${index}-${value}`
}

export function FeedbackLoopSummary({
  interviewDetail,
  interviewFeedback,
  feedbackSummary,
  feedbackPolicy,
}: FeedbackLoopSummaryProps) {
  const topDelta = [...(interviewFeedback?.competencies ?? [])]
    .filter((item) => item.delta != null)
    .sort((left, right) => Math.abs(right.delta ?? 0) - Math.abs(left.delta ?? 0))[0]
  const activePolicy = feedbackPolicy?.active_policy ?? feedbackSummary?.active_policy ?? null
  const latestAuditEvent =
    feedbackPolicy?.policy_audit_trail?.[0] ?? feedbackSummary?.policy_audit_trail?.[0] ?? null
  const policySummary = interviewDetail.plan?.policy_summary ?? null
  const policyOverrides = interviewDetail.plan?.active_policy?.competency_overrides ?? []
  const planImpactSignals = (interviewDetail.plan?.competencies ?? []).flatMap((competency) =>
    competency.evidence_needed
      .filter((item) => item.en.includes("previously showed AI-HR disagreement"))
      .map((item) => ({
        competency: competency.name.vi || competency.name.en,
        evidence: item.vi || item.en,
      })),
  )

  return (
    <section className="rounded-[24px] bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
      <p className="text-sm font-medium text-[var(--color-brand-text-muted)]">Tóm tắt cho người đánh giá</p>
      <h2 className="mt-2 text-2xl font-semibold text-[var(--color-brand-text-primary)]">
        Vòng phản hồi đang cải thiện buổi phỏng vấn tiếp theo như thế nào
      </h2>
      <p className="mt-2 text-sm text-[var(--color-brand-text-body)]">
        Khu vực này nối kết buổi phỏng vấn AI đã hoàn tất, phần chỉnh sửa của HR và các thay đổi chính sách cho phiên sau.
      </p>

      <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <article className="rounded-[16px] border border-[var(--color-brand-input-border)] p-4">
          <p className="text-xs text-[var(--color-brand-text-muted)]">Khuyến nghị của AI</p>
          <p className="mt-2 text-sm font-semibold text-[var(--color-brand-text-primary)]">
            {interviewFeedback?.ai_recommendation ?? interviewDetail.recommendation ?? "Chưa có dữ liệu"}
          </p>
        </article>
        <article className="rounded-[16px] border border-[var(--color-brand-input-border)] p-4">
          <p className="text-xs text-[var(--color-brand-text-muted)]">Khuyến nghị của HR</p>
          <p className="mt-2 text-sm font-semibold text-[var(--color-brand-text-primary)]">
            {interviewFeedback?.hr_recommendation ?? "Đang chờ phản hồi từ HR"}
          </p>
        </article>
        <article className="rounded-[16px] border border-[var(--color-brand-input-border)] p-4">
          <p className="text-xs text-[var(--color-brand-text-muted)]">Mức đồng thuận</p>
          <p className="mt-2 text-sm font-semibold text-[var(--color-brand-text-primary)]">
            {formatPercent(interviewFeedback?.overall_agreement_score)}
          </p>
        </article>
        <article className="rounded-[16px] border border-[var(--color-brand-input-border)] p-4">
          <p className="text-xs text-[var(--color-brand-text-muted)]">Điểm lệch lớn nhất</p>
          <p className="mt-2 text-sm font-semibold text-[var(--color-brand-text-primary)]">
            {topDelta
              ? `${topDelta.competency_name.vi || topDelta.competency_name.en} (${formatPercent(Math.abs(topDelta.delta ?? 0))})`
              : "Chưa có dữ liệu"}
          </p>
        </article>
        <article className="rounded-[16px] border border-[var(--color-brand-input-border)] p-4">
          <p className="text-xs text-[var(--color-brand-text-muted)]">Chính sách đang áp dụng</p>
          <p className="mt-2 text-sm font-semibold text-[var(--color-brand-text-primary)]">
            {activePolicy ? `v${activePolicy.version} · ${activePolicy.status}` : "Chưa có chính sách"}
          </p>
        </article>
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-2">
        <article className="rounded-[16px] border border-[var(--color-brand-input-border)] p-4">
          <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">Bằng chứng vòng kín</p>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-[var(--color-brand-text-body)]">
            <li>
              Số phản hồi HR cho JD này: {feedbackSummary?.feedback_count ?? 0}. Tỷ lệ khớp khuyến nghị là{" "}
              {formatPercent(feedbackSummary?.recommendation_agreement_rate)}.
            </li>
            <li>
              Phiên hiện tại đang dùng policy version {interviewDetail.plan?.policy_version ?? "không có"} và trạng thái quyết định{" "}
              {interviewDetail.plan?.interview_decision_status ?? "continue"}.
            </li>
            <li>
              Số override đang áp dụng: {policyOverrides.length}. Hiệu ứng dự kiến:{" "}
              {policySummary?.expected_effects.length ?? 0}.
            </li>
            <li>Sự kiện audit mới nhất: {latestAuditEvent?.event_type ?? "Chưa có sự kiện audit"}.</li>
          </ul>
        </article>

        <article className="rounded-[16px] border border-[var(--color-brand-input-border)] p-4">
          <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">Kế hoạch tiếp theo đã đổi ra sao</p>
          <div className="mt-3 space-y-3 text-sm text-[var(--color-brand-text-body)]">
            {policySummary?.expected_effects?.length ? (
              <ul className="list-disc space-y-2 pl-5">
                {policySummary.expected_effects.map((item, index) => (
                  <li key={buildScopedListKey("expected-effect", item, index)}>{item}</li>
                ))}
              </ul>
            ) : null}
            {planImpactSignals.length ? (
              <ul className="list-disc space-y-2 pl-5">
                {planImpactSignals.slice(0, 3).map((item, index) => (
                  <li key={buildScopedListKey("plan-impact", `${item.competency}-${item.evidence}`, index)}>
                    {item.competency}: {item.evidence}
                  </li>
                ))}
              </ul>
            ) : (
              <p>Chưa thấy tín hiệu tác động lên kế hoạch. Hãy áp policy và xuất bản phiên tiếp theo để hiển thị ở đây.</p>
            )}
          </div>
        </article>
      </div>
    </section>
  )
}
