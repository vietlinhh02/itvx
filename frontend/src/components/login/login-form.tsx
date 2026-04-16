"use client"

import { useAuthStore } from "@/stores"

export function LoginForm() {
  const isLoading = useAuthStore((state) => state.isLoading)
  const error = useAuthStore((state) => state.error)
  const loginWithGoogle = useAuthStore((state) => state.loginWithGoogle)

  return (
    <div className="w-full space-y-7">
      <div className="flex items-center gap-3">
        <div className="h-px flex-1 bg-[var(--color-brand-input-border)]" />
        <p className="text-sm font-medium text-[var(--color-brand-text-muted)]">
          Sign in with your Gmail
        </p>
        <div className="h-px flex-1 bg-[var(--color-brand-input-border)]" />
      </div>

      <button
        className="flex h-[52px] w-full items-center justify-center gap-3 rounded-lg bg-[var(--color-brand-primary)] px-6 text-lg font-semibold text-white shadow-[inset_0px_4px_10px_rgba(255,255,255,0.08)] transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-70"
        disabled={isLoading}
        onClick={loginWithGoogle}
        type="button"
      >
        <GoogleMark />
        <span>{isLoading ? "Redirecting..." : "Continue with Google"}</span>
      </button>

      {error ? <p className="text-center text-sm font-medium text-red-600">{error}</p> : null}

      <p className="text-center text-base text-[var(--color-brand-text-body)]">
        Only authorized HR and Admin accounts can access InterviewX.
      </p>
    </div>
  )
}

function GoogleMark() {
  return (
    <svg aria-hidden className="size-5 rounded-full bg-white p-[2px]" viewBox="0 0 18 18">
      <path
        d="M17.64 9.2045C17.64 8.5677 17.5827 7.95545 17.4764 7.36719H9V10.8472H13.8436C13.635 11.9722 12.9975 12.9259 12.0409 13.5627V15.8209H14.9509C16.6536 14.2532 17.64 11.9405 17.64 9.2045Z"
        fill="#4285F4"
      />
      <path
        d="M9 18C11.43 18 13.4673 17.1941 14.9509 15.8209L12.0409 13.5627C11.235 14.1027 10.2041 14.4205 9 14.4205C6.65591 14.4205 4.67182 12.8373 3.96409 10.71H0.95591V13.0418C2.43136 15.9723 5.46318 18 9 18Z"
        fill="#34A853"
      />
      <path
        d="M3.96409 10.71C3.78409 10.17 3.68182 9.59318 3.68182 9.00091C3.68182 8.40864 3.78409 7.83182 3.96409 7.29182V4.96H0.95591C0.348182 6.17091 0 7.54227 0 9.00091C0 10.4595 0.348182 11.8309 0.95591 13.0418L3.96409 10.71Z"
        fill="#FBBC05"
      />
      <path
        d="M9 3.57955C10.3132 3.57955 11.4932 4.03136 12.4209 4.91864L15.0164 2.32318C13.4632 0.864545 11.4259 0 9 0C5.46318 0 2.43136 2.02773 0.95591 4.96L3.96409 7.29182C4.67182 5.16455 6.65591 3.57955 9 3.57955Z"
        fill="#EA4335"
      />
    </svg>
  )
}
