"use client"

import { useCallback, useEffect, useMemo, useState } from "react"

import { LiveKitRoom, RoomAudioRenderer, useMediaDevices } from "@livekit/components-react"

import { ConversationPanel } from "@/components/interview/live-room/live-room-conversation-panel"
import {
  ControlDock,
  MicrophoneSelector,
  ParticipantCard,
  StatusChip,
} from "@/components/interview/live-room/live-room-shell-parts"
import {
  buildAudioCaptureOptions,
  formatLabel,
  normalizeDeviceLabel,
  shortenRoomName,
} from "@/components/interview/live-room/live-room-utils"
import {
  ConnectedAiWavePreview,
  PreJoinAiWavePreview,
  Toast,
} from "@/components/interview/live-room/live-room-waves"
import type { InterviewSessionDetailResponse } from "@/components/interview/interview-types"
import { SessionStatusCard } from "@/components/interview/session-status-card"

export function LiveRoom({
  participantName,
  roomName,
  participantToken,
  sessionDetail,
}: {
  participantName: string
  roomName: string
  participantToken: string
  sessionDetail?: InterviewSessionDetailResponse | null
}) {
  const serverUrl = process.env.NEXT_PUBLIC_LIVEKIT_URL ?? ""
  const [connectRoom, setConnectRoom] = useState(false)
  const [audioEnabled, setAudioEnabled] = useState(true)
  const [videoEnabled, setVideoEnabled] = useState(false)
  const [toastMessage, setToastMessage] = useState<string | null>(null)
  const [showStatus, setShowStatus] = useState(false)
  const [selectedAudioDeviceId, setSelectedAudioDeviceId] = useState<string | null>(null)
  const [microphoneMenuOpen, setMicrophoneMenuOpen] = useState(false)
  const handleDeviceError = useCallback((error: Error) => {
    setToastMessage((current) => (current === error.message ? current : error.message))
  }, [])
  const audioDevices = useMediaDevices({
    kind: "audioinput",
    onError: handleDeviceError,
  })

  const candidateSeed = useMemo(() => participantName.trim() || "candidate", [participantName])
  const aiSeed = useMemo(() => `ai-${roomName}`, [roomName])
  const selectedAudioDeviceLabel = useMemo(() => {
    const fallback = audioDevices[0]
    const matchedDevice = audioDevices.find((device) => device.deviceId === selectedAudioDeviceId) ?? fallback

    if (!matchedDevice) {
      return "Chọn micro"
    }

    return normalizeDeviceLabel(
      matchedDevice.label,
      Math.max(audioDevices.findIndex((device) => device.deviceId === matchedDevice.deviceId), 0),
    )
  }, [audioDevices, selectedAudioDeviceId])
  const audioCaptureOptions = useMemo(
    () => buildAudioCaptureOptions(audioEnabled, selectedAudioDeviceId),
    [audioEnabled, selectedAudioDeviceId],
  )
  const roomAudioCaptureDefaults = audioCaptureOptions === false ? undefined : audioCaptureOptions
  const shouldPromptCandidateToStart = connectRoom && (sessionDetail?.transcript_turns.length ?? 0) === 0

  useEffect(() => {
    console.info("[LiveRoom] mounted", {
      roomName,
      hasToken: Boolean(participantToken),
      serverUrl,
      connectRoom,
      workerStatus: sessionDetail?.worker_status,
      providerStatus: sessionDetail?.provider_status,
    })
  }, [connectRoom, participantToken, roomName, serverUrl, sessionDetail])

  useEffect(() => {
    if (!toastMessage) {
      return
    }

    const timer = window.setTimeout(() => {
      setToastMessage(null)
    }, 5000)

    return () => window.clearTimeout(timer)
  }, [toastMessage])

  useEffect(() => {
    if (connectRoom || typeof navigator === "undefined") {
      return
    }

    let cancelled = false

    async function primeAudioDevices() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false })
        if (cancelled) {
          stream.getTracks().forEach((track) => track.stop())
          return
        }
        stream.getTracks().forEach((track) => track.stop())
      } catch (error) {
        if (error instanceof Error) {
          handleDeviceError(error)
        }
      }
    }

    void primeAudioDevices()

    return () => {
      cancelled = true
    }
  }, [connectRoom, handleDeviceError])

  useEffect(() => {
    const selectors = [
      ".lk-room-container",
      ".lk-focus-layout",
      ".lk-audio-conference-stage",
      ".lk-participant-tile",
      ".lk-participant-media-video",
    ]

    selectors.forEach((selector) => {
      const elements = document.querySelectorAll<HTMLElement>(selector)
      elements.forEach((element) => {
        element.style.background = "transparent"
        element.style.backgroundColor = "transparent"
        element.style.boxShadow = "none"
        element.style.border = "0"
      })
    })
  }, [connectRoom])

  return (
    <div data-testid="meeting-shell" className="min-h-screen bg-[var(--color-brand-background,#f7fbfb)] px-4 py-6 lg:px-8">
      {toastMessage ? <Toast message={toastMessage} onClose={() => setToastMessage(null)} /> : null}
      <div className="flex w-full flex-col gap-6">
        <section className="rounded-[24px] bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-sm font-medium text-[var(--color-brand-text-muted)]">Phòng phỏng vấn</p>
              <h1 className="mt-2 text-3xl font-semibold text-[var(--color-brand-text-primary)]">
                {roomName}
              </h1>
              <p className="mt-2 text-sm text-[var(--color-brand-text-body)]">
                Tham gia phiên phỏng vấn trực tiếp cùng InterviewX AI trong một giao diện gọn và tập trung.
              </p>
            </div>
            {sessionDetail ? (
              <button
                type="button"
                onClick={() => setShowStatus((value) => !value)}
                className="rounded-full bg-[var(--color-brand-primary)] px-4 py-3 text-sm font-semibold text-white"
              >
                {showStatus ? "Ẩn trạng thái" : "Hiện trạng thái"}
              </button>
            ) : null}
          </div>
        </section>

        {!connectRoom ? (
          <div className="flex flex-col gap-6">
            <section className="rounded-[24px] bg-white p-4 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
              <div className="grid gap-3 xl:grid-cols-[minmax(240px,0.9fr)_minmax(240px,0.9fr)_110px_minmax(180px,0.7fr)_110px]">
                <ParticipantCard
                  testId="candidate-avatar-tile"
                  label={participantName || "Bạn"}
                  subtitle="Xem trước ứng viên"
                  seed={candidateSeed}
                />
                <ParticipantCard
                  testId="ai-avatar-tile"
                  label="InterviewX AI"
                  subtitle="AI phỏng vấn"
                  seed={aiSeed}
                  tone="primary"
                />
                <StatusChip label="Chế độ" value="Giọng nói" />
                <StatusChip label="Phòng" value={roomName} />
                <StatusChip label="Sẵn sàng" value="Trước khi vào phòng" />
              </div>
            </section>

            <section className="rounded-[24px] bg-white p-8 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)] lg:p-10">
              <p className="text-sm font-medium text-[var(--color-brand-text-muted)]">Kiểm tra trước khi vào</p>
              <h2 className="mt-2 text-3xl font-semibold text-[var(--color-brand-text-primary)]">
                Tham gia phòng phỏng vấn
              </h2>
              <p className="mt-3 max-w-2xl text-base leading-7 text-[var(--color-brand-text-body)]">
                Kiểm tra micro và camera, sau đó kết nối khi bạn đã sẵn sàng.
              </p>
              <div className="interview-prejoin-shell mt-8 space-y-5 rounded-[20px] border border-[var(--color-brand-input-border)] bg-[var(--color-primary-50)]/40 p-5">
                <PreJoinAiWavePreview />
                <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
                  <MicrophoneSelector
                    devices={audioDevices}
                    selectedAudioDeviceId={selectedAudioDeviceId}
                    selectedAudioDeviceLabel={selectedAudioDeviceLabel}
                    dropdownOpen={microphoneMenuOpen}
                    onToggle={() => setMicrophoneMenuOpen((open) => !open)}
                    onSelect={(deviceId) => {
                      setSelectedAudioDeviceId(deviceId)
                      setMicrophoneMenuOpen(false)
                    }}
                  />
                  <div className="rounded-[20px] border border-[var(--color-brand-input-border)] bg-white p-5 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
                    <p className="text-xs font-semibold text-[var(--color-brand-text-muted)]">Kiểm tra thiết bị</p>
                    <div className="mt-3 space-y-3">
                      <label className="flex items-center justify-between rounded-full border border-[var(--color-brand-input-border)] bg-white px-4 py-3 text-sm font-semibold text-[var(--color-brand-text-primary)]">
                        <span>Micro</span>
                        <input
                          type="checkbox"
                          className="h-4 w-4 accent-[var(--color-brand-primary)]"
                          checked={audioEnabled}
                          onChange={(event) => setAudioEnabled(event.target.checked)}
                        />
                      </label>
                      <label className="flex items-center justify-between rounded-full border border-[var(--color-brand-input-border)] bg-white px-4 py-3 text-sm font-semibold text-[var(--color-brand-text-primary)]">
                        <span>Camera</span>
                        <input
                          type="checkbox"
                          className="h-4 w-4 accent-[var(--color-brand-primary)]"
                          checked={videoEnabled}
                          onChange={(event) => setVideoEnabled(event.target.checked)}
                        />
                      </label>
                      <button
                        type="button"
                        className="min-h-12 w-full rounded-full bg-[var(--color-brand-primary)] px-5 py-3 text-sm font-semibold text-white"
                        onClick={() => {
                          setToastMessage(null)
                          setMicrophoneMenuOpen(false)
                          setConnectRoom(true)
                        }}
                      >
                        Kết nối vào buổi phỏng vấn
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </section>
          </div>
        ) : (
          <LiveKitRoom
            token={participantToken}
            serverUrl={serverUrl}
            connect={connectRoom}
            audio={audioCaptureOptions}
            video={videoEnabled}
            options={{
              audioCaptureDefaults: roomAudioCaptureDefaults,
            }}
            data-lk-theme="default"
            className="grid min-h-[calc(100vh-7rem)] grid-cols-1 gap-6 bg-transparent [--lk-bg:transparent] [--lk-background:transparent] [--lk-overlay-bg:transparent] xl:grid-cols-[minmax(360px,0.9fr)_minmax(0,1.35fr)] [&_.lk-room-container]:bg-transparent [&_.lk-room-container]:shadow-none [&_.lk-room-container]:border-0 [&_.lk-focus-layout]:bg-transparent [&_.lk-participant-tile]:bg-transparent [&_.lk-participant-media-video]:bg-transparent [&_.lk-audio-conference-stage]:bg-transparent"
            onDisconnected={() => setConnectRoom(false)}
            onError={handleDeviceError}
          >
            <RoomAudioRenderer />

            <div className="flex min-h-0 flex-col gap-4">
              <section className="rounded-[24px] bg-white p-4 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
                <div className="grid gap-2 xl:grid-cols-[minmax(160px,1fr)_minmax(160px,1fr)_84px_160px_84px]">
                  <ParticipantCard
                    testId="candidate-avatar-tile"
                    label={participantName}
                    subtitle="Bạn đã kết nối"
                    seed={candidateSeed}
                  />
                  <ParticipantCard
                    testId="ai-avatar-tile"
                    label="InterviewX AI"
                    subtitle="AI phỏng vấn"
                    seed={aiSeed}
                    tone="primary"
                  />
                  <StatusChip label="Chế độ" value="Giọng nói" />
                  <StatusChip label="Phòng" value={shortenRoomName(roomName)} />
                  <StatusChip label="Trạng thái" value={formatLabel(sessionDetail?.status ?? "Connected")} />
                </div>
                <div className="mt-4 rounded-[18px] border border-[var(--color-brand-input-border)] bg-[var(--color-primary-50)]/35 p-4">
                  <p className="text-sm font-medium text-[var(--color-brand-text-muted)]">Điều khiển trong phòng</p>
                  {shouldPromptCandidateToStart ? (
                    <div className="mt-3 rounded-[16px] border border-[var(--color-brand-input-border)] bg-white px-4 py-3 text-sm text-[var(--color-brand-text-body)]">
                      Hãy nói một câu ngắn để bắt đầu cuộc phỏng vấn. AI sẽ phản hồi ngay sau khi nghe thấy bạn.
                    </div>
                  ) : null}
                  <div className="mt-3">
                    <ConnectedAiWavePreview />
                  </div>
                  <div className="mt-3">
                    <ControlDock />
                  </div>
                </div>
              </section>
              {sessionDetail && showStatus ? (
                <SessionStatusCard
                  status={sessionDetail.status}
                  workerStatus={sessionDetail.worker_status}
                  providerStatus={sessionDetail.provider_status}
                />
              ) : null}
            </div>

            <div className="min-h-0 overflow-y-auto">
              <ConversationPanel sessionDetail={sessionDetail} />
            </div>
          </LiveKitRoom>
        )}
      </div>
    </div>
  )
}
