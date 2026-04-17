"use client"

export function LoadingScreen({
  fullscreen = true,
}: {
  fullscreen?: boolean
}) {
  return (
    <div
      aria-live="polite"
      aria-busy="true"
      role="status"
      className={
        fullscreen
          ? "fixed inset-0 z-[100] flex items-center justify-center bg-white/88 backdrop-blur-sm"
          : "flex min-h-[40vh] items-center justify-center rounded-[24px] bg-white"
      }
    >
      <span className="sr-only">Đang tải</span>
      <div
        aria-hidden="true"
        data-testid="navigation-spinner"
        className="h-9 w-9 animate-spin rounded-full border-[3px] border-[var(--color-primary-100)] border-t-[var(--color-brand-primary)]"
      />
    </div>
  )
}
