"use client"

import type {
  CompanyKnowledgeDocument,
  InterviewFeedbackPolicyCollectionResponse,
  InterviewFeedbackResponse,
  InterviewFeedbackSummaryResponse,
  InterviewSessionDetailResponse,
  InterviewSessionReviewResponse,
} from "@/components/interview/interview-types"
import {
  ActionsPhaseContent,
  EvaluationPhaseContent,
  FeedbackLoopPhaseContent,
  InterviewPhaseContent,
  OverviewPhaseContent,
  type PhaseKey,
  phaseTabs,
} from "@/components/jd/cv-screening-detail/phase-content"
import type {
  CVScreeningCompletedResponse,
  CVScreeningHistoryItem,
} from "@/components/jd/cv-screening-types"
import type { Route } from "next"
import { AppLink } from "@/components/navigation/app-link"
import { usePageScrollRestore, useSessionStorageState } from "@/hooks/use-persisted-ui-state"

type CVScreeningDetailProps = {
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

export function CVScreeningDetail({
  screening,
  historyItems,
  accessToken,
  backendBaseUrl,
  interviewDetail,
  interviewReview,
  interviewFeedback,
  feedbackSummary,
  feedbackPolicy,
  companyDocuments,
}: CVScreeningDetailProps) {
  const [activePhase, setActivePhase] = useSessionStorageState<PhaseKey>(
    `interviewx:cv-screening-detail:${screening.screening_id}:active-phase`,
    "overview",
  )
  usePageScrollRestore(`interviewx:cv-screening-detail:${screening.screening_id}:scroll-y`)
  const activeTab = phaseTabs.find((tab) => tab.key === activePhase) ?? phaseTabs[0]

  return (
    <main className="flex w-full flex-col gap-6 py-6">
      <section className="rounded-[24px] bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-[var(--color-brand-text-muted)]">
              Giai đoạn 2 - Sàng lọc CV
            </p>
            <h1 className="mt-2 text-3xl font-semibold text-[var(--color-brand-text-primary)]">
              {screening.file_name}
            </h1>
            <p className="mt-2 text-sm text-[var(--color-brand-text-body)]">
              Xem lại kết quả sàng lọc đã được lưu trong cơ sở dữ liệu.
            </p>
          </div>
          <AppLink
            className="rounded-full bg-[var(--color-brand-primary)] px-4 py-3 text-sm font-semibold text-white"
            href={buildJDRoute(screening.jd_id)}
          >
            Quay lại chi tiết mô tả công việc
          </AppLink>
        </div>

        <div className="mt-6 flex flex-wrap gap-3">
          {phaseTabs.map((tab) => {
            const isActive = tab.key === activePhase

            return (
              <button
                key={tab.key}
                className={[
                  "rounded-full border px-4 py-3 text-sm font-semibold transition duration-200 hover:-translate-y-0.5",
                  isActive
                    ? "border-[var(--color-brand-primary)] bg-[var(--color-brand-primary)] text-white"
                    : "border-[var(--color-brand-input-border)] bg-white text-[var(--color-brand-text-muted)]",
                ].join(" ")}
                onClick={() => setActivePhase(tab.key)}
                type="button"
              >
                {tab.label}
              </button>
            )
          })}
        </div>
        <p className="mt-3 text-sm text-[var(--color-brand-text-body)]">{activeTab.description}</p>
      </section>

      <div key={activePhase} className="space-y-6 motion-safe:animate-[panel-enter_220ms_ease-out]">
        {activePhase === "overview" ? (
          <OverviewPhaseContent screening={screening} historyItems={historyItems} />
        ) : null}

        {activePhase === "evaluation" ? <EvaluationPhaseContent screening={screening} /> : null}

        {activePhase === "actions" ? <ActionsPhaseContent screening={screening} /> : null}

        {activePhase === "interview" ? (
          <InterviewPhaseContent
            screening={screening}
            accessToken={accessToken}
            backendBaseUrl={backendBaseUrl}
            interviewDetail={interviewDetail}
            interviewReview={interviewReview}
            companyDocuments={companyDocuments}
          />
        ) : null}

        {activePhase === "feedback_loop" ? (
          <FeedbackLoopPhaseContent
            screening={screening}
            accessToken={accessToken}
            backendBaseUrl={backendBaseUrl}
            interviewDetail={interviewDetail}
            interviewReview={interviewReview}
            interviewFeedback={interviewFeedback}
            feedbackSummary={feedbackSummary}
            feedbackPolicy={feedbackPolicy}
          />
        ) : null}
      </div>
    </main>
  )
}

function buildJDRoute(jdId: string): Route {
  return `/dashboard/jd/${jdId}` as Route
}
