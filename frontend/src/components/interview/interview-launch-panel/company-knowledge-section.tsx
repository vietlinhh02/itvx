import { formatVietnamDateTime } from "@/lib/datetime"

import type { CompanyKnowledgeDocument } from "@/components/interview/interview-types"

export function CompanyKnowledgeSection({
  companyDocuments,
  isRefreshingCompanyDocs,
  isUploadingCompanyDoc,
  onRefresh,
  onUpload,
  onDelete,
}: {
  companyDocuments: CompanyKnowledgeDocument[]
  isRefreshingCompanyDocs: boolean
  isUploadingCompanyDoc: boolean
  onRefresh: () => void
  onUpload: (file: File | null) => void
  onDelete: (documentId: string) => void
}) {
  return (
    <div className="mt-5 rounded-[20px] border border-[var(--color-brand-input-border)] p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-[var(--color-brand-text-muted)]">Tri thức doanh nghiệp</p>
          <h3 className="mt-2 text-xl font-semibold text-[var(--color-brand-text-primary)]">
            Tải tài liệu tham chiếu cho AI
          </h3>
          <p className="mt-2 text-sm leading-6 text-[var(--color-brand-text-body)]">
            AI phỏng vấn có thể dùng các tài liệu này để trả lời câu hỏi của ứng viên về công ty kèm trích dẫn có căn cứ.
          </p>
        </div>
        <button
          className="rounded-full border border-[var(--color-brand-input-border)] px-4 py-2 text-sm font-semibold text-[var(--color-brand-primary)] disabled:opacity-60"
          disabled={isRefreshingCompanyDocs}
          onClick={onRefresh}
          type="button"
        >
          {isRefreshingCompanyDocs ? "Đang làm mới..." : "Làm mới"}
        </button>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <label className="rounded-full bg-[var(--color-brand-primary)] px-5 py-3 text-sm font-semibold text-white">
          <span>{isUploadingCompanyDoc ? "Đang tải lên..." : "Tải tài liệu lên"}</span>
          <input
            accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            className="sr-only"
            disabled={isUploadingCompanyDoc}
            onChange={(event) => {
              const file = event.target.files?.[0] ?? null
              onUpload(file)
              event.currentTarget.value = ""
            }}
            type="file"
          />
        </label>
        <p className="text-sm text-[var(--color-brand-text-muted)]">
          Chỉ hỗ trợ PDF và DOCX. Các tệp này được dùng chung cho mọi phiên phỏng vấn của JD này.
        </p>
      </div>

      <div className="mt-4 divide-y divide-[var(--color-brand-input-border)] border-y border-[var(--color-brand-input-border)]">
        {companyDocuments.length ? (
          companyDocuments.map((document) => (
            <div key={document.document_id} className="flex flex-wrap items-center justify-between gap-3 py-3">
              <div>
                <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">{document.file_name}</p>
                <p className="mt-1 text-xs text-[var(--color-brand-text-muted)]">
                  Trạng thái: {document.status} · Đoạn cắt: {document.chunk_count} · Thêm lúc{" "}
                  {formatVietnamDateTime(document.created_at)}
                </p>
                {document.error_message ? (
                  <p className="mt-1 text-xs text-red-700">{document.error_message}</p>
                ) : null}
              </div>
              <button
                className="text-sm font-medium text-red-700"
                onClick={() => onDelete(document.document_id)}
                type="button"
              >
                Xóa
              </button>
            </div>
          ))
        ) : (
          <div className="py-3 text-sm text-[var(--color-brand-text-muted)]">Chưa có tài liệu công ty nào được tải lên.</div>
        )}
      </div>
    </div>
  )
}
