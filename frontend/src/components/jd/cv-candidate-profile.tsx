import type { CandidateProfile } from "@/components/jd/cv-screening-types"
import { EmptyValue, ReviewSection } from "@/components/jd/cv-screening-ui"

export function CVCandidateProfile({ profile }: { profile: CandidateProfile }) {
  return (
    <ReviewSection
      title="Hồ sơ ứng viên"
      description="Hồ sơ ứng viên có cấu trúc được trích xuất từ CV đã tải lên."
    >
      <div className="space-y-6">
        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <ProfileFact label="Họ tên" value={profile.candidate_summary.full_name} />
          <ProfileFact label="Chức danh hiện tại" value={profile.candidate_summary.current_title} />
          <ProfileFact label="Địa điểm" value={profile.candidate_summary.location} />
          <ProfileFact
            label="Số năm kinh nghiệm"
            value={
              profile.candidate_summary.total_years_experience === null
                ? null
                : String(profile.candidate_summary.total_years_experience)
            }
          />
        </section>

        <section>
          <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">Tóm tắt nghề nghiệp</p>
          {profile.candidate_summary.professional_summary ? (
            <>
              <p className="mt-2 text-sm text-[var(--color-brand-text-body)]">
                {profile.candidate_summary.professional_summary.vi}
              </p>
              <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">
                {profile.candidate_summary.professional_summary.en}
              </p>
            </>
          ) : (
            <div className="mt-2">
              <EmptyValue text="Chưa có dữ liệu" />
            </div>
          )}
        </section>

        <EntityList
          title="Kinh nghiệm làm việc"
          items={profile.work_experience.map((item) => ({
            key: `${item.company}-${item.role}`,
            title: `${item.role} tại ${item.company}`,
            meta: item.duration_text,
            details: [...item.responsibilities, ...item.achievements],
          }))}
        />

        <EntityList
          title="Dự án"
          items={profile.projects.map((item, index) => ({
            key: `${item.name ?? item.summary}-${index}`,
            title: item.name ?? item.summary,
            meta: item.role,
            details: [
              item.summary,
              ...(item.technologies.length ? [`Công nghệ: ${item.technologies.join(", ")}`] : []),
            ],
          }))}
        />

        <StringChipSection
          title="Kỹ năng"
          items={profile.skills_inventory.map((item) => item.skill_name)}
        />
        <StringChipSection title="Ngôn ngữ" items={profile.languages.map((item) => item.language_name)} />
        <StringChipSection title="Chứng chỉ" items={profile.certifications.map((item) => item.name)} />
        <StringChipSection title="Học vấn" items={profile.education.map((item) => item.institution)} />

        <EntityList
          title="Điểm chưa chắc chắn trong hồ sơ"
          items={profile.profile_uncertainties.map((item) => ({
            key: item.title.en,
            title: item.title.vi,
            meta: item.title.en,
            details: [item.reason.vi, item.impact.vi],
          }))}
          emptyText="Không có điểm chưa chắc chắn"
        />
      </div>
    </ReviewSection>
  )
}

function ProfileFact({ label, value }: { label: string; value: string | null }) {
  return (
    <article className="rounded-[16px] border border-[var(--color-brand-input-border)] p-4">
      <p className="text-xs text-[var(--color-brand-text-muted)]">{label}</p>
      <p className="mt-2 text-sm font-medium text-[var(--color-brand-text-primary)]">{value ?? "Chưa có dữ liệu"}</p>
    </article>
  )
}

function EntityList({
  title,
  items,
  emptyText = "Không có",
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
          <EmptyValue text="Không có" />
        )}
      </div>
    </section>
  )
}
