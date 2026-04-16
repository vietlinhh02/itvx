import { notFound, redirect } from "next/navigation"

import { CVScreeningDetail } from "@/components/jd/cv-screening-detail"
import type {
  CVScreeningHistoryResponse,
  CVScreeningResponse,
} from "@/components/jd/cv-screening-types"
import { auth } from "@/lib/auth"

const backendBaseUrl = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL

type CVScreeningDetailPageProps = {
  params: Promise<{ screeningId: string }>
}

export default async function CVScreeningDetailPage({ params }: CVScreeningDetailPageProps) {
  const session = await auth()

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
            Could not load the CV screening result. Please try again.
          </p>
        </section>
      </main>
    )
  }

  const screening = (await response.json()) as CVScreeningResponse

  const historyResponse = await fetch(`${backendBaseUrl}/api/v1/cv/jd/${screening.jd_id}/screenings`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${session.accessToken}`,
    },
    cache: "no-store",
  })
  const history = historyResponse.ok
    ? ((await historyResponse.json()) as CVScreeningHistoryResponse)
    : { items: [] }

  return <CVScreeningDetail screening={screening} historyItems={history.items} />
}
