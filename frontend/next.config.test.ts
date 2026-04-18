import { expect, test, vi } from "vitest"

async function loadNextConfig() {
  vi.resetModules()
  const loaded = await import("./next.config.js")
  return (loaded.default ?? loaded) as {
    experimental?: {
      proxyClientMaxBodySize?: number
    }
    rewrites?: () => Promise<Array<{ source: string; destination: string }>>
  }
}

test("configures proxy body size large enough for company document uploads", async () => {
  process.env.API_URL = "http://localhost:8000"
  const nextConfig = await loadNextConfig()

  expect(nextConfig.experimental?.proxyClientMaxBodySize).toBe(52_428_800)
})

test("keeps api rewrites pointed at the configured backend origin", async () => {
  process.env.API_URL = "http://localhost:8000"
  const nextConfig = await loadNextConfig()
  const rewrites = await nextConfig.rewrites?.()

  expect(rewrites).toEqual([
    {
      source: "/api/v1/:path*",
      destination: "http://localhost:8000/api/v1/:path*",
    },
  ])
})
