"use client"

import { ShieldWarning, Sparkle, Target } from "@phosphor-icons/react"

import type {
  BilingualText,
  RequirementStatus,
  RiskSeverity,
} from "@/components/jd/cv-screening-types"

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
  const className =
    status === "met"
      ? "bg-emerald-50 text-emerald-700"
      : status === "not_met"
        ? "bg-rose-50 text-rose-700"
        : "bg-amber-50 text-amber-700"

  return (
    <span className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] ${className}`}>
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
