"use client"

import { CaretDown, ShieldWarning, Sparkle, Target } from "@phosphor-icons/react"
import { useState } from "react"

import type { BilingualText, HumanReadableText, JDAnalysisResponse } from "@/components/jd/jd-analysis-types"

type JDAnalysisContentProps = {
  result: JDAnalysisResponse
}

export function JDAnalysisContent({ result }: JDAnalysisContentProps) {
  const { analysis } = result

  return (
    <div className="flex flex-col gap-6">
      <section className="rounded-[24px] bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-[var(--color-brand-text-muted)]">Tệp đã lưu</p>
            <h2 className="mt-2 text-2xl font-semibold text-[var(--color-brand-text-primary)]">
              {result.file_name}
            </h2>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <section className="rounded-[16px] bg-[var(--color-primary-50)] px-4 py-3 text-sm text-[var(--color-brand-primary)]">
              <p className="font-semibold">Trạng thái: {formatJDStatus(result.status)}</p>
              <p className="mt-1 break-all font-mono text-[var(--color-brand-text-body)]">Mã JD: {result.jd_id}</p>
            </section>
            <a
              className="flex items-center justify-center rounded-full bg-[var(--color-brand-primary)] px-4 py-3 text-sm font-semibold text-white"
              href="#cv-screening-panel"
            >
              Xem nhanh phần sàng lọc CV
            </a>
          </div>
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-3">
        <CollapsibleSection
          description="Tổng quan vai trò và bối cảnh công ty được trích xuất để HR rà soát."
          title="Tổng quan vị trí"
        >
          <div className="space-y-5">
            <InfoCard label="Tên vị trí" value={analysis.job_overview.job_title} />
            <InfoCard label="Phòng ban" value={analysis.job_overview.department} />
            <InfoCard label="Địa điểm" value={analysis.job_overview.location} />
            <InfoCard label="Mô tả vai trò" value={analysis.job_overview.role_summary} />
            <PlainInfoCard label="Cấp độ" value={analysis.job_overview.seniority_level} />
            <PlainInfoCard label="Hình thức làm việc" value={analysis.job_overview.work_mode} />
            <ChipGroup
              items={analysis.job_overview.company_benefits}
              label="Phúc lợi"
              mode="bilingual"
            />
          </div>
        </CollapsibleSection>

        <CollapsibleSection
          description="Các yêu cầu có cấu trúc để phục vụ sàng lọc CV ở bước sau."
          title="Yêu cầu"
        >
          <div className="space-y-5">
            <StringListCard items={analysis.requirements.required_skills} label="Kỹ năng bắt buộc" />
            <StringListCard items={analysis.requirements.preferred_skills} label="Kỹ năng ưu tiên" />
            <StringListCard items={analysis.requirements.tools_and_technologies} label="Công cụ và công nghệ" />
            <article className="border-b border-[var(--color-brand-input-border)] pb-5 last:border-b-0 last:pb-0">
              <header className="text-sm font-medium text-[var(--color-brand-text-muted)]">
                Kinh nghiệm yêu cầu
              </header>
              <dl className="mt-3 space-y-3 text-sm text-[var(--color-brand-text-body)]">
                <div>
                  <dt className="font-medium text-[var(--color-brand-text-primary)]">Số năm tối thiểu</dt>
                  <dd>{analysis.requirements.experience_requirements.minimum_years ?? "Chưa nêu rõ"}</dd>
                </div>
                <div>
                  <dt className="font-medium text-[var(--color-brand-text-primary)]">Vai trò liên quan</dt>
                  <dd className="mt-2 flex flex-col gap-2">
                    {analysis.requirements.experience_requirements.relevant_roles.length ? (
                      analysis.requirements.experience_requirements.relevant_roles.map((item, index) => (
                        <HumanReadableValue key={`${readableKey(item)}-${index}`} value={item} />
                      ))
                    ) : (
                      <span>Chưa nêu rõ</span>
                    )}
                  </dd>
                </div>
              </dl>
            </article>
            <HumanReadableListCard
              items={analysis.requirements.experience_requirements.preferred_domains}
              label="Lĩnh vực ưu tiên"
            />
            <HumanReadableListCard items={analysis.requirements.language_requirements} label="Yêu cầu ngôn ngữ" />
            <HumanReadableListCard
              items={analysis.requirements.education_and_certifications}
              label="Học vấn và chứng chỉ"
            />
            <HumanReadableListCard
              items={analysis.requirements.screening_knockout_criteria}
              label="Tiêu chí loại trực tiếp"
            />
            <BilingualListCard items={analysis.requirements.key_responsibilities} label="Trách nhiệm chính" />
          </div>
        </CollapsibleSection>

        <CollapsibleSection
          description="Các tiêu chí đánh giá có trọng số được gieo từ JD để dùng ở bước sàng lọc sau."
          title="Khung đánh giá gợi ý"
        >
          <div className="space-y-5">
            {analysis.rubric_seed.evaluation_dimensions.map((dimension) => (
              <article
                className="border-b border-[var(--color-brand-input-border)] pb-5 last:border-b-0 last:pb-0"
                key={dimension.name.en}
              >
                <header className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-lg font-semibold text-[var(--color-brand-text-primary)]">
                      {dimension.name.vi}
                    </p>
                    <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">{dimension.name.en}</p>
                  </div>
                  <PriorityBadge priority={dimension.priority} />
                </header>
                <p className="mt-3 text-sm text-[var(--color-brand-text-body)]">{dimension.description.vi}</p>
                <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">{dimension.description.en}</p>
                <p className="mt-3 text-sm font-medium text-[var(--color-brand-text-primary)]">
                  Trọng số: {dimension.weight}
                </p>
                <ul className="mt-3 space-y-2">
                  {dimension.evidence_signals.map((signal) => (
                    <li
                      className="rounded-[14px] bg-[var(--color-primary-50)] px-3 py-2"
                      key={`${dimension.name.en}-${signal.en}`}
                    >
                      <p className="text-sm font-medium text-[var(--color-brand-text-primary)]">{signal.vi}</p>
                      <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">{signal.en}</p>
                    </li>
                  ))}
                </ul>
              </article>
            ))}

            <section className="space-y-5 border-t border-[var(--color-brand-input-border)] pt-5">
              <HumanReadableListCard
                items={analysis.rubric_seed.screening_rules.minimum_requirements}
                label="Yêu cầu tối thiểu"
              />
              <article className="border-b border-[var(--color-brand-input-border)] pb-5 last:border-b-0 last:pb-0">
                <header className="text-sm font-medium text-[var(--color-brand-text-muted)]">
                  Nguyên tắc chấm điểm
                </header>
                <div className="mt-3">
                  <HumanReadableValue value={analysis.rubric_seed.screening_rules.scoring_principle} />
                </div>
              </article>
              <BilingualListCard
                items={analysis.rubric_seed.ambiguities_for_human_review}
                label="Điểm cần người xem lại"
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
      <header className="text-sm font-medium text-[var(--color-brand-text-muted)]">{label}</header>
      <div className="mt-3">
        <p className="text-lg font-semibold text-[var(--color-brand-text-primary)]">{value.vi}</p>
        <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">{value.en}</p>
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
      <header className="text-sm font-medium text-[var(--color-brand-text-muted)]">{label}</header>
      <p className="mt-3 text-lg font-semibold text-[var(--color-brand-text-primary)]">{value}</p>
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
      <header className="text-sm font-medium text-[var(--color-brand-text-muted)]">{label}</header>
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
      <header className="text-sm font-medium text-[var(--color-brand-text-muted)]">{label}</header>
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
      <header className="text-sm font-medium text-[var(--color-brand-text-muted)]">{label}</header>
      <div className="mt-3 flex flex-col gap-2">
        {items.length ? items.map((item) => <HumanReadableValue key={item.en} value={item} />) : <EmptyState />}
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
      <header className="text-sm font-medium text-[var(--color-brand-text-muted)]">{label}</header>
      <div className="mt-3 flex flex-wrap gap-2">
        {items.length ? (
          items.map((item, index) => (
            <Chip
              key={`${typeof item === "string" ? item : item.en}-${index}`}
              text={
                typeof item === "string"
                  ? item
                  : mode === "plain"
                    ? item.vi
                    : `${item.vi} / ${item.en}`
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
      <p className="text-sm font-medium text-[var(--color-brand-text-primary)]">{value.vi}</p>
      <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">{value.en}</p>
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
  return <p className="text-sm text-[var(--color-brand-text-muted)]">Chưa có dữ liệu</p>
}

function readableKey(value: HumanReadableText) {
  return typeof value === "string" ? value : value.en
}

function PriorityBadge({ priority }: { priority: string }) {
  const config = getPriorityConfig(priority)
  const Icon = config.icon

  return (
    <div className={`rounded-full px-3 py-1 text-xs font-semibold ${config.className}`}>
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
      label: "Bắt buộc",
      icon: ShieldWarning,
      className: "bg-rose-50 text-rose-700",
    }
  }

  if (priority === "important") {
    return {
      label: "Quan trọng",
      icon: Target,
      className: "bg-sky-50 text-sky-700",
    }
  }

  return {
    label: "Nên có",
    icon: Sparkle,
    className: "bg-violet-50 text-violet-700",
  }
}

function formatJDStatus(status: JDAnalysisResponse["status"]) {
  if (status === "completed") {
    return "Hoàn tất"
  }

  return status
}
