# CV Screening Phase 2 Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update the frontend CV screening UI to fully consume the Phase 2 backend response and render a full HR review dossier using smaller, focused components.

**Architecture:** Keep `frontend/src/app/dashboard/jd/[id]/page.tsx` as the entry point and keep `frontend/src/components/jd/cv-screening-panel.tsx` as the upload container and state owner. Move the response contract into a dedicated types file and split rendering into focused sections for summary, candidate profile, assessments, dimensions, insights, follow-ups, risks, and audit metadata.

**Tech Stack:** Next.js App Router, React 19, TypeScript, existing dashboard component styling, ESLint, TypeScript compiler

---

## Planned File Structure

- Create: `frontend/src/components/jd/cv-screening-types.ts`
  - Define the full Phase 2 backend response contract and shared UI-facing types.
- Create: `frontend/src/components/jd/cv-screening-ui.tsx`
  - Hold small shared display helpers like section wrappers, status badges, and bilingual/evidence rendering.
- Create: `frontend/src/components/jd/cv-screening-summary.tsx`
  - Render recommendation, score, summary, and decision reason.
- Create: `frontend/src/components/jd/cv-candidate-profile.tsx`
  - Render the extracted candidate profile snapshot.
- Create: `frontend/src/components/jd/cv-screening-assessments.tsx`
  - Render knockout and minimum requirement assessments.
- Create: `frontend/src/components/jd/cv-screening-dimensions.tsx`
  - Render rubric dimension scores, evidence, and confidence notes.
- Create: `frontend/src/components/jd/cv-screening-insights.tsx`
  - Render strengths, gaps, and uncertainties.
- Create: `frontend/src/components/jd/cv-screening-followups.tsx`
  - Render follow-up questions.
- Create: `frontend/src/components/jd/cv-screening-risks.tsx`
  - Render risk flags.
- Create: `frontend/src/components/jd/cv-screening-audit.tsx`
  - Render audit metadata.
- Modify: `frontend/src/components/jd/cv-screening-panel.tsx`
  - Update request/response typing and compose the new Phase 2 sections.
- Verify only: `frontend/src/app/dashboard/jd/[id]/page.tsx`
  - Confirm the existing page integration remains correct without code changes.

### Task 1: Add the Phase 2 frontend response contract

**Files:**
- Create: `frontend/src/components/jd/cv-screening-types.ts`
- Modify: `frontend/src/components/jd/cv-screening-panel.tsx`

- [ ] **Step 1: Write the failing type import in the panel**

```tsx
import type { CVScreeningResponse } from "@/components/jd/cv-screening-types"
```

Add it near the top of `frontend/src/components/jd/cv-screening-panel.tsx` and remove the old inline `CVScreeningResponse` type definition.

- [ ] **Step 2: Run type-check to verify it fails**

Run: `npm --prefix frontend run type-check`
Expected: FAIL with `Cannot find module '@/components/jd/cv-screening-types'`.

- [ ] **Step 3: Create `frontend/src/components/jd/cv-screening-types.ts`**

```tsx
export type BilingualText = {
  vi: string
  en: string
}

export type RequirementStatus = "met" | "not_met" | "unclear"
export type ScreeningRecommendation = "advance" | "review" | "reject"
export type RiskSeverity = "low" | "medium" | "high"

export type CandidateSummary = {
  full_name: string | null
  current_title: string | null
  location: string | null
  total_years_experience: number | null
  seniority_signal: "intern" | "junior" | "mid" | "senior" | "lead" | "manager" | "unknown"
  professional_summary: BilingualText | null
}

export type WorkExperienceItem = {
  company: string
  role: string
  start_date_text: string | null
  end_date_text: string | null
  duration_text: string | null
  responsibilities: string[]
  achievements: string[]
  technologies: string[]
  evidence_excerpts: string[]
  ambiguity_notes: string[]
}

export type ProjectItem = {
  name: string | null
  role: string | null
  summary: string
  technologies: string[]
  domain_context: string | null
  evidence_excerpts: string[]
}

export type SkillEvidenceItem = {
  skill_name: string
  proficiency_signal: string | null
  evidence_excerpts: string[]
  source_section: "experience" | "project" | "summary" | "skills" | "other"
}

export type EducationItem = {
  institution: string
  degree: string | null
  field_of_study: string | null
  graduation_text: string | null
  evidence_excerpts: string[]
}

export type CertificationItem = {
  name: string
  issuer: string | null
  date_text: string | null
  evidence_excerpts: string[]
}

export type LanguageItem = {
  language_name: string
  proficiency_signal: string | null
  evidence_excerpts: string[]
}

export type ProfileUncertainty = {
  title: BilingualText
  reason: BilingualText
  impact: BilingualText
}

export type CandidateProfile = {
  candidate_summary: CandidateSummary
  work_experience: WorkExperienceItem[]
  projects: ProjectItem[]
  skills_inventory: SkillEvidenceItem[]
  education: EducationItem[]
  certifications: CertificationItem[]
  languages: LanguageItem[]
  profile_uncertainties: ProfileUncertainty[]
}

export type RequirementAssessment = {
  criterion: BilingualText
  status: RequirementStatus
  reason: BilingualText
  evidence: BilingualText[]
}

export type DimensionScore = {
  dimension_name: BilingualText
  priority: "must_have" | "important" | "nice_to_have"
  weight: number
  score: number
  reason: BilingualText
  evidence: BilingualText[]
  confidence_note: BilingualText | null
}

export type ScreeningInsight = {
  title: BilingualText
  reason: BilingualText
  evidence: BilingualText[]
}

export type ScreeningUncertainty = {
  title: BilingualText
  reason: BilingualText
  follow_up_suggestion: BilingualText
}

export type FollowUpQuestion = {
  question: BilingualText
  purpose: BilingualText
  linked_dimension: BilingualText | null
}

export type RiskFlag = {
  title: BilingualText
  reason: BilingualText
  severity: RiskSeverity
}

export type AuditMetadata = {
  extraction_model: string
  screening_model: string
  profile_schema_version: string
  screening_schema_version: string
  generated_at: string
  reconciliation_notes: string[]
  consistency_flags: string[]
}

export type CVScreeningResponse = {
  screening_id: string
  jd_id: string
  candidate_id: string
  file_name: string
  status: "completed"
  created_at: string
  candidate_profile: CandidateProfile
  result: {
    match_score: number
    recommendation: ScreeningRecommendation
    decision_reason: BilingualText
    screening_summary: BilingualText
    knockout_assessments: RequirementAssessment[]
    minimum_requirement_checks: RequirementAssessment[]
    dimension_scores: DimensionScore[]
    strengths: ScreeningInsight[]
    gaps: ScreeningInsight[]
    uncertainties: ScreeningUncertainty[]
    follow_up_questions: FollowUpQuestion[]
    risk_flags: RiskFlag[]
  }
  audit: AuditMetadata
}
```

- [ ] **Step 4: Update the panel import and state typing**

Replace the inline response type in `frontend/src/components/jd/cv-screening-panel.tsx` with:

```tsx
import { useState } from "react"

import type { JDAnalysisResponse } from "@/components/jd/jd-upload-panel"
import type { CVScreeningResponse } from "@/components/jd/cv-screening-types"
```

Keep the existing state declaration:

```tsx
const [result, setResult] = useState<CVScreeningResponse | null>(null)
```

- [ ] **Step 5: Run type-check to verify it passes**

Run: `npm --prefix frontend run type-check`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/jd/cv-screening-types.ts frontend/src/components/jd/cv-screening-panel.tsx
git commit -m "feat(frontend): add phase 2 cv screening types"
```

### Task 2: Add shared UI helpers for Phase 2 rendering

**Files:**
- Create: `frontend/src/components/jd/cv-screening-ui.tsx`

- [ ] **Step 1: Create the shared UI helper file**

```tsx
import { ShieldWarning, Sparkle, Target } from "@phosphor-icons/react"

import type { BilingualText, RequirementStatus, RiskSeverity } from "@/components/jd/cv-screening-types"

export function ReviewSection({
  title,
  description,
  children,
}: {
  title: string
  description: string
  children: React.ReactNode
}) {
  return (
    <section className="rounded-[24px] bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
      <div>
        <h3 className="text-2xl font-semibold text-[var(--color-brand-text-primary)]">{title}</h3>
        <p className="mt-2 text-sm leading-6 text-[var(--color-brand-text-body)]">{description}</p>
      </div>
      <div className="mt-5">{children}</div>
    </section>
  )
}

export function BilingualBlock({ value }: { value: BilingualText }) {
  return (
    <div>
      <p className="text-sm font-medium text-[var(--color-brand-text-primary)]">{value.en}</p>
      <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">{value.vi}</p>
    </div>
  )
}

export function StatusBadge({ status }: { status: RequirementStatus }) {
  const config =
    status === "met"
      ? "bg-emerald-50 text-emerald-700"
      : status === "not_met"
        ? "bg-rose-50 text-rose-700"
        : "bg-amber-50 text-amber-700"

  return (
    <span className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] ${config}`}>
      {status.replace("_", " ")}
    </span>
  )
}

export function PriorityBadge({ priority }: { priority: string }) {
  const config =
    priority === "must_have"
      ? { label: "Must have", icon: ShieldWarning, className: "bg-rose-50 text-rose-700" }
      : priority === "important"
        ? { label: "Important", icon: Target, className: "bg-sky-50 text-sky-700" }
        : { label: "Nice to have", icon: Sparkle, className: "bg-violet-50 text-violet-700" }

  const Icon = config.icon

  return (
    <span className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] ${config.className}`}>
      <span className="flex items-center gap-1.5">
        <Icon size={12} weight="fill" />
        {config.label}
      </span>
    </span>
  )
}

export function RiskBadge({ severity }: { severity: RiskSeverity }) {
  const className =
    severity === "high"
      ? "bg-rose-50 text-rose-700"
      : severity === "medium"
        ? "bg-amber-50 text-amber-700"
        : "bg-slate-100 text-slate-700"

  return (
    <span className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] ${className}`}>
      {severity}
    </span>
  )
}

export function EvidenceList({ items }: { items: BilingualText[] }) {
  if (!items.length) {
    return <p className="text-sm text-[var(--color-brand-text-muted)]">No evidence</p>
  }

  return (
    <ul className="mt-3 space-y-2">
      {items.map((item) => (
        <li className="rounded-[14px] bg-[var(--color-primary-50)] px-3 py-2" key={`${item.en}-${item.vi}`}>
          <BilingualBlock value={item} />
        </li>
      ))}
    </ul>
  )
}

export function EmptyValue({ text = "None" }: { text?: string }) {
  return <p className="text-sm text-[var(--color-brand-text-muted)]">{text}</p>
}
```

- [ ] **Step 2: Run type-check to verify the helper file compiles**

Run: `npm --prefix frontend run type-check`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/jd/cv-screening-ui.tsx
git commit -m "feat(frontend): add cv screening ui helpers"
```

### Task 3: Build the summary and candidate profile sections

**Files:**
- Create: `frontend/src/components/jd/cv-screening-summary.tsx`
- Create: `frontend/src/components/jd/cv-candidate-profile.tsx`
- Modify: `frontend/src/components/jd/cv-screening-panel.tsx`

- [ ] **Step 1: Create the summary component**

```tsx
import type { CVScreeningResponse } from "@/components/jd/cv-screening-types"
import { ReviewSection } from "@/components/jd/cv-screening-ui"

export function CVScreeningSummary({ result }: { result: CVScreeningResponse["result"] }) {
  const scorePercentage = `${Math.round(result.match_score * 100)}%`

  return (
    <ReviewSection
      title="Screening Summary"
      description="Top-level recommendation, score, and summary for HR review."
    >
      <div className="space-y-4">
        <div className="rounded-[16px] bg-[var(--color-primary-50)] p-4">
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[var(--color-brand-primary)]">
            Recommendation
          </p>
          <p className="mt-2 text-2xl font-semibold capitalize text-[var(--color-brand-text-primary)]">
            {result.recommendation}
          </p>
          <p className="mt-3 text-sm font-medium text-[var(--color-brand-text-primary)]">
            Match score: {scorePercentage}
          </p>
        </div>
        <article>
          <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">Screening summary</p>
          <p className="mt-2 text-sm text-[var(--color-brand-text-body)]">{result.screening_summary.en}</p>
          <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">{result.screening_summary.vi}</p>
        </article>
        <article>
          <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">Decision reason</p>
          <p className="mt-2 text-sm text-[var(--color-brand-text-body)]">{result.decision_reason.en}</p>
          <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">{result.decision_reason.vi}</p>
        </article>
      </div>
    </ReviewSection>
  )
}
```

- [ ] **Step 2: Create the candidate profile component**

```tsx
import type { CandidateProfile } from "@/components/jd/cv-screening-types"
import { EmptyValue, ReviewSection } from "@/components/jd/cv-screening-ui"

export function CVCandidateProfile({ profile }: { profile: CandidateProfile }) {
  return (
    <ReviewSection
      title="Candidate Profile"
      description="Structured candidate profile extracted from the uploaded CV."
    >
      <div className="space-y-6">
        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <ProfileFact label="Full name" value={profile.candidate_summary.full_name} />
          <ProfileFact label="Current title" value={profile.candidate_summary.current_title} />
          <ProfileFact label="Location" value={profile.candidate_summary.location} />
          <ProfileFact
            label="Years of experience"
            value={
              profile.candidate_summary.total_years_experience === null
                ? null
                : String(profile.candidate_summary.total_years_experience)
            }
          />
        </section>

        <section>
          <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">Professional summary</p>
          {profile.candidate_summary.professional_summary ? (
            <>
              <p className="mt-2 text-sm text-[var(--color-brand-text-body)]">
                {profile.candidate_summary.professional_summary.en}
              </p>
              <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">
                {profile.candidate_summary.professional_summary.vi}
              </p>
            </>
          ) : (
            <div className="mt-2">
              <EmptyValue text="Not provided" />
            </div>
          )}
        </section>

        <EntityList
          title="Work experience"
          items={profile.work_experience.map((item) => ({
            key: `${item.company}-${item.role}`,
            title: `${item.role} at ${item.company}`,
            meta: item.duration_text,
            details: [...item.responsibilities, ...item.achievements],
          }))}
        />

        <EntityList
          title="Projects"
          items={profile.projects.map((item, index) => ({
            key: `${item.name ?? item.summary}-${index}`,
            title: item.name ?? item.summary,
            meta: item.role,
            details: [item.summary, ...(item.technologies.length ? [`Tech: ${item.technologies.join(", ")}`] : [])],
          }))}
        />

        <StringChipSection
          title="Skills inventory"
          items={profile.skills_inventory.map((item) => item.skill_name)}
        />
        <StringChipSection title="Languages" items={profile.languages.map((item) => item.language_name)} />
        <StringChipSection title="Certifications" items={profile.certifications.map((item) => item.name)} />
        <StringChipSection title="Education" items={profile.education.map((item) => item.institution)} />

        <EntityList
          title="Profile uncertainties"
          items={profile.profile_uncertainties.map((item) => ({
            key: item.title.en,
            title: item.title.en,
            meta: item.title.vi,
            details: [item.reason.en, item.impact.en],
          }))}
          emptyText="No profile uncertainties"
        />
      </div>
    </ReviewSection>
  )
}

function ProfileFact({ label, value }: { label: string; value: string | null }) {
  return (
    <article className="rounded-[16px] border border-[var(--color-brand-input-border)] p-4">
      <p className="text-xs uppercase tracking-[0.18em] text-[var(--color-brand-text-muted)]">{label}</p>
      <p className="mt-2 text-sm font-medium text-[var(--color-brand-text-primary)]">{value ?? "Not provided"}</p>
    </article>
  )
}

function EntityList({
  title,
  items,
  emptyText = "None",
}: {
  title: string
  items: Array<{ key: string; title: string; meta: string | null | undefined; details: string[] }>
  emptyText?: string
}) {
  return (
    <section>
      <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">{title}</p>
      <div className="mt-3 space-y-3">
        {items.length ? (
          items.map((item) => (
            <article className="rounded-[16px] border border-[var(--color-brand-input-border)] p-4" key={item.key}>
              <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">{item.title}</p>
              {item.meta ? <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">{item.meta}</p> : null}
              <ul className="mt-3 space-y-2 text-sm text-[var(--color-brand-text-body)]">
                {item.details.map((detail) => (
                  <li key={detail}>{detail}</li>
                ))}
              </ul>
            </article>
          ))
        ) : (
          <EmptyValue text={emptyText} />
        )}
      </div>
    </section>
  )
}

function StringChipSection({ title, items }: { title: string; items: string[] }) {
  return (
    <section>
      <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">{title}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        {items.length ? (
          items.map((item) => (
            <span
              className="rounded-full bg-[var(--color-primary-50)] px-3 py-2 text-sm text-[var(--color-brand-primary)]"
              key={item}
            >
              {item}
            </span>
          ))
        ) : (
          <EmptyValue text="None" />
        )}
      </div>
    </section>
  )
}
```

- [ ] **Step 3: Update the panel to render the new top sections**

Add these imports to `frontend/src/components/jd/cv-screening-panel.tsx`:

```tsx
import { CVCandidateProfile } from "@/components/jd/cv-candidate-profile"
import { CVScreeningSummary } from "@/components/jd/cv-screening-summary"
```

Replace the current result rendering block with:

```tsx
      {result ? (
        <div className="mt-6 space-y-6">
          <CVScreeningSummary result={result.result} />
          <CVCandidateProfile profile={result.candidate_profile} />
        </div>
      ) : null}
```

- [ ] **Step 4: Run type-check to verify the first two sections compile**

Run: `npm --prefix frontend run type-check`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/jd/cv-screening-summary.tsx frontend/src/components/jd/cv-candidate-profile.tsx frontend/src/components/jd/cv-screening-panel.tsx
git commit -m "feat(frontend): render cv screening summary and candidate profile"
```

### Task 4: Build the assessment and dimension sections

**Files:**
- Create: `frontend/src/components/jd/cv-screening-assessments.tsx`
- Create: `frontend/src/components/jd/cv-screening-dimensions.tsx`
- Modify: `frontend/src/components/jd/cv-screening-panel.tsx`

- [ ] **Step 1: Create the assessments component**

```tsx
import type { CVScreeningResponse } from "@/components/jd/cv-screening-types"
import { BilingualBlock, EmptyValue, EvidenceList, ReviewSection, StatusBadge } from "@/components/jd/cv-screening-ui"

export function CVScreeningAssessments({
  knockoutAssessments,
  minimumRequirements,
}: {
  knockoutAssessments: CVScreeningResponse["result"]["knockout_assessments"]
  minimumRequirements: CVScreeningResponse["result"]["minimum_requirement_checks"]
}) {
  return (
    <ReviewSection
      title="Requirement Assessments"
      description="Knockout and minimum requirement checks used for the final recommendation."
    >
      <div className="grid gap-6 xl:grid-cols-2">
        <AssessmentGroup items={knockoutAssessments} title="Knockout assessments" emptyText="No knockout rules" />
        <AssessmentGroup
          items={minimumRequirements}
          title="Minimum requirements"
          emptyText="No minimum requirements"
        />
      </div>
    </ReviewSection>
  )
}

function AssessmentGroup({
  title,
  items,
  emptyText,
}: {
  title: string
  items: CVScreeningResponse["result"]["knockout_assessments"]
  emptyText: string
}) {
  return (
    <section>
      <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">{title}</p>
      <div className="mt-3 space-y-3">
        {items.length ? (
          items.map((item) => (
            <article className="rounded-[16px] border border-[var(--color-brand-input-border)] p-4" key={item.criterion.en}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <BilingualBlock value={item.criterion} />
                <StatusBadge status={item.status} />
              </div>
              <div className="mt-3">
                <p className="text-sm text-[var(--color-brand-text-body)]">{item.reason.en}</p>
                <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">{item.reason.vi}</p>
              </div>
              <EvidenceList items={item.evidence} />
            </article>
          ))
        ) : (
          <EmptyValue text={emptyText} />
        )}
      </div>
    </section>
  )
}
```

- [ ] **Step 2: Create the dimensions component**

```tsx
import type { CVScreeningResponse } from "@/components/jd/cv-screening-types"
import { BilingualBlock, EmptyValue, EvidenceList, PriorityBadge, ReviewSection } from "@/components/jd/cv-screening-ui"

export function CVScreeningDimensions({
  dimensions,
}: {
  dimensions: CVScreeningResponse["result"]["dimension_scores"]
}) {
  return (
    <ReviewSection
      title="Rubric Dimension Scores"
      description="Weighted dimension-by-dimension assessment from the backend screening engine."
    >
      <div className="space-y-4">
        {dimensions.length ? (
          dimensions.map((dimension) => (
            <article className="rounded-[16px] border border-[var(--color-brand-input-border)] p-4" key={dimension.dimension_name.en}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <BilingualBlock value={dimension.dimension_name} />
                <PriorityBadge priority={dimension.priority} />
              </div>
              <div className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                <Metric label="Weight" value={String(dimension.weight)} />
                <Metric label="Score" value={`${Math.round(dimension.score * 100)}%`} />
                <Metric label="Priority" value={dimension.priority.replaceAll("_", " ")} />
              </div>
              <div className="mt-4">
                <p className="text-sm text-[var(--color-brand-text-body)]">{dimension.reason.en}</p>
                <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">{dimension.reason.vi}</p>
              </div>
              {dimension.confidence_note ? (
                <div className="mt-4 rounded-[14px] bg-[var(--color-primary-50)] px-3 py-2">
                  <p className="text-sm font-medium text-[var(--color-brand-text-primary)]">
                    {dimension.confidence_note.en}
                  </p>
                  <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">
                    {dimension.confidence_note.vi}
                  </p>
                </div>
              ) : null}
              <EvidenceList items={dimension.evidence} />
            </article>
          ))
        ) : (
          <EmptyValue text="No dimension scores" />
        )}
      </div>
    </ReviewSection>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[14px] bg-[var(--color-primary-50)] px-3 py-2">
      <p className="text-xs uppercase tracking-[0.18em] text-[var(--color-brand-text-muted)]">{label}</p>
      <p className="mt-2 text-sm font-medium capitalize text-[var(--color-brand-text-primary)]">{value}</p>
    </div>
  )
}
```

- [ ] **Step 3: Update the panel to render assessments and dimensions**

Add imports:

```tsx
import { CVScreeningAssessments } from "@/components/jd/cv-screening-assessments"
import { CVScreeningDimensions } from "@/components/jd/cv-screening-dimensions"
```

Update the result block to:

```tsx
      {result ? (
        <div className="mt-6 space-y-6">
          <CVScreeningSummary result={result.result} />
          <CVCandidateProfile profile={result.candidate_profile} />
          <CVScreeningAssessments
            knockoutAssessments={result.result.knockout_assessments}
            minimumRequirements={result.result.minimum_requirement_checks}
          />
          <CVScreeningDimensions dimensions={result.result.dimension_scores} />
        </div>
      ) : null}
```

- [ ] **Step 4: Run type-check to verify the middle sections compile**

Run: `npm --prefix frontend run type-check`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/jd/cv-screening-assessments.tsx frontend/src/components/jd/cv-screening-dimensions.tsx frontend/src/components/jd/cv-screening-panel.tsx
git commit -m "feat(frontend): render cv screening assessments and dimensions"
```

### Task 5: Build insights, follow-up questions, risk flags, and audit sections

**Files:**
- Create: `frontend/src/components/jd/cv-screening-insights.tsx`
- Create: `frontend/src/components/jd/cv-screening-followups.tsx`
- Create: `frontend/src/components/jd/cv-screening-risks.tsx`
- Create: `frontend/src/components/jd/cv-screening-audit.tsx`
- Modify: `frontend/src/components/jd/cv-screening-panel.tsx`

- [ ] **Step 1: Create the insights component**

```tsx
import type { CVScreeningResponse } from "@/components/jd/cv-screening-types"
import { EmptyValue, EvidenceList, ReviewSection } from "@/components/jd/cv-screening-ui"

export function CVScreeningInsights({
  strengths,
  gaps,
  uncertainties,
}: {
  strengths: CVScreeningResponse["result"]["strengths"]
  gaps: CVScreeningResponse["result"]["gaps"]
  uncertainties: CVScreeningResponse["result"]["uncertainties"]
}) {
  return (
    <ReviewSection
      title="Insights"
      description="Strengths, gaps, and unresolved uncertainties extracted from the screening output."
    >
      <div className="grid gap-6 xl:grid-cols-3">
        <InsightGroup items={strengths} title="Strengths" emptyText="No strengths" />
        <InsightGroup items={gaps} title="Gaps" emptyText="No gaps" />
        <UncertaintyGroup items={uncertainties} />
      </div>
    </ReviewSection>
  )
}

function InsightGroup({
  title,
  items,
  emptyText,
}: {
  title: string
  items: CVScreeningResponse["result"]["strengths"]
  emptyText: string
}) {
  return (
    <section>
      <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">{title}</p>
      <div className="mt-3 space-y-3">
        {items.length ? (
          items.map((item) => (
            <article className="rounded-[16px] border border-[var(--color-brand-input-border)] p-4" key={item.title.en}>
              <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">{item.title.en}</p>
              <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">{item.title.vi}</p>
              <p className="mt-3 text-sm text-[var(--color-brand-text-body)]">{item.reason.en}</p>
              <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">{item.reason.vi}</p>
              <EvidenceList items={item.evidence} />
            </article>
          ))
        ) : (
          <EmptyValue text={emptyText} />
        )}
      </div>
    </section>
  )
}

function UncertaintyGroup({
  items,
}: {
  items: CVScreeningResponse["result"]["uncertainties"]
}) {
  return (
    <section>
      <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">Uncertainties</p>
      <div className="mt-3 space-y-3">
        {items.length ? (
          items.map((item) => (
            <article className="rounded-[16px] border border-[var(--color-brand-input-border)] p-4" key={item.title.en}>
              <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">{item.title.en}</p>
              <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">{item.title.vi}</p>
              <p className="mt-3 text-sm text-[var(--color-brand-text-body)]">{item.reason.en}</p>
              <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">{item.reason.vi}</p>
              <p className="mt-3 text-sm font-medium text-[var(--color-brand-text-primary)]">
                Follow-up: {item.follow_up_suggestion.en}
              </p>
              <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">
                {item.follow_up_suggestion.vi}
              </p>
            </article>
          ))
        ) : (
          <EmptyValue text="No uncertainties" />
        )}
      </div>
    </section>
  )
}
```

- [ ] **Step 2: Create the follow-up, risk, and audit components**

```tsx
// frontend/src/components/jd/cv-screening-followups.tsx
import type { CVScreeningResponse } from "@/components/jd/cv-screening-types"
import { EmptyValue, ReviewSection } from "@/components/jd/cv-screening-ui"

export function CVScreeningFollowups({
  items,
}: {
  items: CVScreeningResponse["result"]["follow_up_questions"]
}) {
  return (
    <ReviewSection
      title="Follow-up Questions"
      description="Suggested interviewer prompts grounded in the screening output."
    >
      <div className="space-y-3">
        {items.length ? (
          items.map((item) => (
            <article className="rounded-[16px] border border-[var(--color-brand-input-border)] p-4" key={item.question.en}>
              <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">{item.question.en}</p>
              <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">{item.question.vi}</p>
              <p className="mt-3 text-sm text-[var(--color-brand-text-body)]">{item.purpose.en}</p>
              <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">{item.purpose.vi}</p>
              {item.linked_dimension ? (
                <p className="mt-3 text-sm font-medium text-[var(--color-brand-text-primary)]">
                  Linked dimension: {item.linked_dimension.en}
                </p>
              ) : null}
            </article>
          ))
        ) : (
          <EmptyValue text="No follow-up questions" />
        )}
      </div>
    </ReviewSection>
  )
}
```

```tsx
// frontend/src/components/jd/cv-screening-risks.tsx
import type { CVScreeningResponse } from "@/components/jd/cv-screening-types"
import { EmptyValue, ReviewSection, RiskBadge } from "@/components/jd/cv-screening-ui"

export function CVScreeningRisks({
  items,
}: {
  items: CVScreeningResponse["result"]["risk_flags"]
}) {
  return (
    <ReviewSection
      title="Risk Flags"
      description="Explicit screening warnings that HR should review carefully."
    >
      <div className="space-y-3">
        {items.length ? (
          items.map((item) => (
            <article className="rounded-[16px] border border-[var(--color-brand-input-border)] p-4" key={item.title.en}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">{item.title.en}</p>
                  <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">{item.title.vi}</p>
                </div>
                <RiskBadge severity={item.severity} />
              </div>
              <p className="mt-3 text-sm text-[var(--color-brand-text-body)]">{item.reason.en}</p>
              <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">{item.reason.vi}</p>
            </article>
          ))
        ) : (
          <EmptyValue text="No risk flags" />
        )}
      </div>
    </ReviewSection>
  )
}
```

```tsx
// frontend/src/components/jd/cv-screening-audit.tsx
import type { AuditMetadata } from "@/components/jd/cv-screening-types"
import { EmptyValue, ReviewSection } from "@/components/jd/cv-screening-ui"

export function CVScreeningAudit({ audit }: { audit: AuditMetadata }) {
  return (
    <ReviewSection
      title="Audit Metadata"
      description="Extraction and screening metadata returned by the backend."
    >
      <div className="space-y-6">
        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <AuditFact label="Extraction model" value={audit.extraction_model} />
          <AuditFact label="Screening model" value={audit.screening_model} />
          <AuditFact label="Generated at" value={audit.generated_at} />
          <AuditFact label="Profile schema version" value={audit.profile_schema_version} />
          <AuditFact label="Screening schema version" value={audit.screening_schema_version} />
        </section>
        <AuditList title="Reconciliation notes" items={audit.reconciliation_notes} emptyText="No reconciliation notes" />
        <AuditList title="Consistency flags" items={audit.consistency_flags} emptyText="No consistency flags" />
      </div>
    </ReviewSection>
  )
}

function AuditFact({ label, value }: { label: string; value: string }) {
  return (
    <article className="rounded-[16px] border border-[var(--color-brand-input-border)] p-4">
      <p className="text-xs uppercase tracking-[0.18em] text-[var(--color-brand-text-muted)]">{label}</p>
      <p className="mt-2 text-sm font-medium text-[var(--color-brand-text-primary)]">{value}</p>
    </article>
  )
}

function AuditList({
  title,
  items,
  emptyText,
}: {
  title: string
  items: string[]
  emptyText: string
}) {
  return (
    <section>
      <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">{title}</p>
      <div className="mt-3 space-y-2 text-sm text-[var(--color-brand-text-body)]">
        {items.length ? items.map((item) => <p key={item}>{item}</p>) : <EmptyValue text={emptyText} />}
      </div>
    </section>
  )
}
```

- [ ] **Step 3: Update the panel to compose the remaining sections**

Add imports:

```tsx
import { CVScreeningAudit } from "@/components/jd/cv-screening-audit"
import { CVScreeningFollowups } from "@/components/jd/cv-screening-followups"
import { CVScreeningInsights } from "@/components/jd/cv-screening-insights"
import { CVScreeningRisks } from "@/components/jd/cv-screening-risks"
```

Update the result block to:

```tsx
      {result ? (
        <div className="mt-6 space-y-6">
          <CVScreeningSummary result={result.result} />
          <CVCandidateProfile profile={result.candidate_profile} />
          <CVScreeningAssessments
            knockoutAssessments={result.result.knockout_assessments}
            minimumRequirements={result.result.minimum_requirement_checks}
          />
          <CVScreeningDimensions dimensions={result.result.dimension_scores} />
          <CVScreeningInsights
            strengths={result.result.strengths}
            gaps={result.result.gaps}
            uncertainties={result.result.uncertainties}
          />
          <CVScreeningFollowups items={result.result.follow_up_questions} />
          <CVScreeningRisks items={result.result.risk_flags} />
          <CVScreeningAudit audit={result.audit} />
        </div>
      ) : null}
```

- [ ] **Step 4: Run type-check to verify the full review board compiles**

Run: `npm --prefix frontend run type-check`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/jd/cv-screening-insights.tsx frontend/src/components/jd/cv-screening-followups.tsx frontend/src/components/jd/cv-screening-risks.tsx frontend/src/components/jd/cv-screening-audit.tsx frontend/src/components/jd/cv-screening-panel.tsx
git commit -m "feat(frontend): render full phase 2 cv screening review board"
```

### Task 6: Verify the UI integration end-to-end

**Files:**
- Verify: `frontend/src/app/dashboard/jd/[id]/page.tsx`
- Verify: `frontend/src/components/jd/cv-screening-panel.tsx`
- Verify: all new files under `frontend/src/components/jd/`

- [ ] **Step 1: Confirm the page entry still passes the same props**

Verify `frontend/src/app/dashboard/jd/[id]/page.tsx` still renders:

```tsx
<CVScreeningPanel accessToken={session.accessToken} backendBaseUrl={backendBaseUrl} jd={result} />
```

Expected: no code change needed.

- [ ] **Step 2: Run lint and type-check**

Run: `npm --prefix frontend run lint && npm --prefix frontend run type-check`
Expected: PASS

- [ ] **Step 3: Start the frontend and verify the UI manually**

Run: `npm --prefix frontend run dev`
Expected: Next.js dev server starts successfully.

- [ ] **Step 4: Use the browser to verify the Phase 2 screening flow**

Manual verification checklist:

- open the JD detail page
- upload a CV on the screening panel
- confirm the page renders:
  - screening summary
  - candidate profile
  - knockout and minimum requirement sections
  - dimension scores
  - strengths, gaps, uncertainties
  - follow-up questions
  - risk flags
  - audit metadata

Expected: all sections render without runtime errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/jd/cv-screening-panel.tsx frontend/src/components/jd/cv-screening-types.ts frontend/src/components/jd/cv-screening-ui.tsx frontend/src/components/jd/cv-screening-summary.tsx frontend/src/components/jd/cv-candidate-profile.tsx frontend/src/components/jd/cv-screening-assessments.tsx frontend/src/components/jd/cv-screening-dimensions.tsx frontend/src/components/jd/cv-screening-insights.tsx frontend/src/components/jd/cv-screening-followups.tsx frontend/src/components/jd/cv-screening-risks.tsx frontend/src/components/jd/cv-screening-audit.tsx
git commit -m "feat(frontend): integrate phase 2 cv screening response"
```

## Self-Review

- Spec coverage: the plan covers Phase 2 response typing, full review-board rendering, file splitting, and end-to-end UI verification.
- Placeholder scan: every step includes concrete code, commands, or verification instructions.
- Type consistency: the same `CVScreeningResponse`, `CandidateProfile`, `AuditMetadata`, `RequirementAssessment`, and `DimensionScore` names are used consistently across tasks.
