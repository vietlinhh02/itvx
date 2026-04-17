import { formatVietnamDayLabel, formatVietnamDaySummary } from "@/lib/datetime"
import { CollapsibleSection } from "@/components/interview/live-room/live-room-shell-parts"

const timeSlots = [
  "09:00",
  "10:00",
  "11:00",
  "13:00",
  "14:00",
  "15:00",
  "16:00",
  "17:00",
  "19:00",
  "20:00",
] as const

type InterviewSchedulePickerProps = {
  label: string
  value: string
  onChange: (value: string) => void
  noteLabel: string
  noteValue: string
  onNoteChange: (value: string) => void
  summaryText: string
  helperText?: string
  disabled?: boolean
}

function toLocalDateKey(date: Date) {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "Asia/Ho_Chi_Minh",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(date)
  const values = Object.fromEntries(parts.map((entry) => [entry.type, entry.value]))
  return `${values.year ?? ""}-${values.month ?? ""}-${values.day ?? ""}`
}

function buildUpcomingDays() {
  const today = new Date()
  const todayKey = toLocalDateKey(today)
  const [yearText, monthText, dayText] = todayKey.split("-")
  const year = Number(yearText)
  const month = Number(monthText)
  const day = Number(dayText)

  return Array.from({ length: 14 }, (_, index) => {
    const nextDate = new Date(Date.UTC(year, month - 1, day + index, 12, 0, 0))
    return toLocalDateKey(nextDate)
  })
}

function toLocalDatetimeValue(dateKey: string, time: string) {
  return `${dateKey}T${time}`
}

function parseValue(value: string) {
  if (!value) {
    return { selectedDateKey: "", selectedTime: "" }
  }

  const [datePart, timePart] = value.split("T")
  return {
    selectedDateKey: datePart ?? "",
    selectedTime: timePart?.slice(0, 5) ?? "",
  }
}

export function InterviewSchedulePicker({
  label,
  value,
  onChange,
  noteLabel,
  noteValue,
  onNoteChange,
  summaryText,
  helperText,
  disabled = false,
}: InterviewSchedulePickerProps) {
  const upcomingDays = buildUpcomingDays()
  const { selectedDateKey, selectedTime } = parseValue(value)

  function handleDateSelect(dateKey: string) {
    const fallbackTime = selectedTime || timeSlots[0]
    onChange(toLocalDatetimeValue(dateKey, fallbackTime))
  }

  function handleTimeSelect(time: string) {
    const fallbackDate = selectedDateKey || upcomingDays[0]
    if (!fallbackDate) {
      return
    }
    onChange(toLocalDatetimeValue(fallbackDate, time))
  }

  return (
    <section className="mt-5 rounded-[20px] border border-[var(--color-brand-input-border)] bg-[var(--color-primary-50)]/35 p-5">
      <CollapsibleSection title={label}>
        <div>
          <p className="text-sm font-medium text-[var(--color-brand-text-muted)]">Lịch hẹn</p>
          {helperText ? (
            <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--color-brand-text-body)]">{helperText}</p>
          ) : null}
        </div>

        <div className="mt-5 rounded-[16px] border border-[var(--color-brand-input-border)] bg-white p-4">
          <p className="text-xs font-semibold text-[var(--color-brand-text-muted)]">Lựa chọn hiện tại</p>
          <p className="mt-2 text-sm font-medium text-[var(--color-brand-text-primary)]">{summaryText}</p>
        </div>

        <div className="mt-5 space-y-4">
          <section className="rounded-[18px] border border-[var(--color-brand-input-border)] bg-white p-4 sm:p-5">
            <div className="flex items-start gap-3">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[var(--color-primary-50)] text-sm font-semibold text-[var(--color-brand-primary)]">
                1
              </div>
              <div>
                <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">Chọn ngày</p>
                <p className="mt-1 text-sm text-[var(--color-brand-text-body)]">
                  Hãy chọn ngày trước, sau đó chọn khung giờ phù hợp.
                </p>
              </div>
            </div>

            <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-4">
              {upcomingDays.map((dateKey) => {
                const isSelected = dateKey === selectedDateKey
                return (
                  <button
                    key={dateKey}
                    className={[
                      "flex min-h-24 flex-col justify-between rounded-[18px] border px-4 py-3 text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-brand-primary)] focus-visible:ring-offset-2",
                      isSelected
                        ? "border-[var(--color-brand-primary)] bg-[var(--color-brand-primary)] text-white shadow-[0px_12px_24px_rgba(0,32,67,0.18)]"
                        : "border-[var(--color-brand-input-border)] bg-white text-[var(--color-brand-text-primary)] hover:border-[rgba(0,32,67,0.16)] hover:bg-[var(--color-primary-50)]/60",
                    ].join(" ")}
                    disabled={disabled}
                    onClick={() => handleDateSelect(dateKey)}
                    type="button"
                  >
                    <p className="text-[11px] font-semibold opacity-80">
                      {formatVietnamDayLabel(`${dateKey}T00:00:00+07:00`)}
                    </p>
                    <p className="mt-3 text-sm font-semibold leading-5 break-words">
                      {formatVietnamDaySummary(`${dateKey}T00:00:00+07:00`)}
                    </p>
                  </button>
                )
              })}
            </div>
          </section>

          <section className="rounded-[18px] border border-[var(--color-brand-input-border)] bg-white p-4 sm:p-5">
            <div className="flex items-start gap-3">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[var(--color-primary-50)] text-sm font-semibold text-[var(--color-brand-primary)]">
                2
              </div>
              <div>
                <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">Chọn giờ</p>
                <p className="mt-1 text-sm text-[var(--color-brand-text-body)]">
                  Khung giờ hiển thị theo giờ Việt Nam (ICT, UTC+7).
                </p>
              </div>
            </div>

            <div className="mt-4 flex flex-wrap gap-3">
              {timeSlots.map((time) => {
                const isSelected = time === selectedTime
                return (
                  <button
                    key={time}
                    className={[
                      "rounded-full border px-4 py-2 text-sm font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-brand-primary)] focus-visible:ring-offset-2",
                      isSelected
                        ? "border-[var(--color-brand-primary)] bg-[var(--color-brand-primary)] text-white"
                        : "border-[var(--color-brand-input-border)] bg-white text-[var(--color-brand-primary)] hover:border-[rgba(0,32,67,0.16)] hover:bg-[var(--color-primary-50)]/60",
                    ].join(" ")}
                    disabled={disabled}
                    onClick={() => handleTimeSelect(time)}
                    type="button"
                  >
                    {time}
                  </button>
                )
              })}
            </div>
          </section>
        </div>

        <label className="mt-5 block text-sm font-medium text-[var(--color-brand-text-primary)]" htmlFor={`${label}-note`}>
          {noteLabel}
        </label>
        <textarea
          id={`${label}-note`}
          className="mt-2 min-h-24 w-full rounded-[16px] border border-[var(--color-brand-input-border)] bg-white p-4 text-sm outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-brand-primary)] focus-visible:ring-offset-2"
          disabled={disabled}
          onChange={(event) => onNoteChange(event.target.value)}
          value={noteValue}
        />
      </CollapsibleSection>
    </section>
  )
}
