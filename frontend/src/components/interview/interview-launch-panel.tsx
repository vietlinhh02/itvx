"use client"

import { CaretDown } from "@phosphor-icons/react"
import { useEffect, useMemo, useState } from "react"
import { useRouter } from "next/navigation"

import { ApprovedQuestionsEditor } from "@/components/interview/interview-launch-panel/approved-questions-editor"
import { CompanyKnowledgeSection } from "@/components/interview/interview-launch-panel/company-knowledge-section"
import {
  formatSchedule,
  parseQuestionLines,
  resolveApiBaseUrl,
} from "@/components/interview/interview-launch-panel/helpers"
import { ShareLinkModal } from "@/components/interview/interview-launch-panel/share-link-modal"
import { InterviewSchedulePicker } from "@/components/interview/interview-schedule-picker"
import type {
  CompanyKnowledgeDocument,
  CompanyKnowledgeDocumentListResponse,
  CompanyKnowledgeDocumentUploadResponse,
  GenerateInterviewQuestionsResponse,
  InterviewScopeConfig,
  PublishInterviewResponse,
  UpdateInterviewScheduleRequest,
} from "@/components/interview/interview-types"
import type { InterviewDraft } from "@/components/jd/cv-screening-types"
import {
  APP_TIME_ZONE,
  isoToVietnamInputValue,
  vietnamInputValueToIso,
} from "@/lib/datetime"

type PublishedInterview = {
  sessionId: string
  shareLink: string
  roomName: string
}

const INTRO_SCOPE_KEY = "__intro__"

const SCOPE_PRESETS = [
  { id: "full", label: "Đầy đủ" },
  { id: "basic", label: "Kiến thức cơ bản" },
  { id: "intro_only", label: "Chỉ giới thiệu" },
] as const

function buildDefaultScopeSelection(
  preset: InterviewScopeConfig["preset"],
  availableCompetencies: Array<{ vi: string; en: string }>,
) {
  if (!availableCompetencies.length) {
    return [INTRO_SCOPE_KEY]
  }
  if (preset === "intro_only") {
    return [INTRO_SCOPE_KEY]
  }
  if (preset === "basic") {
    return availableCompetencies.slice(0, 2).map((item) => item.en)
  }
  return availableCompetencies.map((item) => item.en)
}

function normalizeScopeSelection(
  selected: string[],
  availableCompetencies: Array<{ vi: string; en: string }>,
) {
  const allowed = new Set([INTRO_SCOPE_KEY, ...availableCompetencies.map((item) => item.en)])
  return selected.filter((item, index) => item && allowed.has(item) && selected.indexOf(item) === index)
}

export function InterviewLaunchPanel({
  screeningId,
  jdId,
  accessToken,
  backendBaseUrl,
  initialDraft = null,
  availableCompetencies = [],
  initialCompanyDocuments = [],
  defaultCollapsed = false,
}: {
  screeningId: string
  jdId: string
  accessToken: string
  backendBaseUrl: string
  initialDraft?: InterviewDraft | null
  availableCompetencies?: Array<{ vi: string; en: string }>
  initialCompanyDocuments?: CompanyKnowledgeDocument[]
  defaultCollapsed?: boolean
}) {
  const router = useRouter()
  const [manualQuestionsText, setManualQuestionsText] = useState(
    initialDraft?.manual_questions.join("\n") ?? "",
  )
  const [questionGuidance, setQuestionGuidance] = useState(initialDraft?.question_guidance ?? "")
  const [approvedQuestions, setApprovedQuestions] = useState<string[]>(initialDraft?.approved_questions ?? [])
  const [scopePreset, setScopePreset] = useState<InterviewScopeConfig["preset"]>(
    initialDraft?.interview_scope?.preset ?? "full",
  )
  const [enabledCompetencies, setEnabledCompetencies] = useState<string[]>(
    normalizeScopeSelection(
      initialDraft?.interview_scope?.enabled_competencies ??
        buildDefaultScopeSelection(initialDraft?.interview_scope?.preset ?? "full", availableCompetencies),
      availableCompetencies,
    ),
  )
  const [isGenerating, setIsGenerating] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isScheduling, setIsScheduling] = useState(false)
  const [scheduledStartAt, setScheduledStartAt] = useState("")
  const [scheduleNote, setScheduleNote] = useState("")
  const [publishedSessionId, setPublishedSessionId] = useState<string | null>(null)
  const [publishedInterview, setPublishedInterview] = useState<PublishedInterview | null>(null)
  const [companyDocuments, setCompanyDocuments] = useState<CompanyKnowledgeDocument[]>(
    initialCompanyDocuments,
  )
  const [isUploadingCompanyDoc, setIsUploadingCompanyDoc] = useState(false)
  const [isRefreshingCompanyDocs, setIsRefreshingCompanyDocs] = useState(false)
  const [isPanelMounted, setIsPanelMounted] = useState(!defaultCollapsed)
  const [isPanelOpen, setIsPanelOpen] = useState(!defaultCollapsed)
  const [error, setError] = useState<string | null>(null)

  const manualQuestions = useMemo(() => parseQuestionLines(manualQuestionsText), [manualQuestionsText])
  const apiBaseUrl = useMemo(() => resolveApiBaseUrl(backendBaseUrl), [backendBaseUrl])
  const competencyOptions = useMemo(
    () => [
      { key: INTRO_SCOPE_KEY, label: "Giới thiệu bản thân" },
      ...availableCompetencies.map((item) => ({
        key: item.en,
        label: item.vi || item.en,
      })),
    ],
    [availableCompetencies],
  )
  const preparationSummaryItems = useMemo(() => {
    return [
      approvedQuestions.length
        ? `${approvedQuestions.length} câu hỏi đã duyệt`
        : "Chưa có câu hỏi đã duyệt",
      manualQuestions.length
        ? `${manualQuestions.length} câu hỏi thủ công`
        : "Chưa có câu hỏi thủ công",
      companyDocuments.length
        ? `${companyDocuments.length} tài liệu tham chiếu`
        : "Chưa có tài liệu tham chiếu",
      `${enabledCompetencies.length} scope đánh giá`,
    ]
  }, [approvedQuestions.length, manualQuestions.length, companyDocuments.length, enabledCompetencies.length])

  useEffect(() => {
    const nextOpen = !defaultCollapsed
    setIsPanelMounted(nextOpen)
    setIsPanelOpen(nextOpen)
  }, [defaultCollapsed])

  useEffect(() => {
    const nextPreset = initialDraft?.interview_scope?.preset ?? "full"
    setScopePreset(nextPreset)
    setEnabledCompetencies(
      normalizeScopeSelection(
        initialDraft?.interview_scope?.enabled_competencies ??
          buildDefaultScopeSelection(nextPreset, availableCompetencies),
        availableCompetencies,
      ),
    )
  }, [availableCompetencies, initialDraft])

  useEffect(() => {
    if (isPanelOpen || !isPanelMounted) {
      return
    }

    const timeoutId = window.setTimeout(() => {
      setIsPanelMounted(false)
    }, 300)

    return () => window.clearTimeout(timeoutId)
  }, [isPanelMounted, isPanelOpen])

  async function handleGenerate() {
    if (!enabledCompetencies.length) {
      setError("Hãy chọn ít nhất một scope đánh giá trước khi tạo câu hỏi.")
      return
    }

    setIsGenerating(true)
    setError(null)
    try {
      const response = await fetch(`${apiBaseUrl}/interviews/generate-questions`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          screening_id: screeningId,
          manual_questions: manualQuestions,
          question_guidance: questionGuidance.trim() || null,
          interview_scope: {
            preset: scopePreset,
            enabled_competencies: enabledCompetencies,
          } satisfies InterviewScopeConfig,
        }),
      })

      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as { detail?: string } | null
        setError(payload?.detail ?? "Không thể tạo bộ câu hỏi phỏng vấn.")
        return
      }

      const payload = (await response.json()) as GenerateInterviewQuestionsResponse
      setManualQuestionsText(payload.manual_questions.join("\n"))
      setQuestionGuidance(payload.question_guidance ?? "")
      setApprovedQuestions(payload.generated_questions.map((item) => item.question_text.trim()).filter(Boolean))
    } catch {
      setError("Không thể kết nối tới backend. Hãy kiểm tra URL API rồi thử lại.")
    } finally {
      setIsGenerating(false)
    }
  }

  async function handleScheduleUpdate(sessionId: string) {
    setIsScheduling(true)
    setError(null)
    try {
      const response = await fetch(`${apiBaseUrl}/interviews/sessions/${sessionId}/schedule`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          scheduled_start_at: scheduledStartAt ? vietnamInputValueToIso(scheduledStartAt) : null,
          schedule_timezone: APP_TIME_ZONE,
          schedule_note: scheduleNote.trim() || null,
        } satisfies UpdateInterviewScheduleRequest),
      })

      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as { detail?: string } | null
        setError(payload?.detail ?? "Không thể cập nhật lịch họp.")
        return
      }
      router.refresh()
    } catch {
      setError("Không thể kết nối tới backend. Hãy kiểm tra URL API rồi thử lại.")
    } finally {
      setIsScheduling(false)
    }
  }

  async function handlePublish() {
    if (!approvedQuestions.length) {
      setError("Hãy tạo hoặc thêm ít nhất một câu hỏi đã duyệt trước khi bắt đầu buổi họp.")
      return
    }
    if (!enabledCompetencies.length) {
      setError("Hãy chọn ít nhất một scope đánh giá trước khi bắt đầu buổi phỏng vấn.")
      return
    }

    setIsSubmitting(true)
    setError(null)
    try {
      const response = await fetch(`${apiBaseUrl}/interviews/publish`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          screening_id: screeningId,
          approved_questions: approvedQuestions,
          manual_questions: manualQuestions,
          question_guidance: questionGuidance.trim() || null,
          interview_scope: {
            preset: scopePreset,
            enabled_competencies: enabledCompetencies,
          } satisfies InterviewScopeConfig,
        }),
      })

      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as { detail?: string } | null
        setError(payload?.detail ?? "Không thể khởi tạo phiên phỏng vấn.")
        return
      }

      const payload = (await response.json()) as PublishInterviewResponse
      const nextScheduledStartAt = payload.schedule.scheduled_start_at
        ? isoToVietnamInputValue(payload.schedule.scheduled_start_at)
        : scheduledStartAt
      const nextScheduleNote = payload.schedule.schedule_note ?? scheduleNote
      setPublishedSessionId(payload.session_id)
      setPublishedInterview({
        sessionId: payload.session_id,
        shareLink: payload.share_link,
        roomName: payload.room_name,
      })
      if (payload.schedule.scheduled_start_at) {
        setScheduledStartAt(nextScheduledStartAt)
      }
      if (payload.schedule.schedule_note) {
        setScheduleNote(nextScheduleNote)
      }
      if (scheduledStartAt || scheduleNote.trim()) {
        const scheduleResponse = await fetch(`${apiBaseUrl}/interviews/sessions/${payload.session_id}/schedule`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${accessToken}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            scheduled_start_at: nextScheduledStartAt ? vietnamInputValueToIso(nextScheduledStartAt) : null,
            schedule_timezone: APP_TIME_ZONE,
            schedule_note: nextScheduleNote.trim() || null,
          } satisfies UpdateInterviewScheduleRequest),
        })
        if (!scheduleResponse.ok) {
          const errorPayload = (await scheduleResponse.json().catch(() => null)) as { detail?: string } | null
          setError(errorPayload?.detail ?? "Không thể cập nhật lịch họp.")
          return
        }
      }
      router.refresh()
    } catch {
      setError("Không thể kết nối tới backend. Hãy kiểm tra URL API rồi thử lại.")
    } finally {
      setIsSubmitting(false)
    }
  }

  async function refreshCompanyDocuments() {
    setIsRefreshingCompanyDocs(true)
    try {
      const response = await fetch(`${apiBaseUrl}/jd/${jdId}/company-documents`, {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      })
      if (!response.ok) {
        return
      }
      const payload = (await response.json()) as CompanyKnowledgeDocumentListResponse
      setCompanyDocuments(payload.items)
    } finally {
      setIsRefreshingCompanyDocs(false)
    }
  }

  async function handleCompanyDocumentUpload(file: File | null) {
    if (!file) {
      return
    }

    setIsUploadingCompanyDoc(true)
    setError(null)
    try {
      const formData = new FormData()
      formData.append("file", file)
      const response = await fetch(`${apiBaseUrl}/jd/${jdId}/company-documents`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
        body: formData,
      })
      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as { detail?: string } | null
        setError(payload?.detail ?? "Không thể tải tài liệu công ty lên.")
        return
      }
      const payload = (await response.json()) as CompanyKnowledgeDocumentUploadResponse
      setCompanyDocuments((current) => [payload.document, ...current])
      await refreshCompanyDocuments()
    } catch {
      setError("Không thể kết nối tới backend. Hãy kiểm tra URL API rồi thử lại.")
    } finally {
      setIsUploadingCompanyDoc(false)
    }
  }

  async function handleDeleteCompanyDocument(documentId: string) {
    setError(null)
    try {
      const response = await fetch(`${apiBaseUrl}/jd/${jdId}/company-documents/${documentId}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      })
      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as { detail?: string } | null
        setError(payload?.detail ?? "Không thể xóa tài liệu công ty.")
        return
      }
      setCompanyDocuments((current) => current.filter((item) => item.document_id !== documentId))
    } catch {
      setError("Không thể kết nối tới backend. Hãy kiểm tra URL API rồi thử lại.")
    }
  }

  function handleQuestionChange(index: number, value: string) {
    setApprovedQuestions((current) =>
      current.map((question, questionIndex) => (questionIndex === index ? value : question)),
    )
  }

  function handleRemoveQuestion(index: number) {
    setApprovedQuestions((current) => current.filter((_, questionIndex) => questionIndex !== index))
  }

  function handlePanelToggle() {
    if (isPanelOpen) {
      setIsPanelOpen(false)
      return
    }

    setIsPanelMounted(true)
    window.requestAnimationFrame(() => {
      setIsPanelOpen(true)
    })
  }

  function handleScopePresetChange(nextPreset: InterviewScopeConfig["preset"]) {
    setScopePreset(nextPreset)
    setEnabledCompetencies(buildDefaultScopeSelection(nextPreset, availableCompetencies))
  }

  function handleCompetencyToggle(key: string) {
    setEnabledCompetencies((current) =>
      current.includes(key) ? current.filter((item) => item !== key) : [...current, key],
    )
  }

  return (
    <>
      <section className="rounded-[24px] bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
        <button
          aria-expanded={isPanelOpen}
          className="flex w-full items-start justify-between gap-4 rounded-[20px] border border-[var(--color-brand-input-border)] bg-[var(--color-primary-50)]/45 px-5 py-4 text-left"
          onClick={handlePanelToggle}
          type="button"
        >
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-[var(--color-brand-text-muted)]">Giai đoạn 4 · Phỏng vấn</p>
            <h2 className="mt-2 text-2xl font-semibold text-[var(--color-brand-text-primary)]">
              Chuẩn bị câu hỏi trước khi bắt đầu buổi phỏng vấn
            </h2>
            <p className="mt-2 text-sm leading-6 text-[var(--color-brand-text-body)]">
              {isPanelOpen
                ? "HR có thể thêm câu hỏi thủ công, định hướng cho AI, rà soát danh sách câu hỏi đã tạo rồi tạo liên kết tham gia."
                : "Phần chuẩn bị đã được thu gọn. Mở lại nếu cần rà soát câu hỏi, lịch hẹn, tài liệu tham chiếu hoặc liên kết tham gia."}
            </p>
            {!isPanelOpen ? (
              <div className="mt-3 flex flex-wrap gap-2">
                {preparationSummaryItems.map((item) => (
                  <span
                    className="rounded-full border border-[var(--color-brand-input-border)] bg-white/85 px-3 py-1 text-xs font-medium text-[var(--color-brand-text-muted)]"
                    key={item}
                  >
                    {item}
                  </span>
                ))}
              </div>
            ) : null}
          </div>
          <span className="inline-flex shrink-0 items-center gap-2 rounded-full border border-[var(--color-brand-input-border)] bg-white px-3 py-1.5 text-xs font-semibold text-[var(--color-brand-primary)]">
            <CaretDown
              className={`transition-transform duration-300 ${isPanelOpen ? "rotate-180" : "rotate-0"}`}
              size={14}
              weight="bold"
            />
            {isPanelOpen ? "Thu gọn" : "Mở lại"}
          </span>
        </button>

        {isPanelMounted ? (
          <div
            aria-hidden={!isPanelOpen}
            className={`grid transition-all duration-300 ease-in-out ${
              isPanelOpen ? "mt-5 grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0"
            }`}
          >
            <div className="overflow-hidden">
              <div className="space-y-5">
            <CompanyKnowledgeSection
              companyDocuments={companyDocuments}
              isRefreshingCompanyDocs={isRefreshingCompanyDocs}
              isUploadingCompanyDoc={isUploadingCompanyDoc}
              onRefresh={() => void refreshCompanyDocuments()}
              onUpload={(file) => {
                void handleCompanyDocumentUpload(file)
              }}
              onDelete={(documentId) => {
                void handleDeleteCompanyDocument(documentId)
              }}
            />

            <section className="rounded-[20px] border border-[var(--color-brand-input-border)] bg-[var(--color-primary-50)]/35 p-5">
              <p className="text-sm font-medium text-[var(--color-brand-text-muted)]">Scope đánh giá của AI</p>
              <p className="mt-2 text-sm leading-6 text-[var(--color-brand-text-body)]">
                AI chỉ hỏi, chấm và quyết định kết thúc dựa trên các scope HR bật ở đây. Scope không chọn sẽ bị bỏ qua hoàn toàn.
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                {SCOPE_PRESETS.map((preset) => (
                  <button
                    key={preset.id}
                    type="button"
                    onClick={() => handleScopePresetChange(preset.id)}
                    className={`rounded-full border px-4 py-2 text-sm font-semibold ${
                      scopePreset === preset.id
                        ? "border-[var(--color-brand-primary)] bg-[var(--color-brand-primary)] text-white"
                        : "border-[var(--color-brand-input-border)] bg-white text-[var(--color-brand-primary)]"
                    }`}
                  >
                    {preset.label}
                  </button>
                ))}
              </div>
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                {competencyOptions.map((option) => (
                  <label
                    key={option.key}
                    className="flex items-center gap-3 rounded-[16px] border border-[var(--color-brand-input-border)] bg-white px-4 py-3 text-sm text-[var(--color-brand-text-primary)]"
                  >
                    <input
                      type="checkbox"
                      className="h-4 w-4 accent-[var(--color-brand-primary)]"
                      checked={enabledCompetencies.includes(option.key)}
                      onChange={() => handleCompetencyToggle(option.key)}
                    />
                    <span>{option.label}</span>
                  </label>
                ))}
              </div>
            </section>

            <label className="mt-5 block text-sm font-medium text-[var(--color-brand-text-primary)]" htmlFor="manual-questions">
              Câu hỏi thủ công
            </label>
            <textarea
              id="manual-questions"
              className="mt-2 min-h-32 w-full rounded-[16px] border border-[var(--color-brand-input-border)] p-4 text-sm outline-none"
              onChange={(event) => setManualQuestionsText(event.target.value)}
              placeholder={"Mỗi dòng là một câu hỏi.\nVí dụ: Bạn tự hào nhất về dự án nào gần đây?"}
              value={manualQuestionsText}
            />

            <label className="mt-5 block text-sm font-medium text-[var(--color-brand-text-primary)]" htmlFor="question-guidance">
              Định hướng cho AI
            </label>
            <textarea
              id="question-guidance"
              className="mt-2 min-h-28 w-full rounded-[16px] border border-[var(--color-brand-input-border)] p-4 text-sm outline-none"
              onChange={(event) => setQuestionGuidance(event.target.value)}
              placeholder="Ví dụ: tập trung vào khả năng làm chủ backend, thiết kế API có thể mở rộng và cách ứng viên xử lý tình huống chưa rõ ràng."
              value={questionGuidance}
            />

            <InterviewSchedulePicker
              helperText="Chọn giờ phỏng vấn theo múi giờ Việt Nam (ICT, UTC+7). Liên kết tham gia vẫn hoạt động nếu ứng viên vào sớm hơn thời gian đã chọn."
              label="Thời gian buổi họp"
              noteLabel="Ghi chú lịch hẹn"
              noteValue={scheduleNote}
              onChange={setScheduledStartAt}
              onNoteChange={setScheduleNote}
              summaryText={formatSchedule(scheduledStartAt || null)}
              value={scheduledStartAt}
            />

            <div className="mt-4 flex flex-wrap items-center gap-3">
              <button
                className="rounded-full border border-[var(--color-brand-input-border)] px-5 py-3 text-sm font-semibold text-[var(--color-brand-primary)] disabled:cursor-not-allowed disabled:opacity-60"
                disabled={isGenerating}
                onClick={() => void handleGenerate()}
                type="button"
              >
                {isGenerating ? "Đang tạo..." : "Tạo câu hỏi"}
              </button>
              <p className="text-sm text-[var(--color-brand-text-muted)]">
                {manualQuestions.length
                  ? `Đã có ${manualQuestions.length} câu hỏi thủ công sẵn sàng.`
                  : "Bạn vẫn có thể sinh câu hỏi từ hướng dẫn AI ngay cả khi chưa nhập câu hỏi thủ công."}
              </p>
            </div>

            <ApprovedQuestionsEditor
              approvedQuestions={approvedQuestions}
              isSubmitting={isSubmitting}
              isScheduling={isScheduling}
              publishedSessionId={publishedSessionId}
              error={error}
              onQuestionChange={handleQuestionChange}
              onRemoveQuestion={handleRemoveQuestion}
              onPublish={() => void handlePublish()}
              onScheduleUpdate={(sessionId) => {
                void handleScheduleUpdate(sessionId)
              }}
            />
              </div>
            </div>
          </div>
        ) : null}
      </section>

      {publishedInterview ? (
        <ShareLinkModal
          onClose={() => setPublishedInterview(null)}
          roomName={publishedInterview.roomName}
          scheduledStartAt={scheduledStartAt || null}
          sessionId={publishedInterview.sessionId}
          shareLink={publishedInterview.shareLink}
        />
      ) : null}
    </>
  )
}
