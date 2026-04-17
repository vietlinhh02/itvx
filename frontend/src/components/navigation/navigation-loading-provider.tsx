"use client"

import { createContext, useContext, useEffect, useMemo, useRef, useState } from "react"

import { usePathname, useSearchParams } from "next/navigation"

import { LoadingScreen } from "@/components/navigation/loading-screen"

type NavigationLoadingContextValue = {
  startLoading: () => void
  stopLoading: () => void
}

const NavigationLoadingContext = createContext<NavigationLoadingContextValue | null>(null)

export function NavigationLoadingProvider({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const [isLoading, setIsLoading] = useState(false)
  const routeKey = `${pathname}?${searchParams.toString()}`
  const hasMounted = useRef(false)

  useEffect(() => {
    if (!hasMounted.current) {
      hasMounted.current = true
      return
    }

    const timer = window.requestAnimationFrame(() => {
      setIsLoading(false)
    })

    return () => window.cancelAnimationFrame(timer)
  }, [routeKey])

  const value = useMemo<NavigationLoadingContextValue>(
    () => ({
      startLoading: () => setIsLoading(true),
      stopLoading: () => setIsLoading(false),
    }),
    [],
  )

  return (
    <NavigationLoadingContext.Provider value={value}>
      {children}
      {isLoading ? <LoadingScreen /> : null}
    </NavigationLoadingContext.Provider>
  )
}

export function useNavigationLoading() {
  return (
    useContext(NavigationLoadingContext) ?? {
      startLoading: () => {},
      stopLoading: () => {},
    }
  )
}
