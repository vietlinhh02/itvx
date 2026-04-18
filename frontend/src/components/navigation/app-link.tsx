"use client"

import Link from "next/link"
import type { ComponentProps } from "react"
import { usePathname } from "next/navigation"

import { useNavigationLoading } from "@/components/navigation/navigation-loading-provider"

type AppLinkProps = ComponentProps<typeof Link>

export function AppLink({ onClick, href, ...props }: AppLinkProps) {
  const { startLoading } = useNavigationLoading()
  const pathname = usePathname()
  const currentPathname = pathname ?? ""

  return (
    <Link
      {...props}
      href={href}
      onClick={(event) => {
        onClick?.(event)

        if (
          event.defaultPrevented ||
          event.metaKey ||
          event.ctrlKey ||
          event.shiftKey ||
          event.altKey ||
          props.target === "_blank"
        ) {
          return
        }

        if (isCurrentRoute(href, currentPathname)) {
          return
        }

        startLoading()
      }}
    />
  )
}

function isCurrentRoute(href: AppLinkProps["href"], currentPathname: string) {
  if (typeof href !== "string") {
    return false
  }

  const target = new URL(href, "http://localhost")

  return target.pathname === currentPathname
}
