"use client"

import Link from "next/link"
import type { ComponentProps } from "react"

import { useNavigationLoading } from "@/components/navigation/navigation-loading-provider"

type AppLinkProps = ComponentProps<typeof Link>

export function AppLink({ onClick, href, ...props }: AppLinkProps) {
  const { startLoading } = useNavigationLoading()

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

        startLoading()
      }}
    />
  )
}
