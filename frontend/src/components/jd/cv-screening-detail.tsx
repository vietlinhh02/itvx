import Link from "next/link"

import { CVCandidateProfile } from "@/components/jd/cv-candidate-profile"
import { CVScreeningAssessments } from "@/components/jd/cv-screening-assessments"
import { CVScreeningAudit } from "@/components/jd/cv-screening-audit"
import { CVScreeningHistory } from "@/components/jd/cv-screening-history"
import { CVScreeningDimensions } from "@/components/jd/cv-screening-dimensions"
import { CVScreeningFollowups } from "@/components/jd/cv-screening-followups"
import { CVScreeningInsights } from "@/components/jd/cv-screening-insights"
import { CVScreeningRisks } from "@/components/jd/cv-screening-risks"
import { CVScreeningSummary } from "@/components/jd/cv-screening-summary"
import type {
  CVScreeningHistoryItem,
  CVScreeningResponse,
} from "@/components/jd/cv-screening-types"

type CVScreeningDetailProps = {
  screening: CVScreeningResponse
  historyItems: CVScreeningHistoryItem[]
}

export function CVScreeningDetail({ screening, historyItems }: CVScreeningDetailProps) {
  return (
    <main className="flex w-full flex-col gap-6 py-6">
      <section className="rounded-[24px] bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-[var(--color-brand-text-muted)]">
              Phase 2 - CV Screening
            </p>
            <h1 className="mt-2 text-3xl font-semibold text-[var(--color-brand-text-primary)]">
              {screening.file_name}
            </h1>
            <p className="mt-2 text-sm text-[var(--color-brand-text-body)]">
              Review the stored screening result loaded from the database.
            </p>
          </div>
          <Link
            className="rounded-full bg-[var(--color-brand-primary)] px-4 py-3 text-sm font-semibold text-white"
            href={`/dashboard/jd/${screening.jd_id}`}
          >
            Back to JD detail
          </Link>
        </div>
      </section>

      <CVScreeningHistory
        title="Other screenings for this JD"
        items={historyItems}
        currentScreeningId={screening.screening_id}
      />
      <CVScreeningSummary result={screening.result} />
      <CVCandidateProfile profile={screening.candidate_profile} />
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
      <CVScreeningFollowups items={screening.result.follow_up_questions} />
      <CVScreeningRisks items={screening.result.risk_flags} />
      <CVScreeningAudit audit={screening.audit} />
    </main>
  )
}
