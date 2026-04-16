import { getServerSession } from "next-auth"
import { notFound, redirect } from "next/navigation"

import { CVScreeningPanel } from "@/components/jd/cv-screening-panel"
import { JDAnalysisContent, type JDAnalysisResponse } from "@/components/jd/jd-upload-panel"
import { authOptions } from "@/lib/auth-options"

const backendBaseUrl = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL

type JDDetailPageProps = {
  params: Promise<{ id: string }>
}

export default async function JDDetailPage({ params }: JDDetailPageProps) {
  const session = await getServerSession(authOptions)

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

  return (
    <main className="flex w-full flex-col gap-6 py-6">
      <JDAnalysisContent result={result} />
      <CVScreeningPanel accessToken={session.accessToken} backendBaseUrl={backendBaseUrl} jd={result} />
    </main>
  )
}
