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
            details: [
              item.summary,
              ...(item.technologies.length ? [`Tech: ${item.technologies.join(", ")}`] : []),
            ],
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
