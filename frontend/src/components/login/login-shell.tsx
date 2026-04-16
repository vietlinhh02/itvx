import type { ReactNode } from "react"
import { LoginLogo } from "./login-logo"

type LoginShellProps = {
  children: ReactNode
}

export function LoginShell({ children }: LoginShellProps) {
  return (
    <main className="login-grid-bg relative flex min-h-screen items-center justify-center px-5 py-10">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(230,193,255,0.2),transparent_40%)]" />
      <section className="relative w-full max-w-[602px] overflow-hidden rounded-[24px] bg-white px-8 py-10 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)] sm:px-10">
        <div
          aria-hidden
          className="absolute -right-16 -top-16 size-56 rounded-full border-[24px] border-[rgba(230,193,255,0.28)]"
        />
        <div className="relative flex flex-col items-center gap-8">
          <LoginLogo />
          <div className="w-full space-y-6">
            <h1 className="text-center text-4xl font-semibold tracking-[-0.03em] text-[var(--color-brand-text-primary)] sm:text-[52px] sm:leading-[1.05]">
              Sign in to InterviewX
            </h1>
            {children}
          </div>
        </div>
      </section>
    </main>
  )
}
