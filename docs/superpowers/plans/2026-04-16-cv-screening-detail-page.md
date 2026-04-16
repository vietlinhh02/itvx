# CV Screening Detail Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move Phase 2 screening results to a dedicated detail page that survives refresh by loading persisted data from the backend.

**Architecture:** Keep CV upload on the JD detail page, but stop rendering the screening result there. After a successful screening request, redirect to a new dashboard route that fetches the saved screening by `screeningId` and renders the existing Phase 2 result sections from backend data.

**Tech Stack:** Next.js App Router, React client components, TypeScript, existing FastAPI screening API

---

## File structure

- Modify: `frontend/src/components/jd/cv-screening-panel.tsx`
  - Keep only file selection, submit state, inline upload error handling, and redirect on success.
- Create: `frontend/src/components/jd/cv-screening-detail.tsx`
  - Reuse the existing screening presentation components in one server-renderable composition component.
- Create: `frontend/src/app/dashboard/cv-screenings/[screeningId]/page.tsx`
  - Authenticate, fetch the saved screening, handle 404/login/error states, and render the detail view.
- Optional create if needed by Next.js routing: `frontend/src/app/dashboard/cv-screenings/[screeningId]/not-found.tsx`
  - Only add if the default not-found page is not acceptable.

## Task 1: Extract a reusable screening detail view

**Files:**
- Create: `frontend/src/components/jd/cv-screening-detail.tsx`
- Modify: `frontend/src/components/jd/cv-screening-panel.tsx:5-13`
- Test manually in browser after wiring route in later tasks

- [ ] **Step 1: Create the detail composition component**

```tsx
import Link from "next/link"

import { CVCandidateProfile } from "@/components/jd/cv-candidate-profile"
import { CVScreeningAssessments } from "@/components/jd/cv-screening-assessments"
import { CVScreeningAudit } from "@/components/jd/cv-screening-audit"
import { CVScreeningDimensions } from "@/components/jd/cv-screening-dimensions"
import { CVScreeningFollowups } from "@/components/jd/cv-screening-followups"
import { CVScreeningInsights } from "@/components/jd/cv-screening-insights"
import { CVScreeningRisks } from "@/components/jd/cv-screening-risks"
import { CVScreeningSummary } from "@/components/jd/cv-screening-summary"
import type { CVScreeningResponse } from "@/components/jd/cv-screening-types"

type CVScreeningDetailProps = {
  screening: CVScreeningResponse
}

export function CVScreeningDetail({ screening }: CVScreeningDetailProps) {
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
```

- [ ] **Step 2: Remove inline result rendering from the upload panel**

```tsx
import { useRouter } from "next/navigation"
import { useState } from "react"

import type { CVScreeningResponse } from "@/components/jd/cv-screening-types"
import type { JDAnalysisResponse } from "@/components/jd/jd-upload-panel"

export function CVScreeningPanel({ accessToken, backendBaseUrl, jd }: CVScreeningPanelProps) {
  const router = useRouter()
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    // keep existing validation and fetch code

    const payload = (await response.json()) as CVScreeningResponse
    router.push(`/dashboard/cv-screenings/${payload.screening_id}`)
  }

  return (
    <section className="rounded-[24px] bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
      {/* keep only the form and inline error UI */}
    </section>
  )
}
```

- [ ] **Step 3: Run type check to catch missing imports and props**

Run: `cd "/home/eddiesngu/Desktop/Dang/interviewx/frontend" && npm exec tsc --noEmit`
Expected: either PASS or targeted type errors only in the newly touched files

- [ ] **Step 4: Fix any type issues in the new detail component**

```tsx
// Example fixes if TypeScript complains about props or imports:
import type { CVScreeningResponse } from "@/components/jd/cv-screening-types"

type CVScreeningDetailProps = {
  screening: CVScreeningResponse
}
```

- [ ] **Step 5: Re-run type check**

Run: `cd "/home/eddiesngu/Desktop/Dang/interviewx/frontend" && npm exec tsc --noEmit`
Expected: PASS

## Task 2: Add the screening detail page route

**Files:**
- Create: `frontend/src/app/dashboard/cv-screenings/[screeningId]/page.tsx`
- Test manually in browser after implementation

- [ ] **Step 1: Create the new route page with auth and fetch handling**

```tsx
import { notFound, redirect } from "next/navigation"

import { CVScreeningDetail } from "@/components/jd/cv-screening-detail"
import type { CVScreeningResponse } from "@/components/jd/cv-screening-types"
import { auth } from "@/lib/auth"

const backendBaseUrl = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL

type CVScreeningDetailPageProps = {
  params: Promise<{ screeningId: string }>
}

export default async function CVScreeningDetailPage({ params }: CVScreeningDetailPageProps) {
  const session = await auth()

  if (!session?.accessToken || !backendBaseUrl) {
    redirect("/login")
  }

  const { screeningId } = await params
  const response = await fetch(`${backendBaseUrl}/api/v1/cv/screenings/${screeningId}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${session.accessToken}`,
    },
    cache: "no-store",
  })

  if (response.status === 404) {
    notFound()
  }

  if (!response.ok) {
    return (
      <main className="flex w-full flex-col gap-6 py-6">
        <section className="rounded-[24px] bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
          <p className="text-sm font-medium text-red-700">
            Could not load the CV screening result. Please try again.
          </p>
        </section>
      </main>
    )
  }

  const screening = (await response.json()) as CVScreeningResponse
  return <CVScreeningDetail screening={screening} />
}
```

- [ ] **Step 2: Run type check for the new page**

Run: `cd "/home/eddiesngu/Desktop/Dang/interviewx/frontend" && npm exec tsc --noEmit`
Expected: PASS

- [ ] **Step 3: If route typing fails, align it with the existing app-router page pattern**

```tsx
type CVScreeningDetailPageProps = {
  params: Promise<{ screeningId: string }>
}

export default async function CVScreeningDetailPage({ params }: CVScreeningDetailPageProps) {
  const { screeningId } = await params
  // existing fetch logic
}
```

- [ ] **Step 4: Re-run type check**

Run: `cd "/home/eddiesngu/Desktop/Dang/interviewx/frontend" && npm exec tsc --noEmit`
Expected: PASS

## Task 3: Wire upload success to redirect instead of inline rendering

**Files:**
- Modify: `frontend/src/components/jd/cv-screening-panel.tsx:1-130`
- Modify if needed for copy only: `frontend/src/app/dashboard/jd/[id]/page.tsx:39-43`
- Test manually in browser

- [ ] **Step 1: Update the upload panel state and submit flow**

```tsx
"use client"

import { useRouter } from "next/navigation"
import { useState } from "react"

import type { CVScreeningResponse } from "@/components/jd/cv-screening-types"
import type { JDAnalysisResponse } from "@/components/jd/jd-upload-panel"

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
      router.push(`/dashboard/cv-screenings/${payload.screening_id}`)
    } catch {
      setError("Could not reach the backend. Check the API URL and try again.")
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <section className="rounded-[24px] bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
      {/* keep current form layout and error block */}
    </section>
  )
}
```

- [ ] **Step 2: Keep the JD detail page composition unchanged except for consuming the simplified panel**

```tsx
return (
  <main className="flex w-full flex-col gap-6 py-6">
    <JDAnalysisContent result={result} />
    <CVScreeningPanel
      accessToken={session.accessToken}
      backendBaseUrl={backendBaseUrl}
      jd={result}
    />
  </main>
)
```

- [ ] **Step 3: Run type check after redirect wiring**

Run: `cd "/home/eddiesngu/Desktop/Dang/interviewx/frontend" && npm exec tsc --noEmit`
Expected: PASS

- [ ] **Step 4: Start the frontend dev server if it is not already running**

Run: `cd "/home/eddiesngu/Desktop/Dang/interviewx/frontend" && npm run dev`
Expected: Next.js dev server starts successfully

- [ ] **Step 5: Start the backend service if it is not already running**

Run: `cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && python -m uvicorn src.main:app --reload`
Expected: FastAPI server starts and serves the existing CV endpoints

## Task 4: Verify the new flow in the browser

**Files:**
- No code changes required unless issues are found
- Use browser verification against the running app

- [ ] **Step 1: Open the JD detail page and upload a valid CV**

Use the browser to:
1. open one JD detail page
2. upload a valid PDF or DOCX CV
3. submit the Phase 2 form

Expected:
- upload succeeds
- browser navigates to `/dashboard/cv-screenings/<screeningId>`
- the stored screening result renders

- [ ] **Step 2: Refresh the screening detail page**

Use the browser refresh action.

Expected:
- page stays on the same URL
- result still renders after refresh

- [ ] **Step 3: Check the back-navigation path**

Use the `Back to JD detail` link.

Expected:
- user returns to `/dashboard/jd/<jdId>`
- JD content still loads correctly

- [ ] **Step 4: Check a missing-screening URL**

Open `/dashboard/cv-screenings/missing-screening-id`.

Expected:
- not-found page renders

- [ ] **Step 5: If any browser issue appears, fix the minimal code needed and re-run type check**

Run: `cd "/home/eddiesngu/Desktop/Dang/interviewx/frontend" && npm exec tsc --noEmit`
Expected: PASS after the fix

## Task 5: Final verification

**Files:**
- Modify only if verification reveals issues

- [ ] **Step 1: Run one targeted backend API test for screening detail behavior**

Run: `cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && pytest -q backend/tests/api/test_cv_api.py -k screening_detail`
Expected: tests for screening detail route PASS

- [ ] **Step 2: Run one targeted frontend type check**

Run: `cd "/home/eddiesngu/Desktop/Dang/interviewx/frontend" && npm exec tsc --noEmit`
Expected: PASS

- [ ] **Step 3: Review changed files for unnecessary complexity**

Checklist:
- `cv-screening-panel.tsx` no longer owns result rendering
- `cv-screening-detail.tsx` only composes existing presentation blocks
- the new route handles auth, fetch, 404, and compact error state only

- [ ] **Step 4: Prepare the final file list for commit**

Expected changed files:
- `frontend/src/components/jd/cv-screening-panel.tsx`
- `frontend/src/components/jd/cv-screening-detail.tsx`
- `frontend/src/app/dashboard/cv-screenings/[screeningId]/page.tsx`

If extra files changed, confirm they are required before committing.
