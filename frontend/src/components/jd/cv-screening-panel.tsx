"use client"

import { useState } from "react"

import type { JDAnalysisResponse } from "@/components/jd/jd-upload-panel"

type BilingualText = {
  vi: string
  en: string
}

type CVScreeningResponse = {
  screening_id: string
  jd_id: string
  candidate_id: string
  file_name: string
  status: "completed"
  created_at: string
  result: {
    match_score: number
    recommendation: "advance" | "review" | "reject"
    decision_reason: BilingualText
    minimum_requirement_checks: Array<{
      criterion: BilingualText
      status: "met" | "not_met" | "unclear"
      reason: BilingualText
      evidence: BilingualText[]
    }>
    dimension_scores: Array<{
      dimension_name: BilingualText
      priority: string
      weight: number
      score: number
      reason: BilingualText
      evidence: BilingualText[]
    }>
    strengths: Array<{
      title: BilingualText
      reason: BilingualText
      evidence: BilingualText[]
    }>
    gaps: Array<{
      title: BilingualText
      reason: BilingualText
      evidence: BilingualText[]
    }>
    uncertainties: Array<{
      title: BilingualText
      reason: BilingualText
      follow_up_suggestion: BilingualText
    }>
  }
}

type CVScreeningPanelProps = {
  accessToken: string
  backendBaseUrl: string
  jd: JDAnalysisResponse
}

export function CVScreeningPanel({ accessToken, backendBaseUrl, jd }: CVScreeningPanelProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [result, setResult] = useState<CVScreeningResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (!selectedFile) {
      setError("Please choose a PDF or DOCX CV before screening.")
      return
    }

    setIsSubmitting(true)
    setError(null)

    const formData = new FormData()
    formData.append("jd_id", jd.jd_id)
    formData.append("file", selectedFile)

    try {
      const response = await fetch(`${backendBaseUrl}/api/v1/cv/screen`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
        body: formData,
      })

      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as { detail?: string } | null
        setResult(null)
        setError(payload?.detail ?? "CV screening failed. Please try again.")
        return
      }

      const payload = (await response.json()) as CVScreeningResponse
      setResult(payload)
    } catch {
      setResult(null)
      setError("Could not reach the backend. Check the API URL and try again.")
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <section className="rounded-[24px] bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
      <div>
        <p className="text-sm font-medium text-[var(--color-brand-text-muted)]">Phase 2 - CV Screening</p>
        <h2 className="mt-2 text-2xl font-semibold text-[var(--color-brand-text-primary)]">
          Screen one CV against this JD
        </h2>
        <p className="mt-2 text-sm leading-6 text-[var(--color-brand-text-body)]">
          Upload one CV and review the AI screening recommendation, evidence, and uncertainty for HR review.
        </p>
      </div>

      <form className="mt-6 flex flex-col gap-4" onSubmit={handleSubmit}>
        <input
          accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          className="rounded-[12px] border border-[var(--color-brand-input-border)] bg-white px-4 py-3 text-sm text-[var(--color-brand-text-primary)] outline-none"
          onChange={(event) => {
            setSelectedFile(event.target.files?.[0] ?? null)
            setError(null)
          }}
          type="file"
        />
        <button
          className="w-fit rounded-[50px] bg-[var(--color-brand-primary)] px-5 py-3 text-sm font-semibold text-white transition disabled:cursor-not-allowed disabled:opacity-60"
          disabled={isSubmitting}
          type="submit"
        >
          {isSubmitting ? "Screening..." : "Upload and screen CV"}
        </button>
        {error ? <p className="rounded-[12px] bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p> : null}
      </form>

      {result ? (
        <div className="mt-6 space-y-4">
          <div className="rounded-[16px] bg-[var(--color-primary-50)] p-4">
            <p className="text-sm font-semibold text-[var(--color-brand-primary)]">
              Recommendation: {result.result.recommendation}
            </p>
            <p className="mt-2 text-sm text-[var(--color-brand-text-body)]">Score: {result.result.match_score}</p>
            <p className="mt-2 text-sm text-[var(--color-brand-text-body)]">
              {result.result.decision_reason.en}
            </p>
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <ResultList
              title="Minimum requirement checks"
              items={result.result.minimum_requirement_checks.map((item) => `${item.criterion.en}: ${item.status}`)}
            />
            <ResultList
              title="Dimension scores"
              items={result.result.dimension_scores.map((item) => `${item.dimension_name.en}: ${item.score}`)}
            />
            <ResultList title="Strengths" items={result.result.strengths.map((item) => item.title.en)} />
            <ResultList title="Gaps" items={result.result.gaps.map((item) => item.title.en)} />
            <ResultList title="Uncertainties" items={result.result.uncertainties.map((item) => item.title.en)} />
          </div>
        </div>
      ) : null}
    </section>
  )
}

function ResultList({ title, items }: { title: string; items: string[] }) {
  return (
    <article className="rounded-[16px] border border-[var(--color-brand-input-border)] p-4">
      <h3 className="text-base font-semibold text-[var(--color-brand-text-primary)]">{title}</h3>
      <ul className="mt-3 space-y-2 text-sm text-[var(--color-brand-text-body)]">
        {items.length ? items.map((item) => <li key={item}>{item}</li>) : <li>None</li>}
      </ul>
    </article>
  )
}
