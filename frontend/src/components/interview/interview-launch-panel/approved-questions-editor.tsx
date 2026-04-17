export function ApprovedQuestionsEditor({
  approvedQuestions,
  isSubmitting,
  isScheduling,
  publishedSessionId,
  error,
  onQuestionChange,
  onRemoveQuestion,
  onPublish,
  onScheduleUpdate,
}: {
  approvedQuestions: string[]
  isSubmitting: boolean
  isScheduling: boolean
  publishedSessionId: string | null
  error: string | null
  onQuestionChange: (index: number, value: string) => void
  onRemoveQuestion: (index: number) => void
  onPublish: () => void
  onScheduleUpdate: (sessionId: string) => void
}) {
  return (
    <div className="mt-6 rounded-[20px] border border-[var(--color-brand-input-border)] p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-[var(--color-brand-text-muted)]">Câu hỏi đã duyệt</p>
          <h3 className="mt-2 text-xl font-semibold text-[var(--color-brand-text-primary)]">
            Rà soát trước khi bắt đầu buổi họp
          </h3>
        </div>
        <span className="rounded-full bg-[var(--color-primary-50)] px-3 py-1 text-xs font-semibold text-[var(--color-brand-primary)]">
          {approvedQuestions.length} câu hỏi
        </span>
      </div>

      <div className="mt-4 divide-y divide-[var(--color-brand-input-border)] border-y border-[var(--color-brand-input-border)]">
        {approvedQuestions.length ? (
          approvedQuestions.map((question, index) => (
            <div key={`${index}-${question}`} className="py-3">
              <div className="flex items-center justify-between gap-2">
                <p className="text-xs font-semibold text-[var(--color-brand-text-muted)]">Câu hỏi {index + 1}</p>
                <button
                  className="text-sm font-medium text-red-700"
                  onClick={() => onRemoveQuestion(index)}
                  type="button"
                >
                  Xóa
                </button>
              </div>
              <textarea
                className="mt-1 min-h-20 w-full border-0 bg-transparent px-0 py-0 text-sm outline-none"
                onChange={(event) => onQuestionChange(index, event.target.value)}
                value={question}
              />
            </div>
          ))
        ) : (
          <div className="py-3 text-sm text-[var(--color-brand-text-muted)]">
            Hãy tạo câu hỏi trước, sau đó chỉnh danh sách cuối tại đây trước khi bắt đầu buổi họp.
          </div>
        )}
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-3">
        <button
          className="rounded-full bg-[var(--color-brand-primary)] px-5 py-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
          disabled={isSubmitting || !approvedQuestions.some((question) => question.trim())}
          onClick={onPublish}
          type="button"
        >
          {isSubmitting ? "Đang khởi tạo..." : "Bắt đầu buổi phỏng vấn"}
        </button>
        {publishedSessionId ? (
          <button
            className="rounded-full border border-[var(--color-brand-input-border)] px-5 py-3 text-sm font-semibold text-[var(--color-brand-primary)] disabled:cursor-not-allowed disabled:opacity-60"
            disabled={isScheduling}
            onClick={() => onScheduleUpdate(publishedSessionId)}
            type="button"
          >
            {isScheduling ? "Đang lưu lịch..." : "Cập nhật lịch phỏng vấn"}
          </button>
        ) : null}
        {error ? <p className="text-sm text-red-700">{error}</p> : null}
      </div>
    </div>
  )
}
