import { formatVietnamDateTime } from "@/lib/datetime"

export function parseQuestionLines(value: string) {
  return value
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean)
}

export function resolveApiBaseUrl(backendBaseUrl: string) {
  if (typeof window === "undefined") {
    return backendBaseUrl
  }

  return "/api/v1"
}

export function formatSchedule(value: string | null) {
  if (!value) {
    return "Chưa đặt lịch phỏng vấn."
  }

  return `${formatVietnamDateTime(value)} (ICT)`
}
