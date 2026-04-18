import { getServerSession } from "next-auth"
import { notFound, redirect } from "next/navigation"

import { DashboardSystemErrorState } from "@/components/dashboard/dashboard-system-error-state"
import { CVScreeningPanel } from "@/components/jd/cv-screening-panel"
import type { CVScreeningHistoryResponse } from "@/components/jd/cv-screening-types"
import { JDAnalysisContent, type JDAnalysisResponse } from "@/components/jd/jd-upload-panel"
import { authOptions } from "@/lib/auth-options"
import { fetchDashboardJson } from "@/lib/dashboard-server"

const backendBaseUrl = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL

type JDDetailPageProps = {
  params: Promise<{ id: string }>
}

export default async function JDDetailPage({ params }: JDDetailPageProps) {
  const session = await getServerSession(authOptions)

  if (!session?.accessToken) {
    redirect("/login")
  }

  if (!backendBaseUrl) {
    return (
      <DashboardSystemErrorState
        title="Không thể tải chi tiết JD"
        description="Ứng dụng chưa được cấu hình địa chỉ backend. Hãy kiểm tra API_URL hoặc NEXT_PUBLIC_API_URL."
      />
    )
  }

  const { id } = await params
  const detailResult = await fetchDashboardJson<JDAnalysisResponse>({
    accessToken: session.accessToken,
    notFoundStatuses: [404],
    resourceLabel: "JD detail",
    url: `${backendBaseUrl}/api/v1/jd/${id}`,
  })

  if (detailResult.kind === "not-found") {
    notFound()
  }

  if (detailResult.kind === "auth") {
    redirect("/login")
  }

  if (detailResult.kind === "system") {
    return (
      <DashboardSystemErrorState
        title="Không thể tải chi tiết JD"
        description="Backend đang lỗi hoặc không phản hồi khi tải chi tiết JD."
        status={detailResult.status}
      />
    )
  }

  const result = detailResult.data
  const recentScreeningsResult = await fetchDashboardJson<CVScreeningHistoryResponse>({
    accessToken: session.accessToken,
    resourceLabel: "JD screenings",
    url: `${backendBaseUrl}/api/v1/cv/jd/${id}/screenings`,
  })

  if (recentScreeningsResult.kind === "auth") {
    redirect("/login")
  }

  const recentScreenings =
    recentScreeningsResult.kind === "success" ? recentScreeningsResult.data.items.slice(0, 4) : []

  return (
    <main className="flex w-full flex-col gap-6 py-6">
      <JDAnalysisContent result={result} />
      <CVScreeningPanel
        accessToken={session.accessToken}
        backendBaseUrl={backendBaseUrl}
        jd={result}
        recentScreenings={recentScreenings}
      />
    </main>
  )
}
