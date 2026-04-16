type LoginLogoProps = {
  compact?: boolean
}

export function LoginLogo({ compact = false }: LoginLogoProps) {
  return (
    <div className="inline-flex items-center gap-2">
      <span
        aria-hidden
        className={`${compact ? "size-5" : "size-6"} relative rounded-full bg-[var(--color-brand-primary)]`}
      >
        <span className="absolute left-1/2 top-1/2 size-[38%] -translate-x-1/2 -translate-y-1/2 rounded-full bg-white" />
        <span className="absolute left-[8%] top-1/2 size-[25%] -translate-y-1/2 rounded-full bg-white" />
        <span className="absolute right-[8%] top-1/2 size-[25%] -translate-y-1/2 rounded-full bg-white" />
      </span>
      <span
        className={`${compact ? "text-xl" : "text-2xl"} font-semibold tracking-[-0.02em] text-[var(--color-brand-text-primary)]`}
      >
        InterviewX
      </span>
    </div>
  )
}
