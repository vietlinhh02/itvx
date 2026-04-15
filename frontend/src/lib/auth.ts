import NextAuth from "next-auth"
import Google from "next-auth/providers/google"

export const {
  handlers: { GET, POST },
  auth,
  signIn,
  signOut,
} = NextAuth({
  providers: [
    Google({
      clientId: process.env.AUTH_GOOGLE_ID!,
      clientSecret: process.env.AUTH_GOOGLE_SECRET!,
      authorization: {
        params: {
          prompt: "consent",
          access_type: "offline",
          response_type: "code",
        },
      },
    }),
  ],
  session: {
    strategy: "jwt",
    maxAge: 7 * 24 * 60 * 60, // 7 days
  },
  callbacks: {
    async jwt({ token, account, user }) {
      // Initial sign in
      if (account && user) {
        try {
          // Exchange Google token for our backend tokens
          const response = await fetch(
            `${process.env.API_URL}/api/v1/auth/google`,
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ token: account.id_token }),
            }
          )

          if (!response.ok) {
            throw new Error("Failed to authenticate with backend")
          }

          const data = await response.json()

          return {
            ...token,
            accessToken: data.tokens.access_token,
            refreshToken: data.tokens.refresh_token,
            expiresIn: data.tokens.expires_in,
            user: data.user,
          }
        } catch (error) {
          console.error("Auth error:", error)
          return token
        }
      }

      // Return previous token if not expired
      const tokenExpiry = (token as any).expiry as number
      if (Date.now() < tokenExpiry) {
        return token
      }

      // Refresh token if expired
      try {
        const response = await fetch(
          `${process.env.API_URL}/api/v1/auth/refresh`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ refresh_token: (token as any).refreshToken }),
          }
        )

        if (!response.ok) {
          throw new Error("Failed to refresh token")
        }

        const data = await response.json()

        return {
          ...token,
          accessToken: data.tokens.access_token,
          refreshToken: data.tokens.refresh_token,
          expiresIn: data.tokens.expires_in,
          expiry: Date.now() + data.tokens.expires_in * 1000,
        }
      } catch (error) {
        console.error("Token refresh error:", error)
        return { ...token, error: "RefreshTokenError" }
      }
    },
    async session({ session, token }) {
      session.accessToken = (token as any).accessToken
      session.refreshToken = (token as any).refreshToken
      session.user = (token as any).user
      session.error = (token as any).error
      return session
    },
  },
  pages: {
    signIn: "/login",
    error: "/login",
  },
})

// Type augmentation
declare module "next-auth" {
  interface Session {
    accessToken?: string
    refreshToken?: string
    error?: string
    user?: {
      id: string
      email: string
      name: string | null
      role: string
      avatar_url: string | null
    }
  }

  interface JWT {
    accessToken?: string
    refreshToken?: string
    expiresIn?: number
    expiry?: number
    user?: any
    error?: string
  }
}
