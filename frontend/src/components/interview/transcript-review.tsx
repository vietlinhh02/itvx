import { CaretDown } from "@phosphor-icons/react"
import { useState } from "react"

import type { TranscriptTurn } from "@/components/interview/interview-types"
import { EmptyValue, ReviewSection } from "@/components/jd/cv-screening-ui"

type SummarySection = {
  speaker?: string
  summary?: string
}

type CompetencyAssessment = {
  competency_name?: { vi?: string; en?: string }
  ai_score?: number
  evidence_strength?: number
  needs_hr_review?: boolean
  notes?: string
}

function asStringList(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : []
}

function asSummarySectionList(value: unknown): SummarySection[] {
  if (!Array.isArray(value)) {
    return []
  }

  return value.flatMap((item) => {
    if (!item || typeof item !== "object") {
      return []
    }

    const speaker = "speaker" in item && typeof item.speaker === "string" ? item.speaker : undefined
    const summary = "summary" in item && typeof item.summary === "string" ? item.summary : undefined

    return speaker || summary ? [{ speaker, summary }] : []
  })
}

function formatLabel(value: string): string {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ")
}

function asCompetencyAssessmentList(value: unknown): CompetencyAssessment[] {
  if (!Array.isArray(value)) {
    return []
  }

  return value.flatMap((item) => {
    if (!item || typeof item !== "object") {
      return []
    }
    const competencyName =
      "competency_name" in item && item.competency_name && typeof item.competency_name === "object"
        ? (item.competency_name as { vi?: string; en?: string })
        : undefined
    const aiScore = "ai_score" in item && typeof item.ai_score === "number" ? item.ai_score : undefined
    const evidenceStrength =
      "evidence_strength" in item && typeof item.evidence_strength === "number"
        ? item.evidence_strength
        : undefined
    const needsHrReview =
      "needs_hr_review" in item && typeof item.needs_hr_review === "boolean"
        ? item.needs_hr_review
        : undefined
    const notes = "notes" in item && typeof item.notes === "string" ? item.notes : undefined

    if (!competencyName?.en && aiScore == null && evidenceStrength == null && !notes) {
      return []
    }
    return [{ competency_name: competencyName, ai_score: aiScore, evidence_strength: evidenceStrength, needs_hr_review: needsHrReview, notes }]
  })
}

function DetailCard({
  title,
  children,
  className = "",
}: {
  title: string
  children: React.ReactNode
  className?: string
}) {
  return (
    <article className={`rounded-[16px] border border-[var(--color-brand-input-border)] p-4 ${className}`.trim()}>
      <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">{title}</p>
      <div className="mt-3">{children}</div>
    </article>
  )
}

function StringList({ items, emptyText }: { items: string[]; emptyText: string }) {
  if (!items.length) {
    return <EmptyValue text={emptyText} />
  }

  return (
    <ul className="space-y-3">
      {items.map((item) => (
        <li className="rounded-[16px] border border-[var(--color-brand-input-border)] p-4" key={item}>
          <p className="text-sm text-[var(--color-brand-text-body)]">{item}</p>
        </li>
      ))}
    </ul>
  )
}

export function TranscriptReview({
  summary,
  turns,
  headerActions,
}: {
  summary: Record<string, unknown>
  turns: TranscriptTurn[]
  headerActions?: React.ReactNode
}) {
  const [isTranscriptOpen, setIsTranscriptOpen] = useState(false)
  const finalSummary = typeof summary.final_summary === "string" ? summary.final_summary : null
  const recommendation =
    typeof summary.recommendation === "string" ? formatLabel(summary.recommendation) : null
  const completionReason =
    typeof summary.completion_reason === "string" ? formatLabel(summary.completion_reason) : null
  const strengths = asStringList(summary.strengths)
  const concerns = asStringList(summary.concerns)
  const turnBreakdown = asSummarySectionList(summary.turn_breakdown)
  const competencyAssessments = asCompetencyAssessmentList(summary.competency_assessments)

  return (
    <ReviewSection
      title="Rà soát buổi phỏng vấn"
      description="Phần tổng kết cuối, các điểm nổi bật và bản ghi từ buổi phỏng vấn đã hoàn tất."
    >
      <div className="space-y-6">
        {headerActions ? <div className="flex flex-wrap items-center gap-3">{headerActions}</div> : null}
        <div className="grid gap-6 xl:grid-cols-2">
          <div className="space-y-6 xl:col-span-2">
            <div className="rounded-[16px] bg-[var(--color-primary-50)] p-4">
              <p className="text-sm font-semibold text-[var(--color-brand-primary)]">
                Đề xuất sau buổi phỏng vấn
              </p>
              {recommendation ? (
                <p className="mt-2 text-2xl font-semibold text-[var(--color-brand-text-primary)]">
                  {recommendation}
                </p>
              ) : (
                <div className="mt-2">
                  <EmptyValue text="Chưa có khuyến nghị" />
                </div>
              )}
              {completionReason ? (
                <p className="mt-3 text-sm font-medium text-[var(--color-brand-text-primary)]">
                  Trạng thái kết thúc phiên: {completionReason}
                </p>
              ) : null}
            </div>

            <DetailCard title="Tóm tắt cuối">
              {finalSummary ? (
                <p className="text-sm text-[var(--color-brand-text-body)]">{finalSummary}</p>
              ) : (
                <EmptyValue text="Chưa có tóm tắt cuối." />
              )}
            </DetailCard>
          </div>

          <section>
            <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">Điểm mạnh</p>
            <div className="mt-3">
              <StringList items={strengths} emptyText="Không có điểm mạnh" />
            </div>
          </section>

          <section>
            <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">Điểm cần cân nhắc thêm</p>
            <div className="mt-3">
              <StringList items={concerns} emptyText="Không có điểm cần lưu ý" />
            </div>
          </section>
        </div>

        <section>
          <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">Đánh giá năng lực từ AI</p>
          <div className="mt-3 space-y-3">
            {competencyAssessments.length ? (
              competencyAssessments.map((item, index) => (
                <article
                  className="rounded-[16px] border border-[var(--color-brand-input-border)] p-4"
                  key={`${item.competency_name?.en ?? "competency"}-${index}`}
                >
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">{item.competency_name?.vi ?? item.competency_name?.en ?? `Năng lực ${index + 1}`}</p>
                    {item.needs_hr_review ? (
                      <span className="rounded-full bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-700">
                        Cần HR xem lại
                      </span>
                    ) : null}
                  </div>
                  <p className="mt-2 text-sm text-[var(--color-brand-text-body)]">
                    Mức đánh giá của AI: {item.ai_score != null ? `${Math.round(item.ai_score * 100)}%` : "—"} · Độ tin cậy của bằng chứng: {item.evidence_strength != null ? `${Math.round(item.evidence_strength * 100)}%` : "—"}
                  </p>
                  {item.notes ? <p className="mt-2 text-sm text-[var(--color-brand-text-body)]">{item.notes}</p> : null}
                </article>
              ))
            ) : (
              <EmptyValue text="Chưa có đánh giá năng lực" />
            )}
          </div>
        </section>

        <section>
          <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">Điểm nổi bật của buổi phỏng vấn</p>
          <div className="mt-3 space-y-3">
            {turnBreakdown.length ? (
              turnBreakdown.map((item, index) => (
                <article
                  className="rounded-[16px] border border-[var(--color-brand-input-border)] p-4"
                  key={`${item.speaker ?? "step"}-${index}`}
                >
                  <p className="text-xs text-[var(--color-brand-text-muted)]">
                    {item.speaker ? formatLabel(item.speaker) : `Bước ${index + 1}`}
                  </p>
                  {item.summary ? (
                    <p className="mt-2 text-sm text-[var(--color-brand-text-body)]">{item.summary}</p>
                  ) : (
                    <div className="mt-2">
                      <EmptyValue text="Chưa có tóm tắt điểm nổi bật" />
                    </div>
                  )}
                </article>
              ))
            ) : (
              <EmptyValue text="Chưa có điểm nổi bật của buổi phỏng vấn" />
            )}
          </div>
        </section>

        <section>
          <button
            className="flex w-full items-center justify-between gap-3 rounded-[16px] border border-[var(--color-brand-input-border)] bg-white px-4 py-3 text-left"
            onClick={() => setIsTranscriptOpen((current) => !current)}
            type="button"
          >
            <div>
              <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">Bản ghi</p>
              <p className="mt-1 text-xs text-[var(--color-brand-text-muted)]">
                {isTranscriptOpen ? "Thu gọn bản ghi chi tiết" : "Mở bản ghi chi tiết"}
              </p>
            </div>
            <CaretDown
              className={`shrink-0 text-[var(--color-brand-text-muted)] transition-transform duration-300 ${isTranscriptOpen ? "rotate-180" : "rotate-0"}`}
              size={18}
              weight="bold"
            />
          </button>
          <div
            className={`grid transition-all duration-300 ease-in-out ${
              isTranscriptOpen ? "mt-3 grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0"
            }`}
          >
            <div className="overflow-hidden">
              {turns.length ? (
                <div className="mt-3 overflow-hidden rounded-[16px] border border-[var(--color-brand-input-border)] bg-white">
                  {turns.map((turn) => (
                    <article
                      className="grid gap-2 border-b border-[var(--color-brand-input-border)] px-4 py-4 last:border-b-0 md:grid-cols-[140px_minmax(0,1fr)] md:gap-4"
                      key={`${turn.speaker}-${turn.sequence_number}`}
                    >
                      <p className="text-xs font-semibold uppercase tracking-[0.08em] text-[var(--color-brand-text-muted)]">
                        {formatLabel(turn.speaker)}
                      </p>
                      <p className="text-sm leading-6 text-[var(--color-brand-text-body)]">{turn.transcript_text}</p>
                    </article>
                  ))}
                </div>
              ) : (
                <div className="pt-3">
                  <EmptyValue text="Chưa có bản ghi" />
                </div>
              )}
            </div>
          </div>
        </section>
      </div>
    </ReviewSection>
  )
}
