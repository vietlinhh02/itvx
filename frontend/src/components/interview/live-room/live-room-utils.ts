import { Track, type AudioCaptureOptions } from "livekit-client"

export { Track }

export function buildDiceBearAvatar(seed: string, style: "bottts-neutral" | "notionists-neutral") {
  return `https://api.dicebear.com/9.x/${style}/svg?seed=${encodeURIComponent(seed)}`
}

export function buildAudioCaptureOptions(
  audioEnabled: boolean,
  selectedAudioDeviceId: string | null,
): AudioCaptureOptions | false {
  if (!audioEnabled) {
    return false
  }

  return {
    deviceId: selectedAudioDeviceId ?? undefined,
    autoGainControl: true,
    channelCount: 1,
    echoCancellation: true,
    noiseSuppression: true,
  }
}

export function normalizeDeviceLabel(label: string | undefined, index: number) {
  const trimmed = label?.trim()
  if (trimmed) {
    return trimmed
  }

  return index === 0 ? "Micro mặc định" : `Micro ${index + 1}`
}

export function formatLabel(value: string | null | undefined) {
  if (!value) {
    return "Chưa có dữ liệu"
  }

  const localizedMap: Record<string, string> = {
    continue: "Tiếp tục",
    adjust: "Điều chỉnh",
    ready_to_wrap: "Sẵn sàng kết thúc",
    escalate_hr: "Chuyển cho HR",
    not_started: "Chưa bắt đầu",
    in_progress: "Đang diễn ra",
    completed: "Hoàn tất",
    failed: "Thất bại",
    waiting: "Đang chờ",
    responding: "Đang phản hồi",
    idle: "Nhàn",
    review: "Cần xem lại",
    reject: "Từ chối",
    advance: "Tiến tiếp",
    recovery: "Khôi phục",
    clarification: "Làm rõ",
    manual: "Thủ công",
    adaptive: "Thích ứng",
    planned: "Đã lên kế hoạch",
    competency_validation: "Xác thực năng lực",
    gemini_live: "Gemini live",
  }

  if (localizedMap[value]) {
    return localizedMap[value]
  }

  return value
    .split(/[._-]+/)
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(" ")
}

export function shortenRoomName(value: string) {
  if (value.length <= 24) {
    return value
  }

  return `${value.slice(0, 12)}...${value.slice(-6)}`
}
