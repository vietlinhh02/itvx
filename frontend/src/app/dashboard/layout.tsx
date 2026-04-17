import type { ReactNode } from "react"

import { DashboardHeader } from "@/components/dashboard/dashboard-header"
import { JobTrackerProvider } from "@/components/dashboard/job-tracker"

export default function DashboardLayout({ children }: { children: ReactNode }) {
  return (
    <JobTrackerProvider>
      <div className="flex h-screen h-[100dvh] flex-col overflow-hidden bg-[#f8f9fc]">
        <div className="shrink-0 px-6 pt-8 xl:px-10">
          <DashboardHeader />
        </div>
        <main className="flex-1 overflow-y-auto px-6 pb-8 xl:px-10 [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]">
          {children}
        </main>
      </div>
    </JobTrackerProvider>
  )
}
