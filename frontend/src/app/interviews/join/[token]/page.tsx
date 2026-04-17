import { CandidateJoin } from "@/components/interview/candidate-join"

const backendBaseUrl = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? ""

export default async function CandidateJoinPage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params
  return (
    <main className="flex min-h-screen w-full flex-col gap-6">
      {!backendBaseUrl ? (
        <section className="rounded-[24px] bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
          <p className="text-sm text-red-700">Interview service is not configured.</p>
        </section>
      ) : (
        <CandidateJoin token={token} backendBaseUrl={backendBaseUrl} />
      )}
    </main>
  )
}
