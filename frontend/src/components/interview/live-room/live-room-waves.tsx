"use client"

import { useEffect, useMemo, useState } from "react"

import { useAudioWaveform, useLocalParticipant } from "@livekit/components-react"

import { Track } from "@/components/interview/live-room/live-room-utils"

export function Toast({
  message,
  onClose,
}: {
  message: string
  onClose: () => void
}) {
  return (
    <div className="pointer-events-none fixed right-4 top-4 z-50 w-full max-w-sm">
      <div className="pointer-events-auto rounded-[16px] border border-[var(--color-brand-primary)] bg-white p-4 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.12)]">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">Lỗi thiết bị</p>
            <p className="mt-1 text-sm text-[var(--color-brand-text-body)]">{message}</p>
          </div>
          <button
            className="text-xs font-medium text-[var(--color-brand-text-muted)]"
            onClick={onClose}
            type="button"
          >
            Đóng
          </button>
        </div>
      </div>
    </div>
  )
}

function AiWavePreview({ levels, title }: { levels: number[]; title: string }) {
  const normalizedLevels = levels.length ? levels : [0.24, 0.4, 0.32, 0.52, 0.34, 0.42, 0.28]

  return (
    <div className="rounded-[20px] border border-[var(--color-brand-input-border)] bg-[linear-gradient(180deg,#f7fbff_0%,#eef4fb_100%)] p-5">
      <div className="flex min-h-[180px] flex-col items-center justify-center rounded-[18px] bg-white/70 px-4 py-5">
        <div className="flex items-center gap-2 rounded-full bg-[var(--color-primary-50)] px-4 py-2">
          <span className="text-xs font-semibold text-[var(--color-brand-primary)]">{title}</span>
        </div>
        <div className="mt-6 flex h-20 items-end gap-2">
          {normalizedLevels.map((level, index) => (
            <span
              key={index}
              className="w-3 rounded-full bg-[var(--color-brand-primary)] transition-[height,opacity] duration-200 ease-in-out"
              style={{
                height: `${Math.round(28 + level * 56)}px`,
                opacity: 0.45 + level * 0.5,
              }}
            />
          ))}
        </div>
        <p className="mt-4 max-w-md text-center text-xs text-[var(--color-brand-text-body)]">
          Phần kiểm tra micro và camera nằm bên dưới. Khung xem thử này được giữ nhẹ để màn hình trước khi vào phòng ổn định hơn trên nhiều thiết bị.
        </p>
      </div>
    </div>
  )
}

function useBrowserMicrophoneBars(barCount: number) {
  const [bars, setBars] = useState<number[]>([])

  useEffect(() => {
    let cancelled = false
    let animationFrame = 0
    let audioContext: AudioContext | null = null
    let stream: MediaStream | null = null
    let sourceNode: MediaStreamAudioSourceNode | null = null
    let analyser: AnalyserNode | null = null

    async function start() {
      try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false })
        if (cancelled) {
          stream.getTracks().forEach((track) => track.stop())
          return
        }

        audioContext = new window.AudioContext()
        sourceNode = audioContext.createMediaStreamSource(stream)
        analyser = audioContext.createAnalyser()
        analyser.fftSize = 256
        sourceNode.connect(analyser)

        const data = new Uint8Array(analyser.frequencyBinCount)
        const blockSize = Math.max(1, Math.floor(data.length / barCount))

        const tick = () => {
          if (!analyser) {
            return
          }

          analyser.getByteFrequencyData(data)
          const nextBars = Array.from({ length: barCount }, (_, index) => {
            const start = index * blockSize
            const end = Math.min(start + blockSize, data.length)
            let total = 0
            for (let cursor = start; cursor < end; cursor += 1) {
              total += data[cursor] ?? 0
            }
            const average = end > start ? total / (end - start) : 0
            return Math.min(1, average / 160)
          })
          setBars(nextBars)
          animationFrame = window.requestAnimationFrame(tick)
        }

        tick()
      } catch {
        setBars(Array.from({ length: barCount }, () => 0.18))
      }
    }

    void start()

    return () => {
      cancelled = true
      if (animationFrame) {
        window.cancelAnimationFrame(animationFrame)
      }
      sourceNode?.disconnect()
      analyser?.disconnect()
      stream?.getTracks().forEach((track) => track.stop())
      if (audioContext && audioContext.state !== "closed") {
        void audioContext.close()
      }
    }
  }, [barCount])

  return bars
}

export function PreJoinAiWavePreview() {
  const bars = useBrowserMicrophoneBars(7)

  return <AiWavePreview levels={bars} title="Xem thử âm thanh" />
}

export function ConnectedAiWavePreview() {
  const { microphoneTrack, localParticipant, isMicrophoneEnabled } = useLocalParticipant()
  const microphoneTrackRef = useMemo(
    () => ({
      participant: localParticipant,
      source: Track.Source.Microphone,
      publication: microphoneTrack,
    }),
    [localParticipant, microphoneTrack],
  )
  const { bars } = useAudioWaveform(microphoneTrackRef, {
    barCount: 7,
    volMultiplier: 6,
    updateInterval: 60,
  })

  const levels = useMemo(() => {
    if (!isMicrophoneEnabled) {
      return Array.from({ length: 7 }, () => 0.12)
    }

    if (!bars.length) {
      return Array.from({ length: 7 }, () => 0.18)
    }

    return bars.map((value) => Math.max(0.08, Math.min(1, value / 10)))
  }, [bars, isMicrophoneEnabled])

  return <AiWavePreview levels={levels} title="Mức hoạt động của micro" />
}
