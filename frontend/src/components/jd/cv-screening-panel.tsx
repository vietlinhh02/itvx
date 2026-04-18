"use client"
import { CaretDown } from "@phosphor-icons/react"
import type { Route } from "next"
import { useState } from "react"

import { useJobTracker } from "@/components/dashboard/job-tracker"

import type { CVScreeningEnqueueResponse, CVScreeningHistoryItem } from "@/components/jd/cv-screening-types"
import type { JDAnalysisResponse } from "@/components/jd/jd-upload-panel"
import { AppLink } from "@/components/navigation/app-link"
import { resolveApiBaseUrl } from "@/lib/api"
import { formatVietnamDateTime } from "@/lib/datetime"

type CVScreeningPanelProps = {
  accessToken: string
  backendBaseUrl: string
  jd: JDAnalysisResponse
  recentScreenings: CVScreeningHistoryItem[]
}

export function CVScreeningPanel({ accessToken, backendBaseUrl, jd, recentScreenings }: CVScreeningPanelProps) {
  const { registerJob } = useJobTracker()
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [latestScreening, setLatestScreening] = useState<CVScreeningEnqueueResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isRecentOpen, setIsRecentOpen] = useState(false)
  const apiBaseUrl = resolveApiBaseUrl(backendBaseUrl)

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (!selectedFile) {
      setError("Vui lòng chọn CV dạng PDF hoặc DOCX trước khi sàng lọc.")
      return
    }

    setIsSubmitting(true)
    setError(null)
    setLatestScreening(null)

    const formData = new FormData()
    formData.append("jd_id", jd.jd_id)
    formData.append("file", selectedFile)

    try {
      const response = await fetch(`${apiBaseUrl}/cv/screen`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
        body: formData,
      })

      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as { detail?: string } | null
        setError(payload?.detail ?? "Sàng lọc CV thất bại. Vui lòng thử lại.")
        return
      }

      const payload = (await response.json()) as CVScreeningEnqueueResponse
      setLatestScreening(payload)
      registerJob({
        jobId: payload.job_id,
        resourceId: payload.screening_id,
        resourceType: "screening",
        title: payload.file_name,
        accessToken,
        backendBaseUrl,
      })
    } catch {
      setError("Không thể kết nối tới backend. Hãy kiểm tra URL API rồi thử lại.")
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <section
      id="cv-screening-panel"
      className="scroll-mt-6 rounded-[24px] bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)] motion-safe:animate-[panel-enter_220ms_ease-out]"
    >
      <div>
        <p className="text-sm font-medium text-[var(--color-brand-text-muted)]">Giai đoạn 2 - Sàng lọc CV</p>
        <h2 className="mt-2 text-2xl font-semibold text-[var(--color-brand-text-primary)]">
          Sàng lọc một CV theo JD này
        </h2>
        <p className="mt-2 text-sm leading-6 text-[var(--color-brand-text-body)]">
          Tải một CV lên và xem khuyến nghị, bằng chứng cùng các điểm chưa chắc chắn mà AI đưa ra để HR rà soát.
        </p>
      </div>

      <div className="mt-6 rounded-[16px] border border-[var(--color-brand-input-border)] bg-[var(--color-primary-50)]/40 p-4">
        <button
          aria-controls="recent-cv-screenings"
          aria-expanded={isRecentOpen}
          className="flex w-full items-start justify-between gap-3 text-left"
          onClick={() => setIsRecentOpen((current) => !current)}
          type="button"
        >
          <div>
            <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">CV đã tải gần đây</p>
            <p className="mt-1 text-sm text-[var(--color-brand-text-body)]">
              Mở nhanh các lượt sàng lọc gần nhất của JD này để tiếp tục rà soát.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-[var(--color-brand-primary)]">
              {recentScreenings.length} lượt
            </span>
            <CaretDown
              className={`mt-1 text-[var(--color-brand-text-muted)] transition-transform duration-200 ${isRecentOpen ? "rotate-180" : ""}`}
              size={18}
              weight="bold"
            />
          </div>
        </button>

        {isRecentOpen ? (
          recentScreenings.length ? (
            <div id="recent-cv-screenings" className="mt-4 space-y-3">
              {recentScreenings.map((item) => (
                <AppLink
                  key={item.screening_id}
                  className="flex items-center justify-between rounded-[14px] border border-[var(--color-brand-input-border)] bg-white px-4 py-3 transition hover:border-[var(--color-brand-primary)] hover:bg-[var(--color-primary-50)]"
                  href={buildScreeningRoute(item.screening_id)}
                >
                  <div>
                    <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">{item.file_name}</p>
                    <p className="mt-1 text-sm text-[var(--color-brand-text-body)]">
                      {formatRecommendation(item.recommendation)} · Mức độ phù hợp {Math.round(item.match_score * 100)}%
                    </p>
                  </div>
                  <span className="text-xs text-[var(--color-brand-text-muted)]">{formatVietnamDateTime(item.created_at)}</span>
                </AppLink>
              ))}
            </div>
          ) : (
            <p
              id="recent-cv-screenings"
              className="mt-4 rounded-[14px] border border-dashed border-[var(--color-brand-input-border)] bg-white px-4 py-4 text-sm text-[var(--color-brand-text-muted)]"
            >
              Chưa có CV nào được tải lên cho JD này.
            </p>
          )
        ) : null}
      </div>

      <form className="mt-6 flex flex-col gap-4" onSubmit={handleSubmit}>
        <label className="flex flex-col gap-2 text-sm font-medium text-[var(--color-brand-text-primary)]">
          Tệp CV
          <input
            accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            className="rounded-[12px] border border-[var(--color-brand-input-border)] bg-white px-4 py-3 text-sm text-[var(--color-brand-text-primary)] outline-none"
            onChange={(event) => {
              setSelectedFile(event.target.files?.[0] ?? null)
              setError(null)
            }}
            type="file"
          />
        </label>
        <div className="flex flex-wrap items-center gap-3">
          <button
            className="w-fit rounded-[50px] bg-[var(--color-brand-primary)] px-5 py-3 text-sm font-semibold text-white transition duration-200 hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={isSubmitting}
            type="submit"
          >
            {isSubmitting ? "Đang sàng lọc..." : "Tải lên và sàng lọc CV"}
          </button>
          <p className="text-sm text-[var(--color-brand-text-muted)]">
            {selectedFile ? `Đã chọn: ${selectedFile.name}` : "Hỗ trợ PDF và DOCX"}
          </p>
        </div>
        {error ? <p className="rounded-[12px] bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p> : null}
        {latestScreening ? (
          <div className="rounded-[12px] bg-[var(--color-primary-50)] px-4 py-3 text-sm text-[var(--color-brand-text-primary)]">
            <p className="font-medium">Yêu cầu sàng lọc CV đã được đưa vào hàng đợi nền.</p>
            <p className="mt-1 text-[var(--color-brand-text-body)]">
              Bạn có thể mở trang chi tiết ngay bây giờ và theo dõi từ lúc đang xử lý tới khi hoàn tất.
            </p>
            <AppLink
              className="mt-3 inline-flex rounded-full bg-[var(--color-brand-primary)] px-4 py-2 text-xs font-semibold text-white transition duration-200 hover:-translate-y-0.5"
              href={buildScreeningRoute(latestScreening.screening_id)}
            >
              Mở chi tiết sàng lọc
            </AppLink>
          </div>
        ) : null}
      </form>

    </section>
  )
}

function buildScreeningRoute(screeningId: string): Route {
  return `/dashboard/cv-screenings/${screeningId}` as Route
}

function formatRecommendation(recommendation: CVScreeningHistoryItem["recommendation"]) {
  if (recommendation === "advance") {
    return "Nên mời vào vòng tiếp theo"
  }
  if (recommendation === "review") {
    return "Cần xem xét thêm"
  }
  return "Không phù hợp để đi tiếp"
}
