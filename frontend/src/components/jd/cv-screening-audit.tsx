import type { AuditMetadata } from "@/components/jd/cv-screening-types"
import { EmptyValue, ReviewSection } from "@/components/jd/cv-screening-ui"

export function CVScreeningAudit({ audit }: { audit: AuditMetadata }) {
  return (
    <ReviewSection
      title="Metadata kiểm tra"
      description="Metadata của bước trích xuất và sàng lọc được backend trả về."
    >
      <div className="space-y-6">
        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <AuditFact label="Model trích xuất" value={audit.extraction_model} />
          <AuditFact label="Model sàng lọc" value={audit.screening_model} />
          <AuditFact label="Thời điểm tạo" value={audit.generated_at} />
          <AuditFact label="Phiên bản schema hồ sơ" value={audit.profile_schema_version} />
          <AuditFact label="Phiên bản schema sàng lọc" value={audit.screening_schema_version} />
        </section>
        <AuditList
          title="Ghi chú đối soát"
          items={audit.reconciliation_notes}
          emptyText="Không có ghi chú đối soát"
        />
        <AuditList
          title="Cờ nhất quán"
          items={audit.consistency_flags}
          emptyText="Không có cờ nhất quán"
        />
      </div>
    </ReviewSection>
  )
}

function AuditFact({ label, value }: { label: string; value: string }) {
  return (
    <article className="rounded-[16px] border border-[var(--color-brand-input-border)] p-4">
      <p className="text-xs text-[var(--color-brand-text-muted)]">{label}</p>
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
