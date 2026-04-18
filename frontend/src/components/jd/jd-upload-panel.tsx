"use client"

import { useState } from "react"

import { useJobTracker } from "@/components/dashboard/job-tracker"
import { JDAnalysisContent } from "@/components/jd/jd-analysis-board"
import type { JDAnalysisEnqueueResponse, JDAnalysisResponse } from "@/components/jd/jd-analysis-types"
import { resolveApiBaseUrl } from "@/lib/api"

export { JDAnalysisContent } from "@/components/jd/jd-analysis-board"
export type { BackgroundJobResponse, BilingualText, HumanReadableText, JDAnalysisResponse } from "@/components/jd/jd-analysis-types"

type JDUploadPanelProps = {
  accessToken: string
  backendBaseUrl: string
}

export function JDUploadPanel({ accessToken, backendBaseUrl }: JDUploadPanelProps) {
  const { registerJob } = useJobTracker()
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [result, setResult] = useState<JDAnalysisResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const apiBaseUrl = resolveApiBaseUrl(backendBaseUrl)

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (!selectedFile) {
      setError("Vui lòng chọn tệp PDF hoặc DOCX trước khi tải lên.")
      return
    }

    setIsUploading(true)
    setError(null)

    const formData = new FormData()
    formData.append("file", selectedFile)

    try {
      const response = await fetch(`${apiBaseUrl}/jd/analyze`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
        body: formData,
      })

      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as { detail?: string } | null
        setResult(null)
        setError(payload?.detail ?? "Tải JD thất bại. Vui lòng thử lại.")
        return
      }

      const payload = (await response.json()) as JDAnalysisEnqueueResponse
      setResult(null)
      registerJob({
        jobId: payload.job_id,
        resourceId: payload.jd_id,
        resourceType: "jd",
        title: payload.file_name,
        accessToken,
        backendBaseUrl,
      })
    } catch {
      setResult(null)
      setError("Không thể kết nối tới backend. Hãy kiểm tra URL API rồi thử lại.")
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <section className="rounded-[24px] bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)] motion-safe:animate-[panel-enter_220ms_ease-out]">
        <div className="flex flex-col gap-2">
          <p className="text-sm font-medium text-[var(--color-brand-text-muted)]">
            Giai đoạn 1 - Phân tích mô tả công việc
          </p>
          <h1 className="text-3xl font-semibold text-[var(--color-brand-text-primary)]">
            Tải mô tả công việc lên
          </h1>
          <p className="max-w-2xl text-sm leading-6 text-[var(--color-brand-text-body)]">
            Gửi tệp PDF hoặc DOCX lên backend, lưu tài liệu gốc và xem bản phân tích tuyển dụng theo ba cột.
          </p>
        </div>

        <form className="mt-6 flex flex-col gap-4" onSubmit={handleSubmit}>
          <label className="flex flex-col gap-2 text-sm font-medium text-[var(--color-brand-text-primary)]">
            Tệp mô tả công việc
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
              className="rounded-[50px] bg-[var(--color-brand-primary)] px-5 py-3 text-sm font-semibold text-white transition duration-200 hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-60"
              disabled={isUploading}
              type="submit"
            >
              {isUploading ? "Đang phân tích..." : "Tải lên và phân tích"}
            </button>
            <p className="text-sm text-[var(--color-brand-text-muted)]">
              {selectedFile ? `Đã chọn: ${selectedFile.name}` : "Hỗ trợ PDF và DOCX"}
            </p>
          </div>

          {error ? (
            <p className="rounded-[12px] bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>
          ) : null}
        </form>
      </section>

      {result ? <JDAnalysisContent result={result} /> : null}
    </div>
  )
}
