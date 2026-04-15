import type { Metadata } from "next"
import "./globals.css"

export const metadata: Metadata = {
  title: "InterviewX - AI Interview Platform",
  description: "Multi-Agent AI Interview System",
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  )
}
