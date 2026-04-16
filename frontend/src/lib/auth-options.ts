import type { NextAuthOptions, Session } from "next-auth"
import type { JWT } from "next-auth/jwt"
import GoogleProvider from "next-auth/providers/google"

type BackendAuthResponse = {
  tokens: {
    access_token: string
    refresh_token: string
    expires_in: number
  }
}

const backendBaseUrl = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL

async function refreshBackendToken(token: JWT): Promise<JWT> {
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

export const authOptions: NextAuthOptions = {
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID ?? process.env.AUTH_GOOGLE_ID ?? "",
      clientSecret: process.env.GOOGLE_CLIENT_SECRET ?? process.env.AUTH_GOOGLE_SECRET ?? "",
      authorization: {
        params: {
          prompt: "select_account",
        },
      },
    }),
  ],
  callbacks: {
    async jwt({ token, account }) {
      if (account?.provider === "google" && account.id_token && backendBaseUrl) {
        try {
          const response = await fetch(`${backendBaseUrl}/api/v1/auth/google`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ token: account.id_token }),
          })

          if (!response.ok) {
            token.authError = "BackendExchangeError"
            return token
          }

          const data = (await response.json()) as BackendAuthResponse
          token.accessToken = data.tokens.access_token
          token.refreshToken = data.tokens.refresh_token
          token.accessTokenExpiresAt = Date.now() + data.tokens.expires_in * 1000
          token.authError = undefined
        } catch {
          token.authError = "BackendExchangeError"
        }

        return token
      }

      if (token.accessToken && token.accessTokenExpiresAt) {
        const isStillValid = Date.now() < token.accessTokenExpiresAt - 30_000
        if (isStillValid) {
          return token
        }

        return refreshBackendToken(token)
      }

      return token
    },
    async session({ session, token }): Promise<Session> {
      session.accessToken = token.accessToken
      session.accessTokenExpiresAt = token.accessTokenExpiresAt
      session.authError = token.authError
      return session
    },
  },
  pages: {
    signIn: "/login",
  },
}

declare module "next-auth" {
  interface Session {
    accessToken?: string
    accessTokenExpiresAt?: number
    authError?: string
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    accessToken?: string
    refreshToken?: string
    accessTokenExpiresAt?: number
    authError?: string
  }
}
