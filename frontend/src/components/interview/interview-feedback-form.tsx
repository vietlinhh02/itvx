"use client"

import { CaretDown } from "@phosphor-icons/react"
import { useEffect, useMemo, useRef, useState } from "react"

import type {
  InterviewFeedbackRequest,
  InterviewFeedbackResponse,
  InterviewSessionCompetencyAssessment,
} from "@/components/interview/interview-types"
import { EmptyValue, ReviewSection } from "@/components/jd/cv-screening-ui"
import { CollapsibleSection } from "@/components/interview/live-room/live-room-shell-parts"

const judgementOptions = ["accurate", "overrated", "underrated", "insufficient_evidence"] as const

function formatPercent(value: number | null | undefined) {
  if (value == null || Number.isNaN(value)) {
    return "—"
  }
  return `${Math.round(value * 100)}%`
}

const recommendationOptions = [
  { value: "", label: "Chọn kết luận" },
  { value: "advance", label: "Tiến tiếp" },
  { value: "review", label: "Cần xem lại" },
  { value: "reject", label: "Từ chối" },
]

function formatJudgementLabel(value: (typeof judgementOptions)[number]) {
  if (value === "accurate") {
    return "Đánh giá đúng"
  }
  if (value === "overrated") {
    return "Đánh giá quá cao"
  }
  if (value === "underrated") {
    return "Đánh giá quá thấp"
  }

  return "Thiếu bằng chứng"
}

type DropdownOption = {
  value: string
  label: string
}

function FormDropdown({
  label,
  options,
  value,
  placeholder,
  onChange,
  className,
  buttonClassName,
}: {
  label: string
  options: DropdownOption[]
  value: string
  placeholder: string
  onChange: (value: string) => void
  className?: string
  buttonClassName?: string
}) {
  const [isOpen, setIsOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement | null>(null)
  const selectedOption = options.find((option) => option.value === value) ?? null

  useEffect(() => {
    function handlePointerDown(event: PointerEvent) {
      if (!containerRef.current?.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setIsOpen(false)
      }
    }

    document.addEventListener("pointerdown", handlePointerDown)
    document.addEventListener("keydown", handleEscape)

    return () => {
      document.removeEventListener("pointerdown", handlePointerDown)
      document.removeEventListener("keydown", handleEscape)
    }
  }, [])

  return (
    <div ref={containerRef} className={className}>
      <span className="text-sm font-semibold text-[var(--color-brand-text-primary)]">{label}</span>
      <div className="relative mt-2">
        <button
          type="button"
          className={[
            "flex w-full items-center justify-between rounded-[16px] border border-[var(--color-brand-input-border)] bg-white px-4 py-3 text-left text-sm",
            buttonClassName ?? "",
          ].join(" ")}
          onClick={() => setIsOpen((open) => !open)}
          aria-expanded={isOpen}
          aria-haspopup="listbox"
        >
          <span className={selectedOption ? "text-[var(--color-brand-text-primary)]" : "text-[var(--color-brand-text-muted)]"}>
            {selectedOption?.label ?? placeholder}
          </span>
          <CaretDown
            className={`shrink-0 text-[var(--color-brand-primary)] transition-transform duration-200 ${isOpen ? "rotate-180" : "rotate-0"}`}
            size={18}
            weight="bold"
          />
        </button>
        {isOpen ? (
          <div
            className="absolute left-0 right-0 top-full z-20 mt-2 overflow-hidden rounded-[16px] border border-[var(--color-brand-input-border)] bg-white shadow-[0px_10px_30px_0px_rgba(15,79,87,0.12)]"
            role="listbox"
            aria-label={label}
          >
            <div className="max-h-72 overflow-y-auto py-1">
              {options.map((option) => {
                const isSelected = option.value === value

                return (
                  <button
                    key={option.value}
                    type="button"
                    role="option"
                    aria-selected={isSelected}
                    onClick={() => {
                      onChange(option.value)
                      setIsOpen(false)
                    }}
                    className={[
                      "flex w-full items-center justify-between px-4 py-3 text-left text-sm font-medium",
                      isSelected
                        ? "bg-[var(--color-primary-50)] text-[var(--color-brand-primary)]"
                        : "bg-white text-[var(--color-brand-text-primary)] hover:bg-[var(--color-primary-50)]",
                    ].join(" ")}
                  >
                    <span className="truncate">{option.label}</span>
                    {isSelected ? <span className="text-xs font-semibold">Đã chọn</span> : null}
                  </button>
                )
              })}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  )
}

export function InterviewFeedbackForm({
  sessionId,
  accessToken,
  backendBaseUrl,
  assessments,
  initialFeedback,
  onSaved,
}: {
  sessionId: string
  accessToken: string
  backendBaseUrl: string
  assessments?: InterviewSessionCompetencyAssessment[] | null
  initialFeedback: InterviewFeedbackResponse | null
  onSaved: (value: InterviewFeedbackResponse) => void
}) {
  const safeAssessments = useMemo(() => assessments ?? [], [assessments])
  const defaultCompetencies = useMemo(
    () =>
      safeAssessments.map((assessment) => ({
        competency_name: assessment.competency_name,
        hr_score: initialFeedback?.competencies.find(
          (item) => item.competency_name.en === assessment.competency_name.en,
        )?.hr_score ?? assessment.ai_score ?? 0.5,
        judgement:
          initialFeedback?.competencies.find((item) => item.competency_name.en === assessment.competency_name.en)
            ?.judgement ?? "accurate",
        missing_evidence:
          initialFeedback?.competencies.find((item) => item.competency_name.en === assessment.competency_name.en)
            ?.missing_evidence ?? "",
        notes:
          initialFeedback?.competencies.find((item) => item.competency_name.en === assessment.competency_name.en)
            ?.notes ?? "",
      })),
    [safeAssessments, initialFeedback],
  )
  const formSourceKey = useMemo(
    () =>
      JSON.stringify({
        assessmentNames: safeAssessments.map((item) => item.competency_name.en),
        feedbackUpdatedAt: initialFeedback?.updated_at ?? null,
      }),
    [safeAssessments, initialFeedback?.updated_at],
  )

  const [overallAgreementScore, setOverallAgreementScore] = useState(
    String(initialFeedback?.overall_agreement_score ?? 0.75),
  )
  const [hrRecommendation, setHrRecommendation] = useState(initialFeedback?.hr_recommendation ?? "")
  const [overallNotes, setOverallNotes] = useState(initialFeedback?.overall_notes ?? "")
  const [missingEvidenceNotes, setMissingEvidenceNotes] = useState(
    initialFeedback?.missing_evidence_notes ?? "",
  )
  const [falsePositiveNotes, setFalsePositiveNotes] = useState(
    initialFeedback?.false_positive_notes ?? "",
  )
  const [falseNegativeNotes, setFalseNegativeNotes] = useState(
    initialFeedback?.false_negative_notes ?? "",
  )
  const [competencies, setCompetencies] = useState(defaultCompetencies)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(
    initialFeedback ? "Đã nạp phản hồi HR mới nhất." : null,
  )

  useEffect(() => {
    setCompetencies(defaultCompetencies)
    setOverallAgreementScore(String(initialFeedback?.overall_agreement_score ?? 0.75))
    setHrRecommendation(initialFeedback?.hr_recommendation ?? "")
    setOverallNotes(initialFeedback?.overall_notes ?? "")
    setMissingEvidenceNotes(initialFeedback?.missing_evidence_notes ?? "")
    setFalsePositiveNotes(initialFeedback?.false_positive_notes ?? "")
    setFalseNegativeNotes(initialFeedback?.false_negative_notes ?? "")
    setSuccess(initialFeedback ? "Đã nạp phản hồi HR mới nhất." : null)
  }, [defaultCompetencies, formSourceKey, initialFeedback])

  async function handleSubmit() {
    setIsSaving(true)
    setError(null)
    setSuccess(null)
    try {
      const payload: InterviewFeedbackRequest = {
        overall_agreement_score: Number(overallAgreementScore),
        hr_recommendation: hrRecommendation.trim() || null,
        overall_notes: overallNotes.trim() || null,
        missing_evidence_notes: missingEvidenceNotes.trim() || null,
        false_positive_notes: falsePositiveNotes.trim() || null,
        false_negative_notes: falseNegativeNotes.trim() || null,
        competencies: competencies.map((item) => ({
          competency_name: item.competency_name,
          hr_score: Number(item.hr_score),
          judgement: item.judgement,
          missing_evidence: item.missing_evidence?.trim() || null,
          notes: item.notes?.trim() || null,
        })),
      }
      const response = await fetch(`${backendBaseUrl}/api/v1/interviews/sessions/${sessionId}/feedback`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      })
      if (!response.ok) {
        const body = (await response.json().catch(() => null)) as { detail?: string } | null
        setError(body?.detail ?? "Không thể lưu phản hồi HR.")
        return
      }
      const saved = (await response.json()) as InterviewFeedbackResponse
      onSaved(saved)
      setSuccess("Đã lưu phản hồi HR. Phiên này giờ có thể ảnh hưởng tới policy phỏng vấn tiếp theo.")
    } catch {
      setError("Không thể kết nối tới backend khi lưu phản hồi HR.")
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div id="hr-feedback-form">
      <ReviewSection
        title="Phản hồi của HR về đánh giá AI"
        description="Ghi lại chênh lệch có cấu trúc, phần còn thiếu bằng chứng và nhận định đã được chỉnh lại để các phiên sau tự hiệu chỉnh policy phỏng vấn."
      >
      <div className="space-y-6">
        <CollapsibleSection title="Tổng quan phản hồi">
          <div className="grid gap-4 md:grid-cols-2">
            <label className="block">
              <span className="text-sm font-semibold text-[var(--color-brand-text-primary)]">Mức đồng thuận tổng thể</span>
              <input
                className="mt-2 w-full rounded-[16px] border border-[var(--color-brand-input-border)] px-4 py-3 text-sm"
                max="1"
                min="0"
                onChange={(event) => setOverallAgreementScore(event.target.value)}
                step="0.05"
                type="number"
                value={overallAgreementScore}
              />
            </label>
            <FormDropdown
              className="block"
              label="Kết luận của HR"
              onChange={setHrRecommendation}
              options={recommendationOptions}
              placeholder="Chọn kết luận"
              value={hrRecommendation}
            />
          </div>
        </CollapsibleSection>

        <CollapsibleSection title="Ghi chú hiệu chỉnh">
          <div className="grid gap-4 lg:grid-cols-2">
            <label className="block">
              <span className="text-sm font-semibold text-[var(--color-brand-text-primary)]">Ghi chú tổng thể</span>
              <textarea
                className="mt-2 min-h-28 w-full rounded-[16px] border border-[var(--color-brand-input-border)] px-4 py-3 text-sm"
                onChange={(event) => setOverallNotes(event.target.value)}
                value={overallNotes}
              />
            </label>
            <label className="block">
              <span className="text-sm font-semibold text-[var(--color-brand-text-primary)]">Ghi chú thiếu bằng chứng</span>
              <textarea
                className="mt-2 min-h-28 w-full rounded-[16px] border border-[var(--color-brand-input-border)] px-4 py-3 text-sm"
                onChange={(event) => setMissingEvidenceNotes(event.target.value)}
                value={missingEvidenceNotes}
              />
            </label>
            <label className="block">
              <span className="text-sm font-semibold text-[var(--color-brand-text-primary)]">Ghi chú khi AI đánh giá quá cao</span>
              <textarea
                className="mt-2 min-h-28 w-full rounded-[16px] border border-[var(--color-brand-input-border)] px-4 py-3 text-sm"
                onChange={(event) => setFalsePositiveNotes(event.target.value)}
                value={falsePositiveNotes}
              />
            </label>
            <label className="block">
              <span className="text-sm font-semibold text-[var(--color-brand-text-primary)]">Ghi chú khi AI đánh giá thiếu</span>
              <textarea
                className="mt-2 min-h-28 w-full rounded-[16px] border border-[var(--color-brand-input-border)] px-4 py-3 text-sm"
                onChange={(event) => setFalseNegativeNotes(event.target.value)}
                value={falseNegativeNotes}
              />
            </label>
          </div>
        </CollapsibleSection>

        <div>
          <h4 className="text-lg font-semibold text-[var(--color-brand-text-primary)]">Rà soát theo từng năng lực</h4>
          {competencies.length ? (
            <div className="mt-4 space-y-4">
              {competencies.map((item, index) => {
                const assessment = safeAssessments[index]
                return (
                  <CollapsibleSection
                    key={item.competency_name.en}
                    title={item.competency_name.vi ?? item.competency_name.en}
                  >
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">{item.competency_name.vi ?? item.competency_name.en}</p>
                        <p className="mt-1 text-xs text-[var(--color-brand-text-muted)]">Mức đánh giá của AI {formatPercent(assessment?.ai_score)} · Độ tin cậy của bằng chứng {formatPercent(assessment?.evidence_strength)}</p>
                      </div>
                      {assessment?.needs_hr_review ? (
                        <span className="rounded-full bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-700">
                          Cần HR xem lại
                        </span>
                      ) : null}
                    </div>
                    <div className="mt-4 grid gap-4 lg:grid-cols-3">
                      <label className="block">
                        <span className="text-xs font-semibold text-[var(--color-brand-text-muted)]">Điểm của HR</span>
                        <input
                          className="mt-2 w-full rounded-[14px] border border-[var(--color-brand-input-border)] px-3 py-2 text-sm"
                          max="1"
                          min="0"
                          onChange={(event) => {
                            const next = [...competencies]
                            next[index] = { ...next[index], hr_score: Number(event.target.value) }
                            setCompetencies(next)
                          }}
                          step="0.05"
                          type="number"
                          value={item.hr_score ?? 0}
                        />
                      </label>
                      <FormDropdown
                        className="block"
                        label="Nhận định"
                        buttonClassName="rounded-[14px] px-3 py-2"
                        onChange={(value) => {
                          const next = [...competencies]
                          next[index] = { ...next[index], judgement: value }
                          setCompetencies(next)
                        }}
                        options={judgementOptions.map((option) => ({
                          value: option,
                          label: formatJudgementLabel(option),
                        }))}
                        placeholder="Chọn nhận định"
                        value={item.judgement}
                      />
                    </div>
                    <div className="mt-4 grid gap-4 lg:grid-cols-2">
                      <label className="block">
                        <span className="text-xs font-semibold text-[var(--color-brand-text-muted)]">Bằng chứng còn thiếu</span>
                        <textarea
                          className="mt-2 min-h-24 w-full rounded-[14px] border border-[var(--color-brand-input-border)] px-3 py-2 text-sm"
                          onChange={(event) => {
                            const next = [...competencies]
                            next[index] = { ...next[index], missing_evidence: event.target.value }
                            setCompetencies(next)
                          }}
                          value={item.missing_evidence ?? ""}
                        />
                      </label>
                      <label className="block">
                        <span className="text-xs font-semibold text-[var(--color-brand-text-muted)]">Ghi chú</span>
                        <textarea
                          className="mt-2 min-h-24 w-full rounded-[14px] border border-[var(--color-brand-input-border)] px-3 py-2 text-sm"
                          onChange={(event) => {
                            const next = [...competencies]
                            next[index] = { ...next[index], notes: event.target.value }
                            setCompetencies(next)
                          }}
                          value={item.notes ?? ""}
                        />
                      </label>
                    </div>
                    {assessment?.notes ? <p className="mt-3 text-sm text-[var(--color-brand-text-muted)]">{assessment.notes}</p> : null}
                  </CollapsibleSection>
                )
              })}
            </div>
          ) : (
            <div className="mt-3">
              <EmptyValue text="Chưa có đánh giá năng lực nào từ AI." />
            </div>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button
            className="rounded-full bg-[var(--color-brand-primary)] px-5 py-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
            disabled={isSaving}
            onClick={() => void handleSubmit()}
            type="button"
          >
            {isSaving ? "Đang lưu..." : "Lưu phản hồi của HR"}
          </button>
          {success ? <p className="text-sm text-emerald-700">{success}</p> : null}
          {error ? <p className="text-sm text-rose-700">{error}</p> : null}
        </div>
        </div>
      </ReviewSection>
    </div>
  )
}
