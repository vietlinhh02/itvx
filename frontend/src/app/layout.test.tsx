import type { ReactNode } from "react"
import { renderToStaticMarkup } from "react-dom/server"
import { expect, test, vi } from "vitest"

const { navigationLoadingProviderSpy } = vi.hoisted(() => ({
  navigationLoadingProviderSpy: vi.fn(({ children }: { children: ReactNode }) => (
    <div data-testid="navigation-loading-provider">{children}</div>
  )),
}))

vi.mock("next/font/local", () => ({
  default: () => ({
    variable: "font-google-sans",
  }),
}))

vi.mock("@/components/navigation/navigation-loading-provider", () => ({
  NavigationLoadingProvider: navigationLoadingProviderSpy,
}))

import RootLayout from "@/app/layout"

test("renders the navigation loading provider around root children", () => {
  const markup = renderToStaticMarkup(
    <RootLayout>
      <main>Page content</main>
    </RootLayout>,
  )

  expect(markup).toContain('data-testid="navigation-loading-provider"')
  expect(markup).toContain("Page content")
  expect(navigationLoadingProviderSpy).toHaveBeenCalled()
})
