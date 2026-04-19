"use client"

import { useEffect, useMemo, useState } from "react"

import Link from "next/link"

import { LiveRoom } from "@/components/interview/live-room"
import { InterviewSchedulePicker } from "@/components/interview/interview-schedule-picker"
import type {
  CandidateJoinRequest,
  CandidateJoinPreviewResponse,
  CandidateJoinResponse,
  InterviewSessionDetailResponse,
  ProposeInterviewScheduleRequest,
} from "@/components/interview/interview-types"
import { resolveApiBaseUrl } from "@/lib/api"
import { APP_TIME_ZONE, formatVietnamDateTime, vietnamInputValueToIso } from "@/lib/datetime"

type PersistedJoinState = {
  candidateName: string
}

function InterviewEndedDialog() {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 px-4">
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="interview-ended-title"
        className="w-full max-w-lg rounded-[28px] bg-white p-8 shadow-[0px_24px_80px_0px_rgba(15,79,87,0.18)]"
      >
        <p className="text-sm font-medium text-[var(--color-brand-text-muted)]">Phỏng vấn</p>
        <h1 id="interview-ended-title" className="mt-2 text-3xl font-semibold text-[var(--color-brand-text-primary)]">
          Buổi phỏng vấn đã kết thúc
        </h1>
        <p className="mt-4 text-base leading-7 text-[var(--color-brand-text-body)]">
          Cảm ơn bạn đã dành thời gian tham gia buổi phỏng vấn.
        </p>
        <p className="mt-3 text-sm leading-6 text-[var(--color-brand-text-body)]">
          Link phỏng vấn này đã hết hiệu lực và không thể dùng để vào lại phòng.
        </p>
        <div className="mt-6">
          <Link
            href="/"
            className="inline-flex min-h-12 items-center justify-center rounded-full bg-[var(--color-brand-primary)] px-5 py-3 text-sm font-semibold text-white"
          >
            Quay về trang chủ
          </Link>
        </div>
      </section>
    </div>
  )
}

function formatSchedule(value: string | null | undefined) {
  if (!value) {
    return "Chưa có thời gian họp được xác nhận."
  }

  return `${formatVietnamDateTime(value)} (ICT)`
}

function hasInterviewEnded(detail: InterviewSessionDetailResponse | null) {
  if (!detail) {
    return false
  }

  if (detail.status === "finishing" || detail.status === "completed") {
    return true
  }

  return detail.worker_status === "completed" && detail.provider_status === "completed"
}

export function CandidateJoin({ token, backendBaseUrl }: { token: string; backendBaseUrl: string }) {
  const [joinPayload, setJoinPayload] = useState<CandidateJoinResponse | null>(null)
  const [joinPreview, setJoinPreview] = useState<CandidateJoinPreviewResponse | null>(null)
  const [sessionDetail, setSessionDetail] = useState<InterviewSessionDetailResponse | null>(null)
  const [isLinkExpired, setIsLinkExpired] = useState(false)
  const [isJoining, setIsJoining] = useState(false)
  const [isScheduling, setIsScheduling] = useState(false)
  const [candidateName, setCandidateName] = useState("")
  const [proposedStartAt, setProposedStartAt] = useState("")
  const [proposedNote, setProposedNote] = useState("")
  const [error, setError] = useState<string | null>(null)
  const storageKey = useMemo(() => `interviewx:candidate-join:${token}`, [token])
  const apiBaseUrl = useMemo(() => resolveApiBaseUrl(backendBaseUrl), [backendBaseUrl])

  function markLinkExpired() {
    setIsLinkExpired(true)
    setError(null)
    setJoinPayload(null)
    setJoinPreview(null)
    setSessionDetail(null)
  }

  useEffect(() => {
    const raw = window.sessionStorage.getItem(storageKey)
    if (!raw) {
      return
    }

    try {
      const persisted = JSON.parse(raw) as PersistedJoinState
      setCandidateName(persisted.candidateName ?? "")
    } catch {
      window.sessionStorage.removeItem(storageKey)
    }
  }, [storageKey])

  useEffect(() => {
    const persistedState: PersistedJoinState = {
      candidateName,
    }
    window.sessionStorage.setItem(storageKey, JSON.stringify(persistedState))
  }, [candidateName, storageKey])

  useEffect(() => {
    let isDisposed = false

    async function loadJoinPreview() {
      try {
        const response = await fetch(`${apiBaseUrl}/interviews/join/${token}`, {
          cache: "no-store",
        })
        if (response.status === 404) {
          if (!isDisposed) {
            markLinkExpired()
          }
          return
        }
        if (!response.ok || isDisposed) {
          return
        }

        const preview = (await response.json()) as CandidateJoinPreviewResponse
        if (!isDisposed) {
          setJoinPreview(preview)
        }
      } catch {
        // Preview is non-blocking for candidate entry.
      }
    }

    void loadJoinPreview()

    return () => {
      isDisposed = true
    }
  }, [apiBaseUrl, token])

  useEffect(() => {
    if (!joinPayload) {
      return
    }

    const sessionId = joinPayload.session_id
    let isDisposed = false

    async function pollSessionDetail() {
      try {
        const response = await fetch(`${apiBaseUrl}/interviews/sessions/${sessionId}`, {
          cache: "no-store",
        })
        if (!response.ok || isDisposed) {
          return
        }

        const detail = (await response.json()) as InterviewSessionDetailResponse
        if (!isDisposed) {
          setSessionDetail(detail)
        }
      } catch {
        // Polling can fail transiently during room setup; keep the UI stable.
      }
    }

    void pollSessionDetail()
    const timer = window.setInterval(() => {
      void pollSessionDetail()
    }, 3000)

    return () => {
      isDisposed = true
      window.clearInterval(timer)
    }
  }, [apiBaseUrl, joinPayload])

  useEffect(() => {
    if (!hasInterviewEnded(sessionDetail)) {
      return
    }

    markLinkExpired()
  }, [sessionDetail])

  async function handleProposeSchedule() {
    if (!proposedStartAt) {
      setError("Vui lòng chọn thời gian bạn muốn đề xuất.")
      return
    }

    setIsScheduling(true)
    setError(null)
    try {
      const response = await fetch(`${apiBaseUrl}/interviews/join/${token}/schedule`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        cache: "no-store",
        body: JSON.stringify({
          proposed_start_at: vietnamInputValueToIso(proposedStartAt),
          note: proposedNote.trim() || null,
          timezone: APP_TIME_ZONE,
        } satisfies ProposeInterviewScheduleRequest),
      })
      if (response.status === 404) {
        markLinkExpired()
        return
      }
      if (!response.ok) {
        setError("Không thể gửi đề xuất thời gian khác.")
        return
      }
      const schedule = (await response.json()) as CandidateJoinPreviewResponse["schedule"]
      setJoinPreview((current) =>
        current
          ? {
              ...current,
              schedule,
            }
          : current,
      )
    } catch {
      setError("Không thể kết nối tới dịch vụ phỏng vấn.")
    } finally {
      setIsScheduling(false)
    }
  }

  async function handleJoin() {
    const trimmedName = candidateName.trim()
    if (!trimmedName) {
      setError("Vui lòng nhập tên trước khi tham gia.")
      return
    }

    setIsJoining(true)
    setError(null)
    try {
      const response = await fetch(`${apiBaseUrl}/interviews/join/${token}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        cache: "no-store",
        body: JSON.stringify({ candidate_name: trimmedName } satisfies CandidateJoinRequest),
      })
      if (response.status === 404) {
        markLinkExpired()
        return
      }
      if (!response.ok) {
        setError("Không thể tham gia buổi phỏng vấn này.")
        return
      }
      const payload = (await response.json()) as CandidateJoinResponse
      setJoinPayload(payload)
    } catch {
      setError("Không thể kết nối tới dịch vụ phỏng vấn.")
    } finally {
      setIsJoining(false)
    }
  }

  if (joinPayload) {
    return (
      <LiveRoom
        participantName={candidateName.trim()}
        roomName={joinPayload.room_name}
        participantToken={joinPayload.participant_token}
        sessionDetail={sessionDetail}
      />
    )
  }

  if (isLinkExpired) {
    return <InterviewEndedDialog />
  }

  const scheduledStartAt =
    joinPreview?.schedule?.scheduled_start_at ?? sessionDetail?.schedule?.scheduled_start_at ?? null

  return (
    <section className="flex min-h-[calc(100vh-8rem)] items-center">
      <div className="w-full max-w-none px-4 py-8 lg:px-8">
        <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <section className="rounded-[24px] bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)] lg:p-8">
          <p className="text-sm font-medium text-[var(--color-brand-text-muted)]">Phỏng vấn</p>
          <h1 className="mt-2 text-3xl font-semibold text-[var(--color-brand-text-primary)]">
            Tham gia buổi phỏng vấn AI trực tiếp
          </h1>
          <p className="mt-3 text-sm leading-6 text-[var(--color-brand-text-body)]">
            Nhập tên của bạn, cho phép dùng micro và tiếp tục vào phòng phỏng vấn. Phiên trực tiếp này giữ cùng ngôn ngữ giao diện với trang sàng lọc CV: nền sáng, thẻ trắng và nút hành động chính rõ ràng.
          </p>
          <div className="mt-5 rounded-[16px] border border-[var(--color-brand-input-border)] p-4 text-sm text-[var(--color-brand-text-body)]">
            Thời gian đã hẹn: {formatSchedule(scheduledStartAt)}
          </div>
          <div className="mt-6 grid gap-3 sm:grid-cols-3">
            <div className="rounded-[16px] bg-[var(--color-primary-50)] px-4 py-3">
              <p className="text-xs font-semibold text-[var(--color-brand-text-muted)]">Hình thức</p>
              <p className="mt-2 text-sm font-medium text-[var(--color-brand-primary)]">Phỏng vấn giọng nói</p>
            </div>
            <div className="rounded-[16px] bg-[var(--color-primary-50)] px-4 py-3">
              <p className="text-xs font-semibold text-[var(--color-brand-text-muted)]">Luồng tham gia</p>
              <p className="mt-2 text-sm font-medium text-[var(--color-brand-primary)]">Kiểm tra trước rồi kết nối</p>
            </div>
            <div className="rounded-[16px] bg-[var(--color-primary-50)] px-4 py-3">
              <p className="text-xs font-semibold text-[var(--color-brand-text-muted)]">Theo dõi</p>
              <p className="mt-2 text-sm font-medium text-[var(--color-brand-primary)]">Bản ghi trực tiếp</p>
            </div>
          </div>
        </section>

        <section className="rounded-[24px] bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)] lg:p-8">
          <p className="text-sm font-medium text-[var(--color-brand-text-muted)]">Thông tin ứng viên</p>
          <label className="mt-4 block text-sm font-medium text-[var(--color-brand-text-primary)]" htmlFor="candidate-name">
            Tên của bạn
          </label>
          <input
            id="candidate-name"
            className="mt-2 w-full rounded-[16px] border border-[var(--color-brand-input-border)] p-4 text-sm outline-none"
            onChange={(event) => setCandidateName(event.target.value)}
            placeholder="Nguyen Van A"
            value={candidateName}
          />
          <InterviewSchedulePicker
            helperText="Dùng hai bước bên dưới để đề xuất một thời gian khác cho HR theo giờ Việt Nam (ICT, UTC+7). Bạn vẫn có thể tham gia ngay nếu muốn tiếp tục luôn."
            label="Đề xuất thời gian khác"
            noteLabel="Lời nhắn cho HR"
            noteValue={proposedNote}
            onChange={setProposedStartAt}
            onNoteChange={setProposedNote}
            summaryText={formatSchedule(scheduledStartAt)}
            value={proposedStartAt}
          />
          <div className="mt-5 flex flex-wrap gap-3">
            <button
              className="rounded-full bg-[var(--color-brand-primary)] px-5 py-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
              type="button"
              disabled={isJoining}
              onClick={() => void handleJoin()}
            >
              {isJoining ? "Đang tham gia..." : "Tham gia phỏng vấn"}
            </button>
            <button
              className="rounded-full border border-[var(--color-brand-input-border)] px-5 py-3 text-sm font-semibold text-[var(--color-brand-primary)] disabled:cursor-not-allowed disabled:opacity-60"
              type="button"
              disabled={isScheduling}
              onClick={() => void handleProposeSchedule()}
            >
              {isScheduling ? "Đang gửi..." : "Gửi đề xuất thời gian khác"}
            </button>
          </div>
          {error ? <p className="mt-4 text-sm text-rose-700">{error}</p> : null}
        </section>
        </div>
      </div>
    </section>
  )
}
