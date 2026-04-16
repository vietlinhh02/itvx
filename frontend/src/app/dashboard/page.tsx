import Link from "next/link"
import { redirect } from "next/navigation"
import { auth } from "@/lib/auth"

type BackendUser = {
  id: string
  email: string
  name: string | null
  role: string
  is_active: boolean
}

const backendBaseUrl = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL

export default async function DashboardPage() {
  const session = await auth()

  if (!session?.accessToken || !backendBaseUrl) {
    redirect("/login")
  }

  const profileResponse = await fetch(`${backendBaseUrl}/api/v1/auth/me`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${session.accessToken}`,
    },
    cache: "no-store",
  })

  if (!profileResponse.ok) {
    redirect("/login")
  }

  const profile = (await profileResponse.json()) as BackendUser

  return (
    <main className="mx-auto flex w-full max-w-4xl flex-col gap-6 py-6">
      <section className="rounded-2xl bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
        <p className="text-sm font-medium text-[var(--color-brand-text-muted)]">Authenticated with backend</p>
        <h2 className="mt-2 text-3xl font-semibold text-[var(--color-brand-text-primary)]">Dashboard overview</h2>
        <div className="mt-4 flex flex-wrap gap-3">
          <Link
            className="rounded-full bg-[var(--color-brand-primary)] px-4 py-2 text-sm font-semibold text-white"
            href="/dashboard/jd"
          >
            Open JD analysis
          </Link>
        </div>
      </section>

      <section className="rounded-2xl bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
        <h2 className="mb-4 text-lg font-semibold text-[var(--color-brand-text-primary)]">User profile from /api/v1/auth/me</h2>
        <dl className="grid gap-4 text-sm sm:grid-cols-2">
          <InfoItem label="User ID" value={profile.id} />
          <InfoItem label="Email" value={profile.email} />
          <InfoItem label="Name" value={profile.name ?? "N/A"} />
          <InfoItem label="Role" value={profile.role} />
          <InfoItem label="Active" value={String(profile.is_active)} />
        </dl>
      </section>
    </main>
  )
}

function InfoItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-[var(--color-brand-input-border)] bg-white p-4">
      <dt className="text-xs uppercase tracking-wide text-[var(--color-brand-text-muted)]">{label}</dt>
      <dd className="mt-1 text-sm font-medium text-[var(--color-brand-text-primary)]">{value}</dd>
    </div>
  )
}
