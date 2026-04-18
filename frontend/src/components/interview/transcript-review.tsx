import { CaretDown } from "@phosphor-icons/react"
import { useState } from "react"

import type {
  InterviewSessionCompetencyAssessment,
  TranscriptTurn,
} from "@/components/interview/interview-types"
import { EmptyValue, ReviewSection } from "@/components/jd/cv-screening-ui"

type SummarySection = {
  speaker?: string
  summary: string
  sequenceNumber?: number
}

type CompetencyAssessment = {
  competency_name?: { vi?: string; en?: string }
  ai_score?: number
  evidence_strength?: number | string
  needs_hr_review?: boolean
  notes?: string
}

const EMPTY_TEXT_VALUES = new Set(["không có", "không có.", "none", "none.", "n/a", "n/a."])

const COMPLETION_REASON_LABELS: Record<string, string> = {
  adjust: "Cần điều chỉnh thêm",
  complete: "Đã hoàn tất",
  continue: "Tiếp tục phỏng vấn",
  escalate_hr: "Cần HR xem xét",
  ready_to_wrap: "Sẵn sàng kết thúc",
}

function normalizeText(value: string): string {
  return value.trim().replace(/\r\n/g, "\n")
}

function isMeaningfulText(value: string): boolean {
  return !EMPTY_TEXT_VALUES.has(normalizeText(value).toLowerCase())
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return value as Record<string, unknown>
  }

  if (typeof value !== "string") {
    return null
  }

  let normalized = value.trim()
  const fencedJsonMatch = normalized.match(/^```(?:json)?\s*([\s\S]*?)\s*```$/i)

  if (fencedJsonMatch) {
    normalized = fencedJsonMatch[1].trim()
  }

  if (!normalized.startsWith("{") || !normalized.endsWith("}")) {
    return null
  }

  try {
    return asRecord(JSON.parse(normalized))
  } catch {
    return null
  }
}

function resolveSummaryPayload(value: unknown): Record<string, unknown> {
  const summary = asRecord(value) ?? {}
  const nestedSummary = asRecord(summary.final_summary)

  return nestedSummary ? { ...summary, ...nestedSummary } : summary
}

function asStringList(value: unknown): string[] {
  if (typeof value === "string") {
    const normalized = normalizeText(value)
    return normalized && isMeaningfulText(normalized) ? [normalized] : []
  }

  return Array.isArray(value)
    ? value.flatMap((item) => (typeof item === "string" ? asStringList(item) : []))
    : []
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
    const sequenceNumber =
      "sequence_number" in item && typeof item.sequence_number === "number" ? item.sequence_number : undefined
    const summaryCandidates = [
      "summary" in item && typeof item.summary === "string" ? item.summary : null,
      "assessment" in item && typeof item.assessment === "string" ? item.assessment : null,
    ]
    const summary = summaryCandidates
      .map((candidate) => (typeof candidate === "string" ? normalizeText(candidate) : null))
      .find((candidate): candidate is string => Boolean(candidate && isMeaningfulText(candidate)))

    return summary ? [{ speaker, summary, sequenceNumber }] : []
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
      "competency_name" in item
        ? typeof item.competency_name === "string"
          ? { en: normalizeText(item.competency_name) }
          : item.competency_name && typeof item.competency_name === "object"
            ? (item.competency_name as { vi?: string; en?: string })
            : undefined
        : undefined
    const aiScore = "ai_score" in item && typeof item.ai_score === "number" ? item.ai_score : undefined
    const evidenceStrength =
      "evidence_strength" in item &&
      (typeof item.evidence_strength === "number" || typeof item.evidence_strength === "string")
        ? typeof item.evidence_strength === "string"
          ? normalizeText(item.evidence_strength)
          : item.evidence_strength
        : undefined
    const needsHrReview =
      "needs_hr_review" in item && typeof item.needs_hr_review === "boolean"
        ? item.needs_hr_review
        : undefined
    const notes = "notes" in item && typeof item.notes === "string" ? normalizeText(item.notes) : undefined

    if (!competencyName?.en && !competencyName?.vi && aiScore == null && evidenceStrength == null && !notes) {
      return []
    }
    return [{ competency_name: competencyName, ai_score: aiScore, evidence_strength: evidenceStrength, needs_hr_review: needsHrReview, notes }]
  })
}

function formatCompletionReason(value: string): string {
  return COMPLETION_REASON_LABELS[value] ?? formatLabel(value)
}

function formatScore(value?: number): string {
  if (value == null) {
    return "—"
  }

  const normalized = value <= 1 ? value * 100 : value

  return `${Math.round(normalized)}%`
}

function formatEvidenceStrength(value?: number | string): string {
  if (typeof value === "number") {
    return formatScore(value)
  }

  if (typeof value === "string" && value) {
    if (!isMeaningfulText(value)) {
      return "Không có"
    }

    return formatLabel(value)
  }

  return "—"
}

function CompactReviewRow({
  label,
  children,
  emphasis = false,
  highlight = false,
}: {
  label: string
  children: React.ReactNode
  emphasis?: boolean
  highlight?: boolean
}) {
  return (
    <article
      className={`grid gap-2 border-b border-[var(--color-brand-input-border)] px-4 py-4 last:border-b-0 md:grid-cols-[180px_minmax(0,1fr)] md:gap-4 ${
        highlight ? "bg-[var(--color-primary-50)]" : ""
      }`.trim()}
    >
      <p className="text-xs font-semibold uppercase tracking-[0.08em] text-[var(--color-brand-text-muted)]">
        {label}
      </p>
      <div
        className={
          emphasis
            ? "min-w-0 text-lg font-semibold leading-8 text-[var(--color-brand-text-primary)]"
            : "min-w-0 text-sm leading-6 text-[var(--color-brand-text-body)]"
        }
      >
        {children}
      </div>
    </article>
  )
}

function CompactTextStack({ items, emptyText }: { items: string[]; emptyText: string }) {
  if (!items.length) {
    return <EmptyValue text={emptyText} />
  }

  return (
    <div className="space-y-2">
      {items.map((item) => (
        <p className="text-sm leading-6 text-[var(--color-brand-text-body)]" key={item}>
          {item}
        </p>
      ))}
    </div>
  )
}

export function TranscriptReview({
  summary,
  turns,
  aiCompetencyAssessments = [],
  headerActions,
}: {
  summary: Record<string, unknown>
  turns: TranscriptTurn[]
  aiCompetencyAssessments?: InterviewSessionCompetencyAssessment[]
  headerActions?: React.ReactNode
}) {
  const [isTranscriptOpen, setIsTranscriptOpen] = useState(false)
  const [isHighlightsOpen, setIsHighlightsOpen] = useState(false)
  const normalizedSummary = resolveSummaryPayload(summary)
  const finalSummary = typeof normalizedSummary.final_summary === "string" ? normalizeText(normalizedSummary.final_summary) : null
  const recommendation =
    typeof normalizedSummary.recommendation === "string" ? normalizeText(normalizedSummary.recommendation) : null
  const completionReason =
    typeof normalizedSummary.completion_reason === "string"
      ? formatCompletionReason(normalizeText(normalizedSummary.completion_reason))
      : null
  const strengths = asStringList(normalizedSummary.strengths)
  const concerns = asStringList(normalizedSummary.concerns)
  const turnBreakdown = asSummarySectionList(normalizedSummary.turn_breakdown)
  const summaryCompetencyAssessments = asCompetencyAssessmentList(normalizedSummary.competency_assessments)
  const competencyAssessments =
    summaryCompetencyAssessments.length > 0
      ? summaryCompetencyAssessments
      : aiCompetencyAssessments.map((item) => ({
          competency_name: item.competency_name,
          ai_score: item.ai_score ?? undefined,
          evidence_strength: item.evidence_strength ?? undefined,
          needs_hr_review: item.needs_hr_review,
          notes: item.notes ?? undefined,
        }))

  return (
    <ReviewSection
      title="Rà soát buổi phỏng vấn"
      description="Phần tổng kết cuối, các điểm nổi bật và bản ghi từ buổi phỏng vấn đã hoàn tất."
    >
      <div className="space-y-6">
        {headerActions ? <div className="flex flex-wrap items-center gap-3">{headerActions}</div> : null}
        <div className="overflow-hidden rounded-[16px] border border-[var(--color-brand-input-border)] bg-white">
          <CompactReviewRow emphasis highlight label="Đề xuất">
            {recommendation ? recommendation : <EmptyValue text="Chưa có khuyến nghị" />}
          </CompactReviewRow>
          {completionReason ? (
            <CompactReviewRow label="Trạng thái kết thúc">{completionReason}</CompactReviewRow>
          ) : null}
          <CompactReviewRow label="Tóm tắt cuối">
            {finalSummary ? finalSummary : <EmptyValue text="Chưa có tóm tắt cuối." />}
          </CompactReviewRow>
          <CompactReviewRow label="Điểm mạnh">
            <CompactTextStack items={strengths} emptyText="Không có điểm mạnh" />
          </CompactReviewRow>
          <CompactReviewRow label="Điểm cần cân nhắc">
            <CompactTextStack items={concerns} emptyText="Không có điểm cần lưu ý" />
          </CompactReviewRow>
        </div>

        <section>
          <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">Đánh giá năng lực từ AI</p>
          <div className="mt-3 overflow-hidden rounded-[16px] border border-[var(--color-brand-input-border)] bg-white">
            {competencyAssessments.length ? (
              competencyAssessments.map((item, index) => (
                <article
                  className="grid gap-2 border-b border-[var(--color-brand-input-border)] px-4 py-4 last:border-b-0 md:grid-cols-[180px_minmax(0,1fr)] md:gap-4"
                  key={`${item.competency_name?.en ?? "competency"}-${index}`}
                >
                  <p className="text-xs font-semibold uppercase tracking-[0.08em] text-[var(--color-brand-text-muted)]">
                    {item.competency_name?.vi ?? item.competency_name?.en ?? `Năng lực ${index + 1}`}
                  </p>
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-3">
                      <p className="text-sm leading-6 text-[var(--color-brand-text-body)]">
                        Mức đánh giá của AI: {formatScore(item.ai_score)} · Độ tin cậy của bằng chứng: {formatEvidenceStrength(item.evidence_strength)}
                      </p>
                    {item.needs_hr_review ? (
                      <span className="rounded-full bg-sky-50 px-3 py-1 text-xs font-semibold text-sky-700">
                        Cần HR xem lại
                      </span>
                    ) : null}
                    </div>
                    {item.notes ? <p className="mt-2 text-sm leading-6 text-[var(--color-brand-text-body)]">{item.notes}</p> : null}
                  </div>
                </article>
              ))
            ) : (
              <div className="px-4 py-4">
                <EmptyValue text="Chưa có đánh giá năng lực" />
              </div>
            )}
          </div>
        </section>

        <section>
          <button
            aria-expanded={isHighlightsOpen}
            className="flex w-full items-center justify-between gap-3 rounded-[16px] border border-[var(--color-brand-input-border)] bg-white px-4 py-3 text-left"
            onClick={() => setIsHighlightsOpen((current) => !current)}
            type="button"
          >
            <div>
              <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">Điểm nổi bật của buổi phỏng vấn</p>
              <p className="mt-1 text-xs text-[var(--color-brand-text-muted)]">
                {isHighlightsOpen
                  ? "Thu gọn các điểm nổi bật"
                  : turnBreakdown.length
                    ? `Mở ${turnBreakdown.length} điểm nổi bật đã được tổng hợp`
                    : "Chưa có điểm nổi bật để hiển thị"}
              </p>
            </div>
            <CaretDown
              className={`shrink-0 text-[var(--color-brand-text-muted)] transition-transform duration-300 ${isHighlightsOpen ? "rotate-180" : "rotate-0"}`}
              size={18}
              weight="bold"
            />
          </button>
          {isHighlightsOpen ? (
            <div className="mt-3 overflow-hidden rounded-[16px] border border-[var(--color-brand-input-border)] bg-white">
              {turnBreakdown.length ? (
                turnBreakdown.map((item, index) => (
                  <article
                    className="grid gap-2 border-b border-[var(--color-brand-input-border)] px-4 py-4 last:border-b-0 md:grid-cols-[140px_minmax(0,1fr)] md:gap-4"
                    key={`${item.speaker ?? "step"}-${item.sequenceNumber ?? index}`}
                  >
                    <p className="text-xs font-semibold uppercase tracking-[0.08em] text-[var(--color-brand-text-muted)]">
                      {item.speaker ? formatLabel(item.speaker) : `Bước ${index + 1}`}
                    </p>
                    <p className="text-sm leading-6 text-[var(--color-brand-text-body)]">{item.summary}</p>
                  </article>
                ))
              ) : (
                <div className="px-4 py-4">
                  <EmptyValue text="Chưa có điểm nổi bật của buổi phỏng vấn" />
                </div>
              )}
            </div>
          ) : null}
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
