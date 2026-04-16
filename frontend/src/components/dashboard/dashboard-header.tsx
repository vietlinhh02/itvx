import type { Route } from "next"
import Link from "next/link"

import { LoginLogo } from "@/components/login/login-logo"

const NAV_ITEMS: { label: string; href: Route }[] = [
  { label: "Overview", href: "/dashboard" as Route },
  { label: "JD workspace", href: "/dashboard/jd" as Route },
]

export function DashboardHeader() {
  return (
    <header className="mx-auto mb-6 flex w-full max-w-5xl items-center rounded-full border border-[var(--color-brand-input-border)] bg-white px-4 py-3 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
      <div className="mr-4 shrink-0">
        <LoginLogo compact />
      </div>
      <nav className="ml-auto flex items-center gap-3">
        {NAV_ITEMS.map((item) => (
          <Link
            key={item.href}
            className="rounded-full border border-[var(--color-brand-input-border)] bg-white px-3 py-1.5 text-xs font-medium text-[var(--color-brand-primary)]"
            href={item.href}
          >
            {item.label}
          </Link>
        ))}
      </nav>
    </header>
  )
}
