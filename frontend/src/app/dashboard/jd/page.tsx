import type { Route } from "next"
import Link from "next/link"
import { redirect } from "next/navigation"

import { JDUploadPanel } from "@/components/jd/jd-upload-panel"
import { auth } from "@/lib/auth"

const backendBaseUrl = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL

type JDRecentItem = {
  jd_id: string
  file_name: string
  status: string
  created_at: string
  job_title: string | null
}

export default async function JDDashboardPage() {
  const session = await auth()

  if (!session?.accessToken || !backendBaseUrl) {
    redirect("/login")
  }

  const recentResponse = await fetch(`${backendBaseUrl}/api/v1/jd`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${session.accessToken}`,
    },
    cache: "no-store",
  })

  if (!recentResponse.ok) {
    redirect("/login")
  }

  const recentUploads = (await recentResponse.json()) as JDRecentItem[]

  return (
    <main className="flex w-full flex-col gap-6 py-6">
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.8fr)_minmax(360px,0.9fr)]">
        <JDUploadPanel accessToken={session.accessToken} backendBaseUrl={backendBaseUrl} />

        <section className="rounded-[24px] bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)] xl:max-h-[calc(100vh-14rem)] xl:overflow-y-auto xl:scrollbar-hidden">
          <div>
            <p className="text-sm font-medium text-[var(--color-brand-text-muted)]">Navigation</p>
            <h2 className="mt-2 text-2xl font-semibold text-[var(--color-brand-text-primary)]">
              Recent JD uploads
            </h2>
            <p className="mt-2 text-sm leading-6 text-[var(--color-brand-text-body)]">
              Open any recent JD analysis directly from its persisted id.
            </p>
          </div>

          <div className="mt-5 flex flex-col gap-3">
            {recentUploads.length ? (
              recentUploads.map((item) => (
                <Link
                  className="rounded-[18px] border border-[var(--color-brand-input-border)] p-4 transition hover:border-[var(--color-brand-primary)] hover:bg-[var(--color-primary-50)]"
                  href={buildJDRoute(item.jd_id)}
                  key={item.jd_id}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-base font-semibold text-[var(--color-brand-text-primary)]">
                        {item.job_title ?? item.file_name}
                      </p>
                      <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">{item.file_name}</p>
                    </div>
                    <span className="rounded-full bg-[var(--color-primary-50)] px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-[var(--color-brand-primary)]">
                      {item.status}
                    </span>
                  </div>
                  <p className="mt-3 text-xs uppercase tracking-[0.18em] text-[var(--color-brand-text-muted)]">
                    {new Date(item.created_at).toLocaleString()}
                  </p>
                </Link>
              ))
            ) : (
              <p className="rounded-[18px] border border-dashed border-[var(--color-brand-input-border)] p-4 text-sm text-[var(--color-brand-text-muted)]">
                No JD uploads yet. Upload your first document to populate this list.
              </p>
            )}
          </div>
        </section>
      </div>
    </main>
  )
}

function buildJDRoute(jdId: string): Route {
  return `/dashboard/jd/${jdId}` as Route
}
