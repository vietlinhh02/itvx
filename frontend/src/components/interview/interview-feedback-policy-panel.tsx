"use client"

import { useState } from "react"

import type {
  InterviewFeedbackMemoryResponse,
  InterviewFeedbackPolicyCollectionResponse,
  InterviewFeedbackPolicyResponse,
  InterviewSessionDetailResponse,
  SuggestInterviewFeedbackPolicyResponse,
} from "@/components/interview/interview-types"
import { EmptyValue, ReviewSection } from "@/components/jd/cv-screening-ui"
import { CollapsibleSection } from "@/components/interview/live-room/live-room-shell-parts"

function PolicyCard({
  title,
  policy,
}: {
  title: string
  policy: InterviewFeedbackPolicyResponse | null | undefined
}) {
  return (
    <article className="rounded-[16px] border border-[var(--color-brand-input-border)] p-4">
      <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">{title}</p>
      {!policy ? (
        <div className="mt-3">
          <EmptyValue text="Chưa có chính sách nào." />
        </div>
      ) : (
        <div className="mt-3 space-y-3">
          <div className="flex flex-wrap items-center gap-3 text-xs text-[var(--color-brand-text-muted)]">
            <span>Phiên bản {policy.version}</span>
            <span>Trạng thái {policy.status}</span>
            <span>Số phản hồi {policy.source_feedback_count}</span>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <div className="rounded-[14px] bg-[var(--color-primary-50)]/50 p-3">
              <p className="text-xs font-semibold text-[var(--color-brand-text-muted)]">Năng lực bị AI đánh giá quá cao</p>
              <ul className="mt-2 space-y-1 text-sm text-[var(--color-brand-text-body)]">
                {policy.summary_payload.top_overrated_competencies.length ? (
                  policy.summary_payload.top_overrated_competencies.map((item) => <li key={item}>{item}</li>)
                ) : (
                  <li>Không có</li>
                )}
              </ul>
            </div>
            <div className="rounded-[14px] bg-[var(--color-primary-50)]/50 p-3">
              <p className="text-xs font-semibold text-[var(--color-brand-text-muted)]">Tác động kỳ vọng</p>
              <ul className="mt-2 space-y-1 text-sm text-[var(--color-brand-text-body)]">
                {policy.summary_payload.expected_effects.length ? (
                  policy.summary_payload.expected_effects.map((item) => <li key={item}>{item}</li>)
                ) : (
                  <li>Không có</li>
                )}
              </ul>
            </div>
          </div>
          <div className="rounded-[14px] border border-[var(--color-brand-input-border)] p-3">
            <p className="text-xs font-semibold text-[var(--color-brand-text-muted)]">Ngưỡng áp dụng chính sách</p>
            <div className="mt-2 grid gap-2 md:grid-cols-2 text-sm text-[var(--color-brand-text-body)]">
              <p>Ngưỡng câu trả lời chung chung: {policy.policy_payload.global_thresholds.generic_answer_evidence_threshold}</p>
              <p>Ngưỡng bằng chứng mạnh: {policy.policy_payload.global_thresholds.strong_evidence_threshold}</p>
              <p>Độ tin cậy khi chốt: {policy.policy_payload.global_thresholds.wrap_up_confidence_threshold}</p>
              <p>Số lần điều chỉnh trước khi nâng cấp cho HR: {policy.policy_payload.global_thresholds.escalate_after_consecutive_adjustments}</p>
            </div>
          </div>
        </div>
      )}
    </article>
  )
}

function PlanImpactCard({ sessionDetail }: { sessionDetail: InterviewSessionDetailResponse | null | undefined }) {
  const plan = sessionDetail?.plan
  const policyOverrides = plan?.active_policy?.competency_overrides ?? []
  const impactedCompetencies = (plan?.competencies ?? []).filter((competency) =>
    competency.evidence_needed.some((item) => item.en.includes("previously showed AI-HR disagreement")),
  )

  return (
    <article className="rounded-[16px] border border-[var(--color-brand-input-border)] p-4">
      <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">Tác động lên kế hoạch phỏng vấn kế tiếp</p>
      {!plan ? (
        <div className="mt-3">
          <EmptyValue text="Hãy publish hoặc tải một phiên để xem policy tác động lên kế hoạch thế nào." />
        </div>
      ) : (
        <div className="mt-3 space-y-3 text-sm text-[var(--color-brand-text-body)]">
          <p>
            Phiên bản chính sách: {plan.policy_version ?? "không có"} · Số điều chỉnh riêng: {policyOverrides.length} · Trạng thái quyết định:{" "}
            {plan.interview_decision_status ?? "continue"}
          </p>
          {policyOverrides.length ? (
            <ul className="list-disc space-y-2 pl-5">
              {policyOverrides.slice(0, 4).map((override) => (
                <li key={override.competency_name.en}>
                  {override.competency_name.vi || override.competency_name.en}: tăng ưu tiên {override.priority_boost}, thiên hướng hỏi làm rõ {override.clarification_bias}, yêu cầu kết quả đo được {override.require_measurable_outcome ? "bắt buộc" : "tùy chọn"}
                </li>
              ))}
            </ul>
          ) : null}
          {impactedCompetencies.length ? (
            <ul className="list-disc space-y-2 pl-5">
              {impactedCompetencies.slice(0, 4).map((competency) => (
                <li key={competency.name.en}>
                  {competency.name.vi || competency.name.en}: số câu hỏi mục tiêu {competency.target_question_count}, ghi chú bằng chứng {competency.evidence_needed.length}
                </li>
              ))}
            </ul>
          ) : (
            <p>Chưa thấy năng lực nào bị tác động trong kế hoạch phiên này.</p>
          )}
        </div>
      )}
    </article>
  )
}

export function InterviewFeedbackPolicyPanel({
  jdId,
  accessToken,
  backendBaseUrl,
  initialData,
  interviewDetail,
}: {
  jdId: string
  accessToken: string
  backendBaseUrl: string
  initialData: InterviewFeedbackPolicyCollectionResponse | null
  interviewDetail?: InterviewSessionDetailResponse | null
}) {
  const [data, setData] = useState(initialData)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  async function refreshPolicies() {
    const response = await fetch(`${backendBaseUrl}/api/v1/interviews/jd/${jdId}/feedback-policy`, {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
      cache: "no-store",
    })
    if (!response.ok) {
      throw new Error("Không thể làm mới policy phản hồi phỏng vấn.")
    }
    setData((await response.json()) as InterviewFeedbackPolicyCollectionResponse)
  }

  async function handleSuggest() {
    setIsLoading(true)
    setError(null)
    setSuccess(null)
    try {
      const response = await fetch(`${backendBaseUrl}/api/v1/interviews/jd/${jdId}/feedback-policy/suggest`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      })
      if (!response.ok) {
        const body = (await response.json().catch(() => null)) as { detail?: string } | null
        setError(body?.detail ?? "Không thể tạo gợi ý policy phản hồi mới.")
        return
      }
      const payload = (await response.json()) as SuggestInterviewFeedbackPolicyResponse
      setData((current) => ({
        jd_id: jdId,
        active_policy: current?.active_policy ?? null,
        latest_suggested_policy: payload.policy,
        memory_context: current?.memory_context ?? [],
        policy_audit_trail: [payload.audit_event, ...(current?.policy_audit_trail ?? [])],
      }))
      await refreshPolicies()
      setSuccess("Đã tạo gợi ý policy bằng AI từ phản hồi gần đây của JD.")
    } catch {
      setError("Không thể kết nối tới backend khi tạo gợi ý policy.")
    } finally {
      setIsLoading(false)
    }
  }

  async function handlePolicyAction(policyId: string, action: "apply" | "reject") {
    setIsLoading(true)
    setError(null)
    setSuccess(null)
    try {
      const response = await fetch(
        `${backendBaseUrl}/api/v1/interviews/jd/${jdId}/feedback-policy/${policyId}/${action}`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
        },
      )
      if (!response.ok) {
        const body = (await response.json().catch(() => null)) as { detail?: string } | null
        setError(body?.detail ?? `Không thể ${action} policy.`)
        return
      }
      await refreshPolicies()
      setSuccess(action === "apply" ? "Policy gợi ý đã được áp dụng." : "Policy gợi ý đã bị từ chối.")
    } catch {
      setError(`Không thể kết nối tới backend khi thử ${action} policy.`)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div id="feedback-policy-panel">
      <ReviewSection
        title="Chính sách phản hồi và nhật ký kiểm tra"
        description="Tạo gợi ý chính sách từ phản hồi của HR, sau đó rà soát và áp dụng trước phiên phỏng vấn tiếp theo."
      >
      <div className="space-y-6">
        <div className="flex flex-wrap items-center gap-3">
          <button
            className="rounded-full bg-[var(--color-brand-primary)] px-5 py-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
            disabled={isLoading}
            onClick={() => void handleSuggest()}
            type="button"
          >
            {isLoading ? "Đang xử lý..." : "Tạo gợi ý chính sách bằng AI"}
          </button>
          {data?.latest_suggested_policy ? (
            <>
              <button
                className="rounded-full border border-[var(--color-brand-primary)] px-5 py-3 text-sm font-semibold text-[var(--color-brand-primary)] disabled:cursor-not-allowed disabled:opacity-60"
                disabled={isLoading}
                onClick={() => void handlePolicyAction(data.latest_suggested_policy!.policy_id, "apply")}
                type="button"
              >
                Áp dụng chính sách gợi ý
              </button>
              <button
                className="rounded-full border border-[var(--color-brand-input-border)] px-5 py-3 text-sm font-semibold text-[var(--color-brand-text-primary)] disabled:cursor-not-allowed disabled:opacity-60"
                disabled={isLoading}
                onClick={() => void handlePolicyAction(data.latest_suggested_policy!.policy_id, "reject")}
                type="button"
              >
                Từ chối gợi ý
              </button>
            </>
          ) : null}
          {success ? <p className="text-sm text-emerald-700">{success}</p> : null}
          {error ? <p className="text-sm text-rose-700">{error}</p> : null}
        </div>

        <div className="grid gap-6 xl:grid-cols-2">
          <CollapsibleSection title="Chính sách đang áp dụng">
            <PolicyCard title="Chi tiết chính sách hiện tại" policy={data?.active_policy} />
          </CollapsibleSection>
          <CollapsibleSection title="Chính sách gợi ý mới nhất">
            <PolicyCard title="Chi tiết chính sách gợi ý" policy={data?.latest_suggested_policy} />
          </CollapsibleSection>
        </div>

        <CollapsibleSection title="Tác động lên kế hoạch phiên tiếp theo">
          <PlanImpactCard sessionDetail={interviewDetail} />
        </CollapsibleSection>

        <CollapsibleSection title="Ngữ cảnh memory đã truy xuất">
        <section>
          <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">Ngữ cảnh memory đã truy xuất</p>
          <div className="mt-3 space-y-3">
            {data?.memory_context?.length ? (
              data.memory_context.map((memory: InterviewFeedbackMemoryResponse) => (
                <article key={memory.memory_id} className="rounded-[16px] border border-[var(--color-brand-input-border)] p-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">{memory.title}</p>
                    <span className="rounded-full bg-[var(--color-primary-50)] px-3 py-1 text-xs font-semibold text-[var(--color-brand-primary)]">
                      {memory.memory_type}
                    </span>
                  </div>
                  <p className="mt-2 text-sm text-[var(--color-brand-text-body)]">{memory.memory_text}</p>
                  <p className="mt-2 text-xs text-[var(--color-brand-text-muted)]">
                    Mức quan trọng {Math.round(memory.importance_score * 100)}%
                    {memory.source_event_at ? ` · Nguồn ${memory.source_event_at}` : ""}
                  </p>
                </article>
              ))
            ) : (
              <EmptyValue text="Chưa có ngữ cảnh memory nào được truy xuất." />
            )}
          </div>
        </section>
        </CollapsibleSection>

        <CollapsibleSection title="Nhật ký kiểm tra">
        <section>
          <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">Nhật ký kiểm tra</p>
          <div className="mt-3 space-y-3">
            {data?.policy_audit_trail?.length ? (
              data.policy_audit_trail.map((event, index) => (
                <article key={`${event.event_type}-${event.created_at}-${index}`} className="rounded-[16px] border border-[var(--color-brand-input-border)] p-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">{event.event_type}</p>
                    <span className="text-xs text-[var(--color-brand-text-muted)]">{event.created_at}</span>
                  </div>
                  {event.payload.generation_mode === "llm" ? (
                    <p className="mt-2 text-xs font-semibold text-[var(--color-brand-primary)]">
                      AI tạo bằng {String(event.payload.model_name ?? "model đã cấu hình")}
                    </p>
                  ) : null}
                  <pre className="mt-3 overflow-x-auto rounded-[14px] bg-[var(--color-primary-50)]/50 p-3 text-xs text-[var(--color-brand-text-body)]">
                    {JSON.stringify(event.payload, null, 2)}
                  </pre>
                </article>
              ))
            ) : (
              <EmptyValue text="Chưa có nhật ký kiểm tra policy." />
            )}
          </div>
        </section>
        </CollapsibleSection>
        </div>
      </ReviewSection>
    </div>
  )
}
