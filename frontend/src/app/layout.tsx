import type { Metadata } from "next"
import localFont from "next/font/local"
import "./globals.css"

const googleSans = localFont({
  src: [
    {
      path: "../../public/font/static/GoogleSans-Regular.ttf",
      weight: "400",
      style: "normal",
    },
    {
      path: "../../public/font/static/GoogleSans-Medium.ttf",
      weight: "500",
      style: "normal",
    },
    {
      path: "../../public/font/static/GoogleSans-SemiBold.ttf",
      weight: "600",
      style: "normal",
    },
    {
      path: "../../public/font/static/GoogleSans-Bold.ttf",
      weight: "700",
      style: "normal",
    },
  ],
  variable: "--font-google-sans",
})

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
    <html lang="vi">
      <body className={`${googleSans.variable} antialiased`}>{children}</body>
    </html>
  )
}
