import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { expect, test, vi } from "vitest"

import { AppLink } from "@/components/navigation/app-link"
import { NavigationLoadingProvider } from "@/components/navigation/navigation-loading-provider"

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    onClick,
    className,
  }: {
    href: string
    children: React.ReactNode
    onClick?: React.MouseEventHandler<HTMLAnchorElement>
    className?: string
  }) => (
    <a
      href={href}
      onClick={(event) => {
        onClick?.(event)
        event.preventDefault()
      }}
      className={className}
    >
      {children}
    </a>
  ),
}))

vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard",
}))

test("shows navigation loading overlay immediately when app links are clicked", async () => {
  render(
    <NavigationLoadingProvider>
      <AppLink href="/dashboard/jd">Mở JD</AppLink>
    </NavigationLoadingProvider>,
  )

  expect(screen.queryByTestId("navigation-spinner")).not.toBeInTheDocument()

  const user = userEvent.setup()
  await user.click(screen.getByRole("link", { name: "Mở JD" }))

  expect(screen.getByRole("status")).toBeInTheDocument()
  expect(screen.getByTestId("navigation-spinner")).toBeInTheDocument()
})

test("does not show navigation loading overlay when clicking the current route", async () => {
  render(
    <NavigationLoadingProvider>
      <AppLink href="/dashboard">Tổng quan</AppLink>
    </NavigationLoadingProvider>,
  )

  const user = userEvent.setup()
  await user.click(screen.getByRole("link", { name: "Tổng quan" }))

  expect(screen.queryByRole("status")).not.toBeInTheDocument()
  expect(screen.queryByTestId("navigation-spinner")).not.toBeInTheDocument()
})
