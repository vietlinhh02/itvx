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
        <AuditList
          title="Reconciliation notes"
          items={audit.reconciliation_notes}
          emptyText="No reconciliation notes"
        />
        <AuditList
          title="Consistency flags"
          items={audit.consistency_flags}
          emptyText="No consistency flags"
        />
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
