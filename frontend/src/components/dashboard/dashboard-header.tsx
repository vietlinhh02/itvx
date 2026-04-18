"use client"

import type { Route } from "next"

import { LoginLogo } from "@/components/login/login-logo"
import { AppLink } from "@/components/navigation/app-link"
import { useAuthStore } from "@/stores/authStore"

const NAV_ITEMS: { label: string; href: Route }[] = [
  { label: "Tổng quan", href: "/dashboard" as Route },
  { label: "Phân tích JD", href: "/dashboard/jd" as Route },
  { label: "Sàng lọc CV", href: "/dashboard/cv-screenings" as Route },
]

export function DashboardHeader() {
  const isLoading = useAuthStore((state) => state.isLoading)
  const logout = useAuthStore((state) => state.logout)

  return (
    <header className="mx-auto mb-6 flex w-full max-w-5xl items-center gap-3 rounded-full border border-[var(--color-brand-input-border)] bg-white px-4 py-3 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
      <div className="mr-4 shrink-0">
        <LoginLogo compact />
      </div>
      <nav className="ml-auto flex items-center gap-3">
        {NAV_ITEMS.map((item) => (
          <AppLink
            key={item.href}
            className="rounded-full border border-[var(--color-brand-input-border)] bg-white px-3 py-1.5 text-xs font-medium text-[var(--color-brand-primary)]"
            href={item.href}
          >
            {item.label}
          </AppLink>
        ))}
        <button
          type="button"
          className="rounded-full border border-[var(--color-brand-input-border)] bg-[var(--color-primary-50)] px-3 py-1.5 text-xs font-medium text-[var(--color-brand-primary)] transition hover:border-[var(--color-brand-primary)] disabled:cursor-not-allowed disabled:opacity-70"
          disabled={isLoading}
          onClick={async () => {
            await logout()
          }}
        >
          {isLoading ? "Đang đăng xuất..." : "Đăng xuất"}
        </button>
      </nav>
    </header>
  )
}
