"use client"

import type { Route } from "next"
import { useRouter } from "next/navigation"
import { useState } from "react"

import type { CVScreeningResponse } from "@/components/jd/cv-screening-types"
import type { JDAnalysisResponse } from "@/components/jd/jd-upload-panel"

type CVScreeningPanelProps = {
  accessToken: string
  backendBaseUrl: string
  jd: JDAnalysisResponse
}

export function CVScreeningPanel({ accessToken, backendBaseUrl, jd }: CVScreeningPanelProps) {
  const router = useRouter()
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
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
        setError(payload?.detail ?? "CV screening failed. Please try again.")
        return
      }

      const payload = (await response.json()) as CVScreeningResponse
      router.push(buildScreeningRoute(payload.screening_id))
    } catch {
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
        <label className="flex flex-col gap-2 text-sm font-medium text-[var(--color-brand-text-primary)]">
          CV file
          <input
            accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            className="rounded-[12px] border border-[var(--color-brand-input-border)] bg-white px-4 py-3 text-sm text-[var(--color-brand-text-primary)] outline-none"
            onChange={(event) => {
              setSelectedFile(event.target.files?.[0] ?? null)
              setError(null)
            }}
            type="file"
          />
        </label>
        <div className="flex flex-wrap items-center gap-3">
          <button
            className="w-fit rounded-[50px] bg-[var(--color-brand-primary)] px-5 py-3 text-sm font-semibold text-white transition disabled:cursor-not-allowed disabled:opacity-60"
            disabled={isSubmitting}
            type="submit"
          >
            {isSubmitting ? "Screening..." : "Upload and screen CV"}
          </button>
          <p className="text-sm text-[var(--color-brand-text-muted)]">
            {selectedFile ? `Selected: ${selectedFile.name}` : "Supported formats: PDF and DOCX"}
          </p>
        </div>
        {error ? <p className="rounded-[12px] bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p> : null}
      </form>

    </section>
  )
}

function buildScreeningRoute(screeningId: string): Route {
  return `/dashboard/cv-screenings/${screeningId}` as Route
}
