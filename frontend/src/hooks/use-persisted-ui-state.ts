"use client"

import { useEffect, useState } from "react"

export function useSessionStorageState<T>(storageKey: string, initialValue: T) {
  const [state, setState] = useState<T>(initialValue)
  const [hasHydrated, setHasHydrated] = useState(false)

  useEffect(() => {
    try {
      const raw = window.sessionStorage.getItem(storageKey)
      if (raw !== null) {
        setState(JSON.parse(raw) as T)
      }
    } catch (error) {
      console.warn(`[persisted-ui-state] could not restore ${storageKey}`, error)
      window.sessionStorage.removeItem(storageKey)
    } finally {
      setHasHydrated(true)
    }
  }, [storageKey])

  useEffect(() => {
    if (!hasHydrated) {
      return
    }

    window.sessionStorage.setItem(storageKey, JSON.stringify(state))
  }, [hasHydrated, state, storageKey])

  return [state, setState, hasHydrated] as const
}

export function usePageScrollRestore(storageKey: string) {
  useEffect(() => {
    const raw = window.sessionStorage.getItem(storageKey)
    if (raw) {
      const y = Number.parseFloat(raw)
      if (Number.isFinite(y)) {
        window.requestAnimationFrame(() => {
          try {
            window.scrollTo({ top: y, behavior: "auto" })
          } catch (error) {
            console.warn(`[persisted-ui-state] could not restore scroll for ${storageKey}`, error)
          }
        })
      }
    }

    const persistScrollPosition = () => {
      window.sessionStorage.setItem(storageKey, String(window.scrollY))
    }

    window.addEventListener("scroll", persistScrollPosition, { passive: true })
    window.addEventListener("beforeunload", persistScrollPosition)

    return () => {
      persistScrollPosition()
      window.removeEventListener("scroll", persistScrollPosition)
      window.removeEventListener("beforeunload", persistScrollPosition)
    }
  }, [storageKey])
}
