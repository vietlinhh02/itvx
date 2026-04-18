import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { expect, test, vi } from "vitest"

const logoutSpy = vi.fn().mockResolvedValue(undefined)

vi.mock("@/components/login/login-logo", () => ({
  LoginLogo: () => <div>InterviewX</div>,
}))

vi.mock("@/components/navigation/app-link", () => ({
  AppLink: ({ href, children, className }: { href: string; children: React.ReactNode; className?: string }) => (
    <a href={href} className={className}>
      {children}
    </a>
  ),
}))

vi.mock("@/stores/authStore", () => ({
  useAuthStore: (selector: (state: { isLoading: boolean; logout: typeof logoutSpy }) => unknown) =>
    selector({
      isLoading: false,
      logout: logoutSpy,
    }),
}))

import { DashboardHeader } from "@/components/dashboard/dashboard-header"

test("renders a logout button in the dashboard header and triggers logout", async () => {
  render(<DashboardHeader />)

  const user = userEvent.setup()
  const logoutButton = screen.getByRole("button", { name: "Đăng xuất" })

  expect(logoutButton).toBeInTheDocument()

  await user.click(logoutButton)

  expect(logoutSpy).toHaveBeenCalledTimes(1)
})
