import { create } from "zustand"
import { signIn, signOut } from "next-auth/react"

interface User {
  id: string
  email: string
  name: string | null
  role: string
  avatar_url: string | null
}

interface AuthState {
  isLoading: boolean
  error: string | null
  user: User | null

  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  setUser: (user: User | null) => void
  loginWithGoogle: () => Promise<void>
  logout: () => Promise<void>
}

export const useAuthStore = create<AuthState>((set) => ({
  isLoading: false,
  error: null,
  user: null,

  setLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error }),
  setUser: (user) => set({ user }),

  loginWithGoogle: async () => {
    set({ isLoading: true, error: null })
    try {
      await signIn("google", { callbackUrl: "/dashboard" })
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Login failed",
        isLoading: false,
      })
    }
  },

  logout: async () => {
    set({ isLoading: true })
    try {
      await signOut({ callbackUrl: "/login" })
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Logout failed",
        isLoading: false,
      })
    }
  },
}))
