import { notFound, redirect } from "next/navigation"

import { CVScreeningHistory } from "@/components/jd/cv-screening-history"
import { CVScreeningPanel } from "@/components/jd/cv-screening-panel"
import {
  type CVScreeningHistoryResponse,
} from "@/components/jd/cv-screening-types"
import { JDAnalysisContent, type JDAnalysisResponse } from "@/components/jd/jd-upload-panel"
import { auth } from "@/lib/auth"

const backendBaseUrl = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL

type JDDetailPageProps = {
  params: Promise<{ id: string }>
}

export default async function JDDetailPage({ params }: JDDetailPageProps) {
  const session = await auth()

  if (!session?.accessToken || !backendBaseUrl) {
    redirect("/login")
  }

  const { id } = await params
  const response = await fetch(`${backendBaseUrl}/api/v1/jd/${id}`, {
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
    redirect("/login")
  }

  const result = (await response.json()) as JDAnalysisResponse

  const screeningsResponse = await fetch(`${backendBaseUrl}/api/v1/cv/jd/${id}/screenings`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${session.accessToken}`,
    },
    cache: "no-store",
  })
  const screeningHistory = screeningsResponse.ok
    ? ((await screeningsResponse.json()) as CVScreeningHistoryResponse)
    : { items: [] }

  return (
    <main className="flex w-full flex-col gap-6 py-6">
      <JDAnalysisContent result={result} />
      <CVScreeningPanel accessToken={session.accessToken} backendBaseUrl={backendBaseUrl} jd={result} />
      <CVScreeningHistory title="Previous screenings" items={screeningHistory.items} />
    </main>
  )
}
