"use client"

import { useState } from "react"

import { formatSchedule } from "@/components/interview/interview-launch-panel/helpers"

export function ShareLinkModal({
  roomName,
  shareLink,
  scheduledStartAt,
  sessionId,
  onClose,
}: {
  roomName: string
  shareLink: string
  scheduledStartAt: string | null
  sessionId: string
  onClose: () => void
}) {
  const [copyStatus, setCopyStatus] = useState<"idle" | "copied" | "failed">("idle")

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(shareLink)
      setCopyStatus("copied")
    } catch {
      setCopyStatus("failed")
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <div className="w-full max-w-2xl rounded-[24px] bg-white p-6 shadow-[0px_20px_60px_0px_rgba(15,79,87,0.2)]">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-[var(--color-brand-text-muted)]">Liên kết tham gia</p>
            <h3 className="mt-2 text-2xl font-semibold text-[var(--color-brand-text-primary)]">
              Phòng phỏng vấn đã sẵn sàng
            </h3>
            <p className="mt-2 text-sm text-[var(--color-brand-text-body)]">
              Hãy gửi liên kết này cho ứng viên hoặc mở ngay.
            </p>
            <p className="mt-2 text-sm text-[var(--color-brand-text-body)]">
              Thời gian hẹn: {formatSchedule(scheduledStartAt)}
            </p>
            <p className="mt-2 text-sm text-[var(--color-brand-text-body)]">Session ID: {sessionId}</p>
            <p className="mt-1 text-sm text-[var(--color-brand-text-body)]">Room name: {roomName}</p>
          </div>
          <button
            className="rounded-full border border-[var(--color-brand-input-border)] px-4 py-2 text-sm font-medium text-[var(--color-brand-text-primary)]"
            onClick={onClose}
            type="button"
          >
            Đóng
          </button>
        </div>

        <div className="mt-5 rounded-[16px] border border-[var(--color-brand-input-border)] bg-[var(--color-primary-50)]/40 p-4">
          <p className="break-all text-sm text-[var(--color-brand-text-primary)]">{shareLink}</p>
        </div>

        <div className="mt-5 flex flex-wrap items-center gap-3">
          <button
            className="rounded-full bg-[var(--color-brand-primary)] px-5 py-3 text-sm font-semibold text-white"
            onClick={() => void handleCopy()}
            type="button"
          >
            Sao chép liên kết
          </button>
          <a
            className="rounded-full border border-[var(--color-brand-input-border)] px-5 py-3 text-sm font-semibold text-[var(--color-brand-primary)]"
            href={shareLink}
            rel="noreferrer"
            target="_blank"
          >
            Mở phòng họp
          </a>
          {copyStatus === "copied" ? <p className="text-sm text-emerald-700">Đã sao chép liên kết.</p> : null}
          {copyStatus === "failed" ? <p className="text-sm text-red-700">Không thể sao chép liên kết.</p> : null}
        </div>
      </div>
    </div>
  )
}
