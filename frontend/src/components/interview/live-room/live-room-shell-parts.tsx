"use client"

import Image from "next/image"
import { useMemo, useState } from "react"

import {
  DisconnectButton,
  StartAudio,
  TrackToggle,
} from "@livekit/components-react"
import { CaretDown, Microphone, PhoneDisconnect, VideoCamera } from "@phosphor-icons/react"

import { buildDiceBearAvatar, normalizeDeviceLabel, Track } from "@/components/interview/live-room/live-room-utils"
import { useSessionStorageState } from "@/hooks/use-persisted-ui-state"

export function MicrophoneSelector({
  devices,
  selectedAudioDeviceId,
  selectedAudioDeviceLabel,
  dropdownOpen,
  onToggle,
  onSelect,
}: {
  devices: MediaDeviceInfo[]
  selectedAudioDeviceId: string | null
  selectedAudioDeviceLabel: string
  dropdownOpen: boolean
  onToggle: () => void
  onSelect: (deviceId: string) => void
}) {
  return (
    <div className="rounded-[20px] border border-[var(--color-brand-input-border)] bg-white p-5 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
      <p className="text-xs font-semibold text-[var(--color-brand-text-muted)]">Micro</p>
      <div className="relative mt-3">
        <button
          type="button"
          onClick={onToggle}
          className="flex min-h-12 w-full items-center justify-between rounded-full border border-[var(--color-brand-input-border)] bg-white px-4 py-3 text-left text-sm font-semibold text-[var(--color-brand-text-primary)] shadow-none"
          aria-expanded={dropdownOpen}
          aria-haspopup="listbox"
        >
          <span className="truncate">{selectedAudioDeviceLabel}</span>
          <CaretDown className="shrink-0 text-[var(--color-brand-primary)]" size={18} weight="bold" />
        </button>
        {dropdownOpen ? (
          <div
            className="absolute left-0 right-0 top-full z-20 mt-2 overflow-hidden rounded-[16px] border border-[var(--color-brand-input-border)] bg-white shadow-[0px_10px_30px_0px_rgba(15,79,87,0.12)]"
            role="listbox"
            aria-label="Danh sách micro"
          >
            <div className="bg-[var(--color-primary-50)] px-3 py-2 text-xs font-semibold text-[var(--color-brand-text-muted)]">
              Micro khả dụng
            </div>
            <div className="max-h-72 overflow-y-auto py-1">
              {devices.map((device, index) => {
                const label = normalizeDeviceLabel(device.label, index)
                const isSelected = device.deviceId === selectedAudioDeviceId

                return (
                  <button
                    key={device.deviceId}
                    type="button"
                    role="option"
                    aria-selected={isSelected}
                    onClick={() => onSelect(device.deviceId)}
                    className={`flex w-full items-center justify-between px-3 py-3 text-left text-sm font-medium ${
                      isSelected
                        ? "bg-[var(--color-primary-50)] text-[var(--color-brand-primary)]"
                        : "bg-white text-[var(--color-brand-text-primary)] hover:bg-[var(--color-primary-50)]"
                    }`}
                  >
                    <span className="truncate">{label}</span>
                    {isSelected ? <span className="text-xs font-semibold">Đã chọn</span> : null}
                  </button>
                )
              })}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  )
}

export function ParticipantCard({
  label,
  subtitle,
  seed,
  tone = "default",
  testId,
}: {
  label: string
  subtitle: string
  seed: string
  tone?: "default" | "primary"
  testId: string
}) {
  const avatarSrc = buildDiceBearAvatar(seed, tone === "primary" ? "bottts-neutral" : "notionists-neutral")

  return (
    <article
      data-testid={testId}
      className={`rounded-[14px] border px-2.5 py-1.5 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)] ${
        tone === "primary"
          ? "border-[var(--color-brand-primary)] bg-[var(--color-primary-50)]"
          : "border-[var(--color-brand-input-border)] bg-white"
      }`}
    >
      <div className="flex items-center gap-2">
        <Image
          alt={`${label} avatar`}
          className="h-7 w-7 rounded-full border border-[var(--color-brand-input-border)] bg-white object-cover"
          height={28}
          src={avatarSrc}
          width={28}
          unoptimized
        />
        <div className="min-w-0">
          <p className="truncate text-[13px] font-semibold text-[var(--color-brand-text-primary)]">{label}</p>
          <p className="mt-0.5 truncate text-[10px] text-[var(--color-brand-text-muted)]">{subtitle}</p>
        </div>
      </div>
    </article>
  )
}

export function ControlDock() {
  return (
    <div
      data-testid="meeting-controls"
      className="flex flex-wrap items-center gap-3 rounded-[20px] border border-[var(--color-brand-input-border)] bg-[var(--color-primary-50)]/55 p-4"
    >
      <StartAudio
        label="Bật âm thanh"
        className="rounded-full border border-[var(--color-brand-input-border)] px-4 py-3 text-sm font-medium text-[var(--color-brand-primary)]"
      />
      <TrackToggle
        source={Track.Source.Microphone}
        showIcon={false}
        className="rounded-full border border-[var(--color-brand-input-border)] px-4 py-3 text-sm font-medium text-[var(--color-brand-primary)]"
      >
        <span className="inline-flex items-center gap-2">
          <Microphone size={18} weight="fill" />
          Micro
        </span>
      </TrackToggle>
      <TrackToggle
        source={Track.Source.Camera}
        showIcon={false}
        className="rounded-full border border-[var(--color-brand-input-border)] px-4 py-3 text-sm font-medium text-[var(--color-brand-primary)]"
      >
        <span className="inline-flex items-center gap-2">
          <VideoCamera size={18} weight="fill" />
          Camera
        </span>
      </TrackToggle>
      <DisconnectButton className="rounded-full bg-[var(--color-brand-primary)] px-4 py-3 text-sm font-semibold text-white">
        <span className="inline-flex items-center gap-2">
          <PhoneDisconnect size={18} weight="fill" />
          Rời buổi phỏng vấn
        </span>
      </DisconnectButton>
    </div>
  )
}

export function StatusChip({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[10px] bg-[var(--color-primary-50)] px-2 py-1.5">
      <p className="text-[9px] font-semibold text-[var(--color-brand-text-muted)]">{label}</p>
      <p className="mt-0.5 truncate text-[10px] font-medium text-[var(--color-brand-primary)]">{value}</p>
    </div>
  )
}

export function CoverageBar({ value }: { value: number }) {
  const percentage = Math.max(0, Math.min(100, Math.round(value * 100)))

  return (
    <div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-[var(--color-primary-50)]">
        <div className="h-full rounded-full bg-[var(--color-brand-primary)]" style={{ width: `${percentage}%` }} />
      </div>
      <p className="mt-2 text-xs text-[var(--color-brand-text-muted)]">Đã bao phủ {percentage}%</p>
    </div>
  )
}

export function CollapsibleSection({
  title,
  children,
  defaultOpen = false,
  persistKey,
}: {
  title: string
  children: React.ReactNode
  defaultOpen?: boolean
  persistKey?: string
}) {
  const fallbackKey = useMemo(() => `interviewx:collapsible:${title}`, [title])
  const storageKey = persistKey ?? fallbackKey
  const [persistedOpen, setPersistedOpen, hasHydrated] = useSessionStorageState<boolean>(storageKey, defaultOpen)
  const [uncontrolledOpen, setUncontrolledOpen] = useState(defaultOpen)
  const isOpen = persistKey ? persistedOpen : uncontrolledOpen
  const setIsOpen = persistKey ? setPersistedOpen : setUncontrolledOpen
  const contentClassName = isOpen
    ? "mt-4 grid-rows-[1fr] opacity-100"
    : "mt-0 grid-rows-[0fr] opacity-0"

  return (
    <section className="rounded-[16px] border border-[var(--color-brand-input-border)] bg-white p-4 transition-transform duration-200 hover:-translate-y-0.5">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-semibold text-[var(--color-brand-text-muted)]">{title}</p>
        <button
          type="button"
          onClick={() => setIsOpen((value) => !value)}
          className="inline-flex items-center gap-2 rounded-full border border-[var(--color-brand-input-border)] px-3 py-1 text-xs font-semibold text-[var(--color-brand-primary)]"
          aria-expanded={isOpen}
        >
          <CaretDown
            size={14}
            weight="bold"
            className={`transition-transform duration-300 ${isOpen ? "rotate-180" : "rotate-0"}`}
          />
          {isOpen ? "Thu gọn" : "Mở rộng"}
        </button>
      </div>
      <div
        className={`grid overflow-hidden transition-all duration-300 ease-in-out ${contentClassName}`}
        data-hydrated={persistKey ? hasHydrated : undefined}
      >
        <div className="overflow-hidden">
          <div>{children}</div>
        </div>
      </div>
    </section>
  )
}
