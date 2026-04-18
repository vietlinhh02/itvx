"use client"

import type { Route } from "next"
import { useRouter } from "next/navigation"
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react"

import type { BackgroundJobResponse } from "@/components/jd/cv-screening-types"
import { resolveApiBaseUrl } from "@/lib/api"

type TrackedJob = {
  jobId: string
  resourceId: string
  resourceType: "jd" | "screening"
  title: string
  accessToken: string
  backendBaseUrl: string
  status: BackgroundJobResponse["status"]
  pollDelayMs: number
}

type ToastItem = {
  id: string
  tone: "info" | "success" | "error"
  title: string
  description: string
  actionLabel?: string
  actionHref?: Route
}

type JobRegistration = Omit<TrackedJob, "status" | "pollDelayMs">

type JobTrackerContextValue = {
  registerJob: (job: JobRegistration) => void
}

function getToastToneClasses(tone: ToastItem["tone"]): string {
  if (tone === "error") {
    return "border-[var(--color-brand-primary)] bg-[var(--color-primary-50)]"
  }
  if (tone === "success") {
    return "border-[var(--color-brand-primary)] bg-[var(--color-primary-50)]"
  }
  return "border-[var(--color-brand-primary)] bg-[var(--color-primary-50)]"
}

const JobTrackerContext = createContext<JobTrackerContextValue | null>(null)

export function JobTrackerProvider({ children }: { children: ReactNode }) {
  const router = useRouter()
  const [jobs, setJobs] = useState<TrackedJob[]>([])
  const [toasts, setToasts] = useState<ToastItem[]>([])
  const timeoutRef = useRef<number | null>(null)
  const isPollingRef = useRef(false)
  const jobsRef = useRef<TrackedJob[]>([])

  const dismissToast = useCallback((id: string) => {
    setToasts((current) => current.filter((toast) => toast.id !== id))
  }, [])

  const pushToast = useCallback((toast: Omit<ToastItem, "id">) => {
    const id = crypto.randomUUID()
    setToasts((current) => [...current, { id, ...toast }])
    window.setTimeout(() => {
      dismissToast(id)
    }, 5000)
  }, [dismissToast])

  const registerJob = useCallback((job: JobRegistration) => {
    setJobs((current) => {
      if (current.some((item) => item.jobId === job.jobId)) {
        return current
      }
      return [...current, { ...job, status: "queued", pollDelayMs: 1500 }]
    })
    pushToast({
      tone: "info",
      title: job.resourceType === "jd" ? "Đã xếp hàng phân tích JD" : "Đã xếp hàng sàng lọc CV",
      description: `${job.title} đang chờ được xử lý ở chế độ nền.`,
    })
  }, [pushToast])

  useEffect(() => {
    jobsRef.current = jobs
  }, [jobs])

  useEffect(() => {
    if (jobs.length === 0) {
      if (timeoutRef.current !== null) {
        window.clearTimeout(timeoutRef.current)
        timeoutRef.current = null
      }
      isPollingRef.current = false
      return
    }

    const getNextDelay = (job: TrackedJob, payload: BackgroundJobResponse) => {
      if (payload.poll_after_ms && payload.poll_after_ms > 0) {
        return payload.poll_after_ms
      }
      if (payload.status === "queued") {
        return Math.min(job.pollDelayMs * 2, 5000)
      }
      if (payload.status === "running") {
        return Math.min(job.pollDelayMs + 1000, 8000)
      }
      return 0
    }

    const pollJobs = async () => {
      if (isPollingRef.current) {
        return
      }
      isPollingRef.current = true

      let nextDelay = 8000
      try {
        const currentJobs = jobsRef.current
        for (const job of currentJobs) {
          const apiBaseUrl = resolveApiBaseUrl(job.backendBaseUrl)
          const response = await fetch(`${apiBaseUrl}/jobs/${job.jobId}`, {
            headers: {
              Authorization: `Bearer ${job.accessToken}`,
            },
            cache: "no-store",
          })
          if (!response.ok) {
            nextDelay = Math.min(nextDelay, Math.min(job.pollDelayMs * 2, 8000))
            continue
          }

          const payload = (await response.json()) as BackgroundJobResponse
          nextDelay = Math.min(nextDelay, Math.max(getNextDelay(job, payload), 1500))

          setJobs((current) => current.map((item) => {
            if (item.jobId !== job.jobId) {
              return item
            }
            return {
              ...item,
              status: payload.status,
              pollDelayMs: Math.max(getNextDelay(item, payload), 1500),
            }
          }))

          if (job.status !== payload.status && payload.status === "running") {
            pushToast({
              tone: "info",
              title: job.resourceType === "jd" ? "Đang phân tích JD" : "Đang sàng lọc CV",
              description: payload.status_message ?? `${job.title} đang được xử lý ở chế độ nền.`,
            })
          }

          if (payload.status === "completed") {
            setJobs((current) => current.filter((item) => item.jobId !== job.jobId))
            const actionHref =
              job.resourceType === "jd"
                ? (`/dashboard/jd/${job.resourceId}` as Route)
                : (`/dashboard/cv-screenings/${job.resourceId}` as Route)
            pushToast({
              tone: "success",
              title: job.resourceType === "jd" ? "Phân tích JD đã sẵn sàng" : "Kết quả sàng lọc CV đã sẵn sàng",
              description: `${job.title} đã được xử lý xong.`,
              actionLabel: job.resourceType === "jd" ? "Mở JD" : "Mở kết quả sàng lọc",
              actionHref,
            })
            continue
          }

          if (payload.status === "failed") {
            setJobs((current) => current.filter((item) => item.jobId !== job.jobId))
            pushToast({
              tone: "error",
              title: job.resourceType === "jd" ? "Phân tích JD thất bại" : "Sàng lọc CV thất bại",
              description: payload.error_message ?? `${job.title} xử lý không thành công.`,
            })
          }
        }
      } finally {
        isPollingRef.current = false
        if (timeoutRef.current !== null) {
          window.clearTimeout(timeoutRef.current)
        }
        if (jobsRef.current.length > 0) {
          timeoutRef.current = window.setTimeout(() => {
            void pollJobs()
          }, nextDelay)
        }
      }
    }

    if (!isPollingRef.current && timeoutRef.current === null) {
      void pollJobs()
    }

    return () => {
      if (timeoutRef.current !== null) {
        window.clearTimeout(timeoutRef.current)
        timeoutRef.current = null
      }
      isPollingRef.current = false
    }
  }, [jobs.length, pushToast])

  const value = useMemo(() => ({ registerJob }), [registerJob])

  return (
    <JobTrackerContext.Provider value={value}>
      {children}
      <div className="pointer-events-none fixed bottom-4 right-4 z-50 flex w-full max-w-sm flex-col gap-3">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`pointer-events-auto rounded-[16px] border bg-white p-4 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.12)] ${getToastToneClasses(
              toast.tone,
            )}`}
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">{toast.title}</p>
                <p className="mt-1 text-sm text-[var(--color-brand-text-body)]">{toast.description}</p>
              </div>
              <button
                className="text-xs font-medium text-[var(--color-brand-text-muted)]"
                onClick={() => dismissToast(toast.id)}
                type="button"
              >
                Đóng
              </button>
            </div>
            {toast.actionHref && toast.actionLabel ? (
              <button
                className="mt-3 rounded-full bg-[var(--color-brand-primary)] px-3 py-2 text-xs font-semibold text-white"
                onClick={() => {
                  const href = toast.actionHref
                  if (href) {
                    router.push(href)
                  }
                  dismissToast(toast.id)
                }}
                type="button"
              >
                {toast.actionLabel}
              </button>
            ) : null}
          </div>
        ))}
      </div>
    </JobTrackerContext.Provider>
  )
}

export function useJobTracker() {
  const context = useContext(JobTrackerContext)
  if (!context) {
    throw new Error("useJobTracker must be used within JobTrackerProvider")
  }
  return context
}
