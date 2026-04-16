import NextAuth from "next-auth"
import Google from "next-auth/providers/google"

type BackendAuthResponse = {
  tokens: {
    access_token: string
    refresh_token: string
    expires_in: number
  }
}

type ExtendedToken = {
  accessToken?: string
  refreshToken?: string
  accessTokenExpiresAt?: number
  authError?: string
}

const backendBaseUrl = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL

async function refreshBackendToken(token: ExtendedToken): Promise<ExtendedToken> {
  if (!backendBaseUrl || !token.refreshToken) {
    return { ...token, authError: "Missing refresh token" }
  }

  try {
    const response = await fetch(`${backendBaseUrl}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: token.refreshToken }),
    })

    if (!response.ok) {
      return { ...token, authError: "RefreshAccessTokenError" }
    }

    const data = (await response.json()) as BackendAuthResponse
    return {
      ...token,
      accessToken: data.tokens.access_token,
      refreshToken: data.tokens.refresh_token,
      accessTokenExpiresAt: Date.now() + data.tokens.expires_in * 1000,
      authError: undefined,
    }
  } catch {
    return { ...token, authError: "RefreshAccessTokenError" }
  }
}

export const { handlers: { GET, POST }, auth, signIn, signOut } = NextAuth({
  providers: [
    Google({
      authorization: {
        params: {
          prompt: "select_account",
        },
      },
    }),
  ],
  callbacks: {
    async jwt({ token, account }) {
      const extended = token as typeof token & ExtendedToken

      if (account?.provider === "google" && account.id_token && backendBaseUrl) {
        try {
          const response = await fetch(`${backendBaseUrl}/api/v1/auth/google`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ token: account.id_token }),
          })

          if (response.ok) {
            const data = (await response.json()) as BackendAuthResponse
            extended.accessToken = data.tokens.access_token
            extended.refreshToken = data.tokens.refresh_token
            extended.accessTokenExpiresAt = Date.now() + data.tokens.expires_in * 1000
            extended.authError = undefined
          }
        } catch {
          extended.authError = "BackendExchangeError"
        }
        return extended
      }

      if (extended.accessToken && extended.accessTokenExpiresAt) {
        const isStillValid = Date.now() < extended.accessTokenExpiresAt - 30_000
        if (isStillValid) {
          return extended
        }
        return await refreshBackendToken(extended)
      }

      return extended
    },
    async session({ session, token }) {
      const extended = token as typeof token & ExtendedToken
      session.accessToken = extended.accessToken
      session.refreshToken = extended.refreshToken
      session.accessTokenExpiresAt = extended.accessTokenExpiresAt
      session.authError = extended.authError
      return session
    },
  },
  pages: {
    signIn: "/login",
  },
})

declare module "next-auth" {
  interface Session {
    accessToken?: string
    refreshToken?: string
    accessTokenExpiresAt?: number
    authError?: string
  }
}
