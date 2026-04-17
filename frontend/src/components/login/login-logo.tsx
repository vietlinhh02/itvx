type LoginLogoProps = {
  compact?: boolean
}

export function LoginLogo({ compact = false }: LoginLogoProps) {
  const logoSize = compact ? "size-8" : "size-12"

  return (
    <div className="inline-flex items-center gap-2">
      <span aria-hidden className={`${logoSize} inline-flex shrink-0`}>
        <svg className="h-full w-full" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <radialGradient id="interviewx-logo-core" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="translate(22 18) rotate(49.97) scale(54.878 54.878)">
              <stop stopColor="#F5FAFF" />
              <stop offset="0.38" stopColor="#DCEEFF" />
              <stop offset="0.72" stopColor="#B7DCF8" />
              <stop offset="1" stopColor="#8CC7EE" />
            </radialGradient>
            <linearGradient id="interviewx-logo-wave" x1="18" y1="18" x2="48" y2="50" gradientUnits="userSpaceOnUse">
              <stop stopColor="#FFFFFF" stopOpacity="0.92" />
              <stop offset="1" stopColor="#D8F1FF" stopOpacity="0.38" />
            </linearGradient>
            <linearGradient id="interviewx-logo-wave-soft" x1="24" y1="10" x2="50" y2="36" gradientUnits="userSpaceOnUse">
              <stop stopColor="#FFFFFF" stopOpacity="0.7" />
              <stop offset="1" stopColor="#FFFFFF" stopOpacity="0.12" />
            </linearGradient>
          </defs>
          <circle cx="32" cy="32" r="28" fill="url(#interviewx-logo-core)" />
          <path
            d="M14 36C18.5 30.8 25.2 28 32.8 28C41 28 47.6 31.1 50 36.8C47 44.2 40.2 49.5 32 49.5C23.4 49.5 16.3 43.7 14 36Z"
            fill="url(#interviewx-logo-wave)"
          />
          <path
            d="M20 24.5C23.7 20.7 28.2 18.8 33.3 18.8C38.7 18.8 43.6 21.1 46.8 25.2C44.2 28.3 39.9 30.2 35 30.2C29.4 30.2 24.2 28.1 20 24.5Z"
            fill="url(#interviewx-logo-wave-soft)"
          />
          <circle cx="24" cy="22" r="5.5" fill="white" fillOpacity="0.26" />
        </svg>
      </span>
      <span
        className={`${compact ? "text-xl" : "text-2xl"} font-semibold tracking-[-0.02em] text-[var(--color-brand-text-primary)]`}
      >
        InterviewX
      </span>
    </div>
  )
}
