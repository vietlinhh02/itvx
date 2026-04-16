"use client"

import { CaretDown, ShieldWarning, Sparkle, Target } from "@phosphor-icons/react"
import type { Route } from "next"
import Link from "next/link"
import { useState } from "react"

type BilingualText = {
  vi: string
  en: string
}

type HumanReadableText = string | BilingualText

export type JDAnalysisResponse = {
  jd_id: string
  file_name: string
  status: "completed"
  created_at: string
  analysis: {
    job_overview: {
      job_title: BilingualText
      department: BilingualText
      seniority_level: string
      location: BilingualText
      work_mode: string
      role_summary: BilingualText
      company_benefits: BilingualText[]
    }
    requirements: {
      required_skills: string[]
      preferred_skills: string[]
      tools_and_technologies: string[]
      experience_requirements: {
        minimum_years: number | null
        relevant_roles: HumanReadableText[]
        preferred_domains: HumanReadableText[]
      }
      education_and_certifications: HumanReadableText[]
      language_requirements: HumanReadableText[]
      key_responsibilities: BilingualText[]
      screening_knockout_criteria: HumanReadableText[]
    }
    rubric_seed: {
      evaluation_dimensions: Array<{
        name: BilingualText
        description: BilingualText
        priority: string
        weight: number
        evidence_signals: BilingualText[]
      }>
      screening_rules: {
        minimum_requirements: HumanReadableText[]
        scoring_principle: HumanReadableText
      }
      ambiguities_for_human_review: BilingualText[]
    }
  }
}

type JDUploadPanelProps = {
  accessToken: string
  backendBaseUrl: string
}

type JDAnalysisContentProps = {
  result: JDAnalysisResponse
}

export function JDUploadPanel({ accessToken, backendBaseUrl }: JDUploadPanelProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [result, setResult] = useState<JDAnalysisResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isUploading, setIsUploading] = useState(false)

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (!selectedFile) {
      setError("Please choose a PDF or DOCX file before uploading.")
      return
    }

    setIsUploading(true)
    setError(null)

    const formData = new FormData()
    formData.append("file", selectedFile)

    try {
      const response = await fetch(`${backendBaseUrl}/api/v1/jd/analyze`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
        body: formData,
      })

      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as { detail?: string } | null
        setResult(null)
        setError(payload?.detail ?? "JD upload failed. Please try again.")
        return
      }

      const payload = (await response.json()) as JDAnalysisResponse
      setResult(payload)
    } catch {
      setResult(null)
      setError("Could not reach the backend. Check the API URL and try again.")
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <section className="rounded-[24px] bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
        <div className="flex flex-col gap-2">
          <p className="text-sm font-medium text-[var(--color-brand-text-muted)]">Phase 1 - JD Analysis</p>
          <h1 className="text-3xl font-semibold text-[var(--color-brand-text-primary)]">
            Upload a job description
          </h1>
          <p className="max-w-2xl text-sm leading-6 text-[var(--color-brand-text-body)]">
            Send a PDF or DOCX file to the backend, store the original document, and review the
            extracted hiring blueprint in a three-column analysis board.
          </p>
        </div>

        <form className="mt-6 flex flex-col gap-4" onSubmit={handleSubmit}>
          <label className="flex flex-col gap-2 text-sm font-medium text-[var(--color-brand-text-primary)]">
            JD file
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
              className="rounded-[50px] bg-[var(--color-brand-primary)] px-5 py-3 text-sm font-semibold text-white transition disabled:cursor-not-allowed disabled:opacity-60"
              disabled={isUploading}
              type="submit"
            >
              {isUploading ? "Analyzing..." : "Upload and analyze"}
            </button>
            <p className="text-sm text-[var(--color-brand-text-muted)]">
              {selectedFile ? `Selected: ${selectedFile.name}` : "Supported formats: PDF and DOCX"}
            </p>
          </div>

          {error ? (
            <p className="rounded-[12px] bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>
          ) : null}
        </form>
      </section>

      {result ? <JDAnalysisContent result={result} /> : null}
    </div>
  )
}

export function JDAnalysisContent({ result }: JDAnalysisContentProps) {
  const { analysis } = result

  return (
    <div className="flex flex-col gap-6">
      <section className="rounded-[24px] bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-[var(--color-brand-text-muted)]">Stored document</p>
            <h2 className="mt-2 text-2xl font-semibold text-[var(--color-brand-text-primary)]">
              {result.file_name}
            </h2>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <section className="rounded-[16px] bg-[var(--color-primary-50)] px-4 py-3 text-sm text-[var(--color-brand-primary)]">
              <p className="font-semibold">Status: {result.status}</p>
              <p className="mt-1 text-[var(--color-brand-text-body)]">JD ID: {result.jd_id}</p>
            </section>
            <Link
              className="flex items-center justify-center rounded-full bg-[var(--color-brand-primary)] px-4 py-3 text-sm font-semibold text-white"
              href={buildJDDetailHref(result.jd_id)}
            >
              Open JD detail
            </Link>
          </div>
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-3">
        <CollapsibleSection
          defaultOpen={true}
          description="Role summary and company context extracted for HR review."
          title="Job Overview"
        >
          <div className="space-y-5">
            <InfoCard label="Job title" value={analysis.job_overview.job_title} />
            <InfoCard label="Department" value={analysis.job_overview.department} />
            <InfoCard label="Location" value={analysis.job_overview.location} />
            <InfoCard label="Role summary" value={analysis.job_overview.role_summary} />
            <PlainInfoCard label="Seniority level" value={analysis.job_overview.seniority_level} />
            <PlainInfoCard label="Work mode" value={analysis.job_overview.work_mode} />
            <ChipGroup
                           items={analysis.job_overview.company_benefits}
              label="Company benefits"
              mode="bilingual"
            />
          </div>
        </CollapsibleSection>

        <CollapsibleSection
          description="Structured requirements that can feed CV screening later."
          title="Requirements"
        >
          <div className="space-y-5">
            <StringListCard items={analysis.requirements.required_skills} label="Required skills" />
            <StringListCard items={analysis.requirements.preferred_skills} label="Preferred skills" />
            <StringListCard
                           items={analysis.requirements.tools_and_technologies}
              label="Tools and technologies"
            />
            <article className="border-b border-[var(--color-brand-input-border)] pb-5 last:border-b-0 last:pb-0">
              <header className="flex items-center gap-2 text-xs uppercase tracking-[0.18em] text-[var(--color-brand-text-muted)]">
                Experience requirements
              </header>
              <dl className="mt-3 space-y-3 text-sm text-[var(--color-brand-text-body)]">
                <div>
                  <dt className="font-medium text-[var(--color-brand-text-primary)]">Minimum years</dt>
                  <dd>{analysis.requirements.experience_requirements.minimum_years ?? "Not specified"}</dd>
                </div>
                <div>
                  <dt className="font-medium text-[var(--color-brand-text-primary)]">Relevant roles</dt>
                  <dd className="mt-2 flex flex-col gap-2">
                    {analysis.requirements.experience_requirements.relevant_roles.length ? (
                      analysis.requirements.experience_requirements.relevant_roles.map((item, index) => (
                        <HumanReadableValue key={`${readableKey(item)}-${index}`} value={item} />
                      ))
                    ) : (
                      <span>Not specified</span>
                    )}
                  </dd>
                </div>
              </dl>
            </article>
            <HumanReadableListCard
                           items={analysis.requirements.experience_requirements.preferred_domains}
              label="Preferred domains"
            />
            <HumanReadableListCard
                           items={analysis.requirements.language_requirements}
              label="Language requirements"
            />
            <HumanReadableListCard
                           items={analysis.requirements.education_and_certifications}
              label="Education and certifications"
            />
            <HumanReadableListCard
                           items={analysis.requirements.screening_knockout_criteria}
              label="Screening knockout criteria"
            />
            <BilingualListCard
              items={analysis.requirements.key_responsibilities}
              label="Key responsibilities"
            />
          </div>
        </CollapsibleSection>

        <CollapsibleSection
          description="Weighted evaluation dimensions seeded from the JD for downstream screening."
          title="Rubric Seed"
        >
          <div className="space-y-5">
            {analysis.rubric_seed.evaluation_dimensions.map((dimension) => (
              <article className="border-b border-[var(--color-brand-input-border)] pb-5 last:border-b-0 last:pb-0" key={dimension.name.en}>
                <header className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-lg font-semibold text-[var(--color-brand-text-primary)]">
                      {dimension.name.en}
                    </p>
                    <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">{dimension.name.vi}</p>
                  </div>
                  <PriorityBadge priority={dimension.priority} />
                </header>
                <p className="mt-3 text-sm text-[var(--color-brand-text-body)]">{dimension.description.en}</p>
                <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">{dimension.description.vi}</p>
                <p className="mt-3 text-sm font-medium text-[var(--color-brand-text-primary)]">
                  Weight: {dimension.weight}
                </p>
                <ul className="mt-3 space-y-2">
                  {dimension.evidence_signals.map((signal) => (
                    <li className="rounded-[14px] bg-[var(--color-primary-50)] px-3 py-2" key={`${dimension.name.en}-${signal.en}`}>
                      <p className="text-sm font-medium text-[var(--color-brand-text-primary)]">{signal.en}</p>
                      <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">{signal.vi}</p>
                    </li>
                  ))}
                </ul>
              </article>
            ))}

            <section className="space-y-5 border-t border-[var(--color-brand-input-border)] pt-5">
              <HumanReadableListCard
                               items={analysis.rubric_seed.screening_rules.minimum_requirements}
                label="Minimum requirements"
              />
              <article className="border-b border-[var(--color-brand-input-border)] pb-5 last:border-b-0 last:pb-0">
                <header className="flex items-center gap-2 text-xs uppercase tracking-[0.18em] text-[var(--color-brand-text-muted)]">
                  Scoring principle
                </header>
                <div className="mt-3">
                  <HumanReadableValue value={analysis.rubric_seed.screening_rules.scoring_principle} />
                </div>
              </article>
              <BilingualListCard
                               items={analysis.rubric_seed.ambiguities_for_human_review}
                label="Ambiguities for human review"
              />
            </section>
          </div>
        </CollapsibleSection>
      </div>
    </div>
  )
}

function CollapsibleSection({
  title,
  description,
  children,
  defaultOpen = false,
}: {
  title: string
  description: string
  children: React.ReactNode
  defaultOpen?: boolean
}) {
  const [isOpen, setIsOpen] = useState(defaultOpen)

  return (
    <section className="rounded-[24px] bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
      <header
        className="flex cursor-pointer items-start justify-between gap-4 xl:cursor-auto"
        onClick={() => setIsOpen((prev) => !prev)}
      >
        <SectionTitle description={description} title={title} />
        <div className="mt-1 xl:hidden">
          <CaretDown
            className={`text-[var(--color-brand-text-muted)] transition-transform duration-300 ${isOpen ? "rotate-180" : ""}`}
            size={20}
            weight="bold"
          />
        </div>
      </header>
      <div
        className={`grid transition-all duration-300 ease-in-out xl:grid-rows-[1fr] xl:opacity-100 ${
          isOpen ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0"
        }`}
      >
        <div className="overflow-hidden">
          <div className="pt-5">{children}</div>
        </div>
      </div>
    </section>
  )
}

function SectionTitle({ title, description }: { title: string; description: string }) {
  return (
    <div>
      <h2 className="text-2xl font-semibold text-[var(--color-brand-text-primary)]">{title}</h2>
      <p className="mt-2 text-sm leading-6 text-[var(--color-brand-text-body)]">{description}</p>
    </div>
  )
}

function InfoCard({
  label,
  value,
}: {
  label: string
  value: BilingualText
}) {
  return (
    <article className="border-b border-[var(--color-brand-input-border)] pb-5 last:border-b-0 last:pb-0">
      <header className="flex items-center gap-2 text-xs uppercase tracking-[0.18em] text-[var(--color-brand-text-muted)]">
        {label}
      </header>
      <div className="mt-3">
        <p className="text-lg font-semibold text-[var(--color-brand-text-primary)]">{value.en}</p>
        <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">{value.vi}</p>
      </div>
    </article>
  )
}

function PlainInfoCard({
  label,
  value,
}: {
  label: string
  value: string
}) {
  return (
    <article className="border-b border-[var(--color-brand-input-border)] pb-5 last:border-b-0 last:pb-0">
      <header className="flex items-center gap-2 text-xs uppercase tracking-[0.18em] text-[var(--color-brand-text-muted)]">
        {label}
      </header>
      <p className="mt-3 text-lg font-semibold capitalize text-[var(--color-brand-text-primary)]">
        {value}
      </p>
    </article>
  )
}

function StringListCard({
  label,
  items,
}: {
  label: string
  items: string[]
}) {
  return (
    <article className="border-b border-[var(--color-brand-input-border)] pb-5 last:border-b-0 last:pb-0">
      <header className="flex items-center gap-2 text-xs uppercase tracking-[0.18em] text-[var(--color-brand-text-muted)]">
        {label}
      </header>
      <div className="mt-3 flex flex-wrap gap-2">
        {items.length ? items.map((item) => <Chip key={item} text={item} />) : <EmptyState />}
      </div>
    </article>
  )
}

function HumanReadableListCard({
  label,
  items,
}: {
  label: string
  items: HumanReadableText[]
}) {
  return (
    <article className="border-b border-[var(--color-brand-input-border)] pb-5 last:border-b-0 last:pb-0">
      <header className="flex items-center gap-2 text-xs uppercase tracking-[0.18em] text-[var(--color-brand-text-muted)]">
        {label}
      </header>
      <div className="mt-3 flex flex-col gap-2">
        {items.length ? (
          items.map((item, index) => (
            <HumanReadableValue key={`${readableKey(item)}-${index}`} value={item} />
          ))
        ) : (
          <EmptyState />
        )}
      </div>
    </article>
  )
}

function BilingualListCard({
  label,
  items,
}: {
  label: string
  items: BilingualText[]
}) {
  return (
    <article className="border-b border-[var(--color-brand-input-border)] pb-5 last:border-b-0 last:pb-0">
      <header className="flex items-center gap-2 text-xs uppercase tracking-[0.18em] text-[var(--color-brand-text-muted)]">
        {label}
      </header>
      <div className="mt-3 flex flex-col gap-2">
        {items.length ? (
          items.map((item) => <HumanReadableValue key={item.en} value={item} />)
        ) : (
          <EmptyState />
        )}
      </div>
    </article>
  )
}

function ChipGroup({
  label,
  items,
  mode,
}: {
  label: string
  items: Array<string | BilingualText>
  mode: "plain" | "bilingual"
}) {
  return (
    <article className="border-b border-[var(--color-brand-input-border)] pb-5 last:border-b-0 last:pb-0">
      <header className="flex items-center gap-2 text-xs uppercase tracking-[0.18em] text-[var(--color-brand-text-muted)]">
        {label}
      </header>
      <div className="mt-3 flex flex-wrap gap-2">
        {items.length ? (
          items.map((item, index) => (
            <Chip
              key={`${typeof item === "string" ? item : item.en}-${index}`}
              text={
                typeof item === "string"
                  ? item
                  : mode === "plain"
                    ? item.en
                    : `${item.en} / ${item.vi}`
              }
            />
          ))
        ) : (
          <EmptyState />
        )}
      </div>
    </article>
  )
}

function HumanReadableValue({ value }: { value: HumanReadableText }) {
  if (typeof value === "string") {
    return <p className="text-sm text-[var(--color-brand-text-body)]">{value}</p>
  }

  return (
    <div className="rounded-[14px] bg-[var(--color-primary-50)] px-3 py-2 ring-1 ring-inset ring-[var(--color-brand-input-border)]">
      <p className="text-sm font-medium text-[var(--color-brand-text-primary)]">{value.en}</p>
      <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">{value.vi}</p>
    </div>
  )
}

function Chip({ text }: { text: string }) {
  return (
    <span className="rounded-full bg-[var(--color-primary-50)] px-3 py-2 text-sm text-[var(--color-brand-primary)]">
      {text}
    </span>
  )
}

function EmptyState() {
  return <p className="text-sm text-[var(--color-brand-text-muted)]">Not specified</p>
}

function readableKey(value: HumanReadableText) {
  return typeof value === "string" ? value : value.en
}

function buildJDDetailHref(jdId: string): Route {
  return `/dashboard/jd/${jdId}` as Route
}

function PriorityBadge({ priority }: { priority: string }) {
  const config = getPriorityConfig(priority)
  const Icon = config.icon

  return (
    <div className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] ${config.className}`}>
      <span className="flex items-center gap-1.5">
        <Icon size={12} weight="fill" />
        {config.label}
      </span>
    </div>
  )
}

function getPriorityConfig(priority: string) {
  if (priority === "must_have") {
    return {
      label: "Must have",
      icon: ShieldWarning,
      className: "bg-rose-50 text-rose-700",
    }
  }

  if (priority === "important") {
    return {
      label: "Important",
      icon: Target,
      className: "bg-sky-50 text-sky-700",
    }
  }

  return {
    label: "Nice to have",
    icon: Sparkle,
    className: "bg-violet-50 text-violet-700",
  }
}
