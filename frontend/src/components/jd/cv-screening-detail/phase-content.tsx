import { InterviewFeedbackAnalytics } from "@/components/interview/interview-feedback-analytics"
import { InterviewFeedbackForm } from "@/components/interview/interview-feedback-form"
import { InterviewFeedbackPolicyPanel } from "@/components/interview/interview-feedback-policy-panel"
import { InterviewLaunchPanel } from "@/components/interview/interview-launch-panel"
import { SessionStatusCard } from "@/components/interview/session-status-card"
import { TranscriptReview } from "@/components/interview/transcript-review"
import type {
  CompanyKnowledgeDocument,
  InterviewFeedbackPolicyCollectionResponse,
  InterviewFeedbackResponse,
  InterviewFeedbackSummaryResponse,
  InterviewSessionDetailResponse,
  InterviewSessionReviewResponse,
} from "@/components/interview/interview-types"
import { CVCandidateProfile } from "@/components/jd/cv-candidate-profile"
import { CVScreeningAssessments } from "@/components/jd/cv-screening-assessments"
import { CVScreeningAudit } from "@/components/jd/cv-screening-audit"
import { FeedbackLoopSummary } from "@/components/jd/cv-screening-detail/feedback-loop-summary"
import { CVScreeningDimensions } from "@/components/jd/cv-screening-dimensions"
import { CVScreeningFollowups } from "@/components/jd/cv-screening-followups"
import { CVScreeningHistory } from "@/components/jd/cv-screening-history"
import { CVScreeningInsights } from "@/components/jd/cv-screening-insights"
import { CVScreeningRisks } from "@/components/jd/cv-screening-risks"
import { CVScreeningSummary } from "@/components/jd/cv-screening-summary"
import type {
  CVScreeningCompletedResponse,
  CVScreeningHistoryItem,
} from "@/components/jd/cv-screening-types"

export type PhaseKey = "overview" | "evaluation" | "actions" | "interview" | "feedback_loop"

type PhaseContentProps = {
  screening: CVScreeningCompletedResponse
  historyItems: CVScreeningHistoryItem[]
  accessToken: string
  backendBaseUrl: string
  interviewDetail: InterviewSessionDetailResponse | null
  interviewReview: InterviewSessionReviewResponse | null
  interviewFeedback: InterviewFeedbackResponse | null
  feedbackSummary: InterviewFeedbackSummaryResponse | null
  feedbackPolicy: InterviewFeedbackPolicyCollectionResponse | null
  companyDocuments: CompanyKnowledgeDocument[]
}

export const phaseTabs: Array<{ key: PhaseKey; label: string; description: string }> = [
  {
    key: "overview",
    label: "Giai đoạn 1 · Tổng quan",
    description: "Tóm tắt, hồ sơ ứng viên và các lượt sàng lọc khác của JD này.",
  },
  {
    key: "evaluation",
    label: "Giai đoạn 2 · Đánh giá",
    description: "Kiểm tra yêu cầu, điểm theo tiêu chí và các nhận định có kèm bằng chứng.",
  },
  {
    key: "actions",
    label: "Giai đoạn 3 · Hành động và rà soát",
    description: "Câu hỏi bổ sung, cảnh báo rủi ro và thông tin kiểm tra để HR rà soát.",
  },
  {
    key: "interview",
    label: "Giai đoạn 4 · Phỏng vấn",
    description: "Khởi chạy buổi phỏng vấn, theo dõi trạng thái phiên và xem phần tổng kết cuối.",
  },
  {
    key: "feedback_loop",
    label: "Giai đoạn 5 · Vòng phản hồi",
    description: "Thu phản hồi từ HR, xem phân tích tổng hợp và cập nhật chính sách cho các phiên sau.",
  },
]

export function OverviewPhaseContent({ screening, historyItems }: Pick<PhaseContentProps, "screening" | "historyItems">) {
  return (
    <>
      <CVScreeningHistory
        title="Các lượt sàng lọc khác của JD này"
        items={historyItems}
        currentScreeningId={screening.screening_id}
      />
      <CVScreeningSummary result={screening.result} />
      <CVCandidateProfile profile={screening.candidate_profile} />
    </>
  )
}

export function EvaluationPhaseContent({ screening }: Pick<PhaseContentProps, "screening">) {
  return (
    <>
      <CVScreeningAssessments
        knockoutAssessments={screening.result.knockout_assessments}
        minimumRequirements={screening.result.minimum_requirement_checks}
      />
      <CVScreeningDimensions dimensions={screening.result.dimension_scores} />
      <CVScreeningInsights
        strengths={screening.result.strengths}
        gaps={screening.result.gaps}
        uncertainties={screening.result.uncertainties}
      />
    </>
  )
}

export function ActionsPhaseContent({ screening }: Pick<PhaseContentProps, "screening">) {
  return (
    <>
      <CVScreeningFollowups items={screening.result.follow_up_questions} />
      <CVScreeningRisks items={screening.result.risk_flags} />
      <CVScreeningAudit audit={screening.audit} />
    </>
  )
}

export function InterviewPhaseContent({
  screening,
  accessToken,
  backendBaseUrl,
  interviewDetail,
  interviewReview,
  companyDocuments,
}: Pick<
  PhaseContentProps,
  "screening" | "accessToken" | "backendBaseUrl" | "interviewDetail" | "interviewReview" | "companyDocuments"
>) {
  return (
    <>
      <InterviewLaunchPanel
        screeningId={screening.screening_id}
        jdId={screening.jd_id}
        accessToken={accessToken}
        backendBaseUrl={backendBaseUrl}
        initialDraft={screening.interview_draft ?? null}
        initialCompanyDocuments={companyDocuments}
      />
      {interviewDetail ? (
        <>
          <SessionStatusCard
            status={interviewDetail.status}
            workerStatus={interviewDetail.worker_status}
            providerStatus={interviewDetail.provider_status}
          />
          {interviewReview ? (
            <TranscriptReview summary={interviewReview.summary_payload} turns={interviewReview.transcript_turns} />
          ) : (
            <section className="rounded-[24px] bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
              <h2 className="text-xl font-semibold text-[var(--color-brand-text-primary)]">Rà soát buổi phỏng vấn</h2>
              <p className="mt-2 text-sm text-[var(--color-brand-text-body)]">
                Buổi phỏng vấn đã bắt đầu. Phần tổng kết cuối sẽ xuất hiện ở đây sau khi phiên hoàn tất.
              </p>
            </section>
          )}
        </>
      ) : (
        <section className="rounded-[24px] bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
          <h2 className="text-xl font-semibold text-[var(--color-brand-text-primary)]">Rà soát buổi phỏng vấn</h2>
          <p className="mt-2 text-sm text-[var(--color-brand-text-body)]">Chưa có phiên phỏng vấn nào được khởi tạo.</p>
        </section>
      )}
    </>
  )
}

export function FeedbackLoopPhaseContent({
  screening,
  accessToken,
  backendBaseUrl,
  interviewDetail,
  interviewReview,
  interviewFeedback,
  feedbackSummary,
  feedbackPolicy,
}: Pick<
  PhaseContentProps,
  | "screening"
  | "accessToken"
  | "backendBaseUrl"
  | "interviewDetail"
  | "interviewReview"
  | "interviewFeedback"
  | "feedbackSummary"
  | "feedbackPolicy"
>) {
  return (
    <>
      {interviewDetail && interviewReview ? (
        <>
          <FeedbackLoopSummary
            interviewDetail={interviewDetail}
            interviewFeedback={interviewFeedback}
            feedbackSummary={feedbackSummary}
            feedbackPolicy={feedbackPolicy}
          />
          <InterviewFeedbackForm
            sessionId={interviewDetail.session_id}
            accessToken={accessToken}
            backendBaseUrl={backendBaseUrl}
            assessments={interviewReview.ai_competency_assessments}
            initialFeedback={interviewFeedback}
            onSaved={() => {
              window.location.reload()
            }}
          />
          <InterviewFeedbackAnalytics summary={feedbackSummary} />
          <InterviewFeedbackPolicyPanel
            jdId={screening.jd_id}
            accessToken={accessToken}
            backendBaseUrl={backendBaseUrl}
            initialData={feedbackPolicy}
            interviewDetail={interviewDetail}
          />
        </>
      ) : (
        <section className="rounded-[24px] bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
          <h2 className="text-xl font-semibold text-[var(--color-brand-text-primary)]">Vòng phản hồi</h2>
          <p className="mt-2 text-sm text-[var(--color-brand-text-body)]">
            Hãy hoàn tất một buổi phỏng vấn trước để mở khóa phản hồi HR, analytics và tính năng tạo policy cho AI.
          </p>
        </section>
      )}
    </>
  )
}
