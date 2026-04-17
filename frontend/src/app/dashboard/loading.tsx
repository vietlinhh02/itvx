import { LoadingScreen } from "@/components/navigation/loading-screen"

export default function DashboardLoading() {
  return (
    <div className="flex w-full flex-col gap-6 py-6">
      <LoadingScreen fullscreen={false} />
    </div>
  )
}
