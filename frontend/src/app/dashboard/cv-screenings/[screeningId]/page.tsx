import { getServerSession } from "next-auth"
import type { Route } from "next"
import { notFound, redirect } from "next/navigation"

import type {
  CompanyKnowledgeDocumentListResponse,
  InterviewFeedbackPolicyCollectionResponse,
  InterviewFeedbackResponse,
  InterviewFeedbackSummaryResponse,
  InterviewSessionDetailResponse,
  InterviewSessionReviewResponse,
} from "@/components/interview/interview-types"
import { CVScreeningDetail } from "@/components/jd/cv-screening-detail"
import type {
  CVScreeningCompletedResponse,
  CVScreeningHistoryResponse,
  CVScreeningResponse,
} from "@/components/jd/cv-screening-types"
import { AppLink } from "@/components/navigation/app-link"
import { authOptions } from "@/lib/auth-options"
import { formatVietnamDateTime } from "@/lib/datetime"

const backendBaseUrl = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL

type CVScreeningDetailPageProps = {
  params: Promise<{ screeningId: string }>
}

export default async function CVScreeningDetailPage({ params }: CVScreeningDetailPageProps) {
  const session = await getServerSession(authOptions)

  if (!session?.accessToken || !backendBaseUrl) {
    redirect("/login")
  }

  const { screeningId } = await params
  const response = await fetch(`${backendBaseUrl}/api/v1/cv/screenings/${screeningId}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${session.accessToken}`,
    },
    cache: "no-store",
  })

  if (response.status === 404) {
    notFound()
  }

  if (!response.ok) {
    return (
      <main className="flex w-full flex-col gap-6 py-6">
        <section className="rounded-[24px] bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
          <p className="text-sm font-medium text-red-700">
            Không thể tải kết quả sàng lọc CV. Vui lòng thử lại.
          </p>
        </section>
      </main>
    )
  }

  const screening = (await response.json()) as CVScreeningResponse

  if (screening.status !== "completed") {
    return (
      <main className="flex w-full flex-col gap-6 py-6">
        <section className="rounded-[24px] bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-sm font-medium text-[var(--color-brand-text-muted)]">Giai đoạn 2 - Sàng lọc CV</p>
              <h1 className="mt-2 text-3xl font-semibold text-[var(--color-brand-text-primary)]">
                {screening.file_name}
              </h1>
              <p className="mt-2 text-sm text-[var(--color-brand-text-body)]">
                {screening.status === "failed"
                  ? screening.error_message ?? "Lượt sàng lọc này đã thất bại trước khi tạo được kết quả."
                  : "Lượt sàng lọc này vẫn đang được xử lý nền. Hãy làm mới trang sau ít phút để xem kết quả hoàn tất."}
              </p>
            </div>
            <AppLink
              className="rounded-full bg-[var(--color-brand-primary)] px-4 py-3 text-sm font-semibold text-white"
              href={buildJDRoute(screening.jd_id)}
            >
              Quay lại chi tiết mô tả công việc
            </AppLink>
          </div>
          <div className="mt-6 rounded-[16px] border border-[var(--color-brand-input-border)] px-4 py-4">
            <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">
              Trạng thái: {screening.status}
            </p>
            <p className="mt-1 text-sm text-[var(--color-brand-text-body)]">
              Tạo lúc {formatVietnamDateTime(screening.created_at)}
            </p>
          </div>
        </section>
      </main>
    )
  }

  const completedScreening = screening as CVScreeningCompletedResponse
  const historyResponse = await fetch(`${backendBaseUrl}/api/v1/cv/jd/${completedScreening.jd_id}/screenings`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${session.accessToken}`,
    },
    cache: "no-store",
  })
  const history = historyResponse.ok
    ? ((await historyResponse.json()) as CVScreeningHistoryResponse)
    : { items: [] }

  const companyDocumentsResponse = await fetch(
    `${backendBaseUrl}/api/v1/jd/${completedScreening.jd_id}/company-documents`,
    {
      headers: {
        Authorization: `Bearer ${session.accessToken}`,
      },
      cache: "no-store",
    },
  )
  const companyDocuments = companyDocumentsResponse.ok
    ? ((await companyDocumentsResponse.json()) as CompanyKnowledgeDocumentListResponse).items
    : []

  const interviewSessionId = completedScreening.interview_session_id ?? null
  const [interviewDetail, interviewReview, interviewFeedback, feedbackSummary, feedbackPolicy] = interviewSessionId
    ? await Promise.all([
        fetch(`${backendBaseUrl}/api/v1/interviews/sessions/${interviewSessionId}`, {
          headers: {
            Authorization: `Bearer ${session.accessToken}`,
          },
          cache: "no-store",
        }).then(async (response) =>
          response.ok ? ((await response.json()) as InterviewSessionDetailResponse) : null,
        ),
        fetch(`${backendBaseUrl}/api/v1/interviews/sessions/${interviewSessionId}/review`, {
          headers: {
            Authorization: `Bearer ${session.accessToken}`,
          },
          cache: "no-store",
        }).then(async (response) =>
          response.ok ? ((await response.json()) as InterviewSessionReviewResponse) : null,
        ),
        fetch(`${backendBaseUrl}/api/v1/interviews/sessions/${interviewSessionId}/feedback`, {
          headers: {
            Authorization: `Bearer ${session.accessToken}`,
          },
          cache: "no-store",
        }).then(async (response) =>
          response.ok ? ((await response.json()) as InterviewFeedbackResponse | null) : null,
        ),
        fetch(`${backendBaseUrl}/api/v1/interviews/jd/${completedScreening.jd_id}/feedback-summary`, {
          headers: {
            Authorization: `Bearer ${session.accessToken}`,
          },
          cache: "no-store",
        }).then(async (response) =>
          response.ok ? ((await response.json()) as InterviewFeedbackSummaryResponse) : null,
        ),
        fetch(`${backendBaseUrl}/api/v1/interviews/jd/${completedScreening.jd_id}/feedback-policy`, {
          headers: {
            Authorization: `Bearer ${session.accessToken}`,
          },
          cache: "no-store",
        }).then(async (response) =>
          response.ok ? ((await response.json()) as InterviewFeedbackPolicyCollectionResponse) : null,
        ),
      ])
    : [null, null, null, null, null]

  return (
    <CVScreeningDetail
      screening={completedScreening}
      historyItems={history.items}
      accessToken={session.accessToken}
      backendBaseUrl={backendBaseUrl}
      interviewDetail={interviewDetail}
      interviewReview={interviewReview}
      interviewFeedback={interviewFeedback}
      feedbackSummary={feedbackSummary}
      feedbackPolicy={feedbackPolicy}
      companyDocuments={companyDocuments}
    />
  )
}

function buildJDRoute(jdId: string): Route {
  return `/dashboard/jd/${jdId}` as Route
}
