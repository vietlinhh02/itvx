# Next.js 16.2.4 and next-auth v4 Rewrite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the frontend to Next.js 16.2.4 while rewriting the current v5-style auth integration to a working `next-auth` v4 setup that preserves backend token exchange.

**Architecture:** Replace the missing v5-style shared auth module with a v4-compatible split setup: route handler configuration under `src/app/api/auth/[...nextauth]/route.ts`, shared `authOptions` in a dedicated file, and server-side session access through `getServerSession(authOptions)`. Keep the existing backend Google-token exchange and refreshed access token flow, but express it through v4 callbacks and JWT/session typing.

**Tech Stack:** Next.js App Router, React 19, TypeScript, next-auth v4, pnpm

---

## File structure

- Modify: `frontend/package.json`
  - Pin Next.js 16.2.4, React 19.x, `next-auth` v4, and matching type/tooling versions.
- Modify: `frontend/pnpm-lock.yaml`
  - Capture the rewritten dependency graph after install.
- Create: `frontend/src/lib/auth-options.ts`
  - Hold the shared `NextAuthOptions`, custom token refresh logic, and module augmentation.
- Modify: `frontend/src/app/api/auth/[...nextauth]/route.ts`
  - Export the App Router route handler built from `NextAuth(authOptions)`.
- Modify: `frontend/src/middleware.ts`
  - Replace the current v5 re-export with v4-compatible middleware or remove auth dependency if unnecessary.
- Modify: `frontend/src/app/page.tsx`
  - Replace `auth()` usage with `getServerSession(authOptions)`.
- Modify: `frontend/src/app/dashboard/page.tsx`
  - Replace `auth()` usage while preserving backend `/auth/me` fetch behavior.
- Modify: `frontend/src/app/dashboard/jd/page.tsx`
  - Replace `auth()` usage while preserving JD list fetch behavior.
- Modify: `frontend/src/app/dashboard/jd/[id]/page.tsx`
  - Replace `auth()` usage and update async params typing if Next.js 16 requires it.
- Modify: `frontend/src/app/dashboard/cv-screenings/[screeningId]/page.tsx`
  - Replace `auth()` usage and update async params typing if Next.js 16 requires it.
- Modify if needed: `frontend/src/stores/authStore.ts`
  - Keep client `signIn` and `signOut` calls aligned with `next-auth/react` v4.
- Modify if needed: `frontend/tsconfig.json`
  - Apply only compatibility changes named by the upgraded toolchain.
- Modify if needed: `frontend/eslint.config.mjs`
  - Apply only compatibility changes named by the upgraded toolchain.

## Task 1: Rewrite the dependency targets for the v4 path

**Files:**
- Modify: `frontend/package.json`
- Test: manifest diff only in this task

- [ ] **Step 1: Edit the dependency targets for the v4 rewrite**

```json
{
  "dependencies": {
    "@auth/core": "remove",
    "next": "16.2.4",
    "next-auth": "4.24.14",
    "react": "19.2.5",
    "react-dom": "19.2.5"
  },
  "devDependencies": {
    "@types/react": "19.2.14",
    "@types/react-dom": "19.2.3",
    "eslint-config-next": "16.2.4"
  }
}
```

- [ ] **Step 2: Keep the unrelated dependency lines unchanged**

```json
{
  "dependencies": {
    "@phosphor-icons/react": "^2.1.10",
    "tailwindcss": "^4.0.0",
    "zustand": "^5.0.12"
  }
}
```

- [ ] **Step 3: Review the manifest diff before install**

Run: `git -C /home/eddiesngu/Desktop/Dang/interviewx/.claude/worktrees/nextjs-auth-upgrade diff -- frontend/package.json`
Expected: only `next`, `next-auth`, `react`, `react-dom`, React types, `eslint-config-next`, and `@auth/core` removal changed

- [ ] **Step 4: Commit the manifest rewrite**

```bash
git -C /home/eddiesngu/Desktop/Dang/interviewx/.claude/worktrees/nextjs-auth-upgrade add frontend/package.json
git -C /home/eddiesngu/Desktop/Dang/interviewx/.claude/worktrees/nextjs-auth-upgrade commit -m "chore: retarget frontend to next-auth v4"
```

## Task 2: Install the downgraded auth stack and capture the first failures

**Files:**
- Modify: `frontend/pnpm-lock.yaml`
- Test: install, type-check, and build output

- [ ] **Step 1: Install the rewritten dependency set**

Run: `cd /home/eddiesngu/Desktop/Dang/interviewx/.claude/worktrees/nextjs-auth-upgrade/frontend && pnpm install`
Expected: lockfile updates successfully with `next-auth@4.24.14`

- [ ] **Step 2: Confirm the resolved top-level versions**

Run: `cd /home/eddiesngu/Desktop/Dang/interviewx/.claude/worktrees/nextjs-auth-upgrade/frontend && pnpm list next react react-dom next-auth --depth 0`
Expected: `next@16.2.4`, `react@19.2.5`, `react-dom@19.2.5`, `next-auth@4.24.14`

- [ ] **Step 3: Run type-check to capture the first real failures**

Run: `cd /home/eddiesngu/Desktop/Dang/interviewx/.claude/worktrees/nextjs-auth-upgrade/frontend && pnpm run type-check`
Expected: FAIL with concrete errors around missing `@/lib/auth`, `auth()` imports, and possibly dynamic route typing

- [ ] **Step 4: Run build to capture Next.js 16 compatibility failures**

Run: `cd /home/eddiesngu/Desktop/Dang/interviewx/.claude/worktrees/nextjs-auth-upgrade/frontend && pnpm run build`
Expected: PASS or FAIL with concrete App Router or middleware errors to fix in later tasks

- [ ] **Step 5: Commit the dependency install state**

```bash
git -C /home/eddiesngu/Desktop/Dang/interviewx/.claude/worktrees/nextjs-auth-upgrade add frontend/package.json frontend/pnpm-lock.yaml
git -C /home/eddiesngu/Desktop/Dang/interviewx/.claude/worktrees/nextjs-auth-upgrade commit -m "chore: install next-auth v4 frontend stack"
```

## Task 3: Add the shared v4 auth configuration

**Files:**
- Create: `frontend/src/lib/auth-options.ts`
- Test: `frontend/src/app/api/auth/[...nextauth]/route.ts` can import it

- [ ] **Step 1: Write the failing import target by creating the shared auth options file reference**

```ts
import { authOptions } from "@/lib/auth-options"
```

- [ ] **Step 2: Run type-check to confirm the new import target does not exist yet**

Run: `cd /home/eddiesngu/Desktop/Dang/interviewx/.claude/worktrees/nextjs-auth-upgrade/frontend && pnpm run type-check`
Expected: FAIL with `Cannot find module '@/lib/auth-options'`

- [ ] **Step 3: Create the shared v4 auth options file with backend token exchange**

```ts
import type { NextAuthOptions } from "next-auth"
import GoogleProvider from "next-auth/providers/google"

import type { JWT } from "next-auth/jwt"

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

          if (response.ok) {
            const data = (await response.json()) as BackendAuthResponse
            token.accessToken = data.tokens.access_token
            token.refreshToken = data.tokens.refresh_token
            token.accessTokenExpiresAt = Date.now() + data.tokens.expires_in * 1000
            token.authError = undefined
          }
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
    async session({ session, token }) {
      session.accessToken = token.accessToken
      session.refreshToken = token.refreshToken
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
    refreshToken?: string
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
```

- [ ] **Step 4: Run type-check to confirm the new shared config compiles**

Run: `cd /home/eddiesngu/Desktop/Dang/interviewx/.claude/worktrees/nextjs-auth-upgrade/frontend && pnpm run type-check`
Expected: the missing-module error for `@/lib/auth-options` is gone

- [ ] **Step 5: Commit the shared auth config**

```bash
git -C /home/eddiesngu/Desktop/Dang/interviewx/.claude/worktrees/nextjs-auth-upgrade add frontend/src/lib/auth-options.ts
git -C /home/eddiesngu/Desktop/Dang/interviewx/.claude/worktrees/nextjs-auth-upgrade commit -m "feat: add shared next-auth v4 config"
```

## Task 4: Replace the auth route handler and middleware entrypoints

**Files:**
- Modify: `frontend/src/app/api/auth/[...nextauth]/route.ts`
- Modify: `frontend/src/middleware.ts`
- Test: `pnpm run type-check`

- [ ] **Step 1: Write the failing route-handler import**

```ts
import NextAuth from "next-auth"
import { authOptions } from "@/lib/auth-options"
```

- [ ] **Step 2: Replace the route file with a v4-compatible App Router handler**

```ts
import NextAuth from "next-auth"

import { authOptions } from "@/lib/auth-options"

const handler = NextAuth(authOptions)

export { handler as GET, handler as POST }
```

- [ ] **Step 3: Replace the current middleware re-export with a v4-compatible middleware wrapper**

```ts
export { default } from "next-auth/middleware"

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico|login).*)"],
}
```

- [ ] **Step 4: Run type-check to confirm the route and middleware compile**

Run: `cd /home/eddiesngu/Desktop/Dang/interviewx/.claude/worktrees/nextjs-auth-upgrade/frontend && pnpm run type-check`
Expected: route-handler and middleware errors removed

- [ ] **Step 5: Commit the entrypoint rewrite**

```bash
git -C /home/eddiesngu/Desktop/Dang/interviewx/.claude/worktrees/nextjs-auth-upgrade add frontend/src/app/api/auth/[...nextauth]/route.ts frontend/src/middleware.ts
git -C /home/eddiesngu/Desktop/Dang/interviewx/.claude/worktrees/nextjs-auth-upgrade commit -m "fix: rewrite auth entrypoints for next-auth v4"
```

## Task 5: Replace server-side `auth()` calls with `getServerSession`

**Files:**
- Modify: `frontend/src/app/page.tsx`
- Modify: `frontend/src/app/dashboard/page.tsx`
- Modify: `frontend/src/app/dashboard/jd/page.tsx`
- Modify: `frontend/src/app/dashboard/jd/[id]/page.tsx`
- Modify: `frontend/src/app/dashboard/cv-screenings/[screeningId]/page.tsx`
- Test: `pnpm run type-check`

- [ ] **Step 1: Write the new server-session imports in each server page**

```ts
import { getServerSession } from "next-auth"

import { authOptions } from "@/lib/auth-options"
```

- [ ] **Step 2: Replace each `auth()` call with `getServerSession(authOptions)`**

```ts
const session = await getServerSession(authOptions)
```

- [ ] **Step 3: Keep the existing redirect and backend API fetch logic unchanged**

```ts
if (!session?.accessToken || !backendBaseUrl) {
  redirect("/login")
}
```

- [ ] **Step 4: Run type-check to verify the server pages now resolve session access**

Run: `cd /home/eddiesngu/Desktop/Dang/interviewx/.claude/worktrees/nextjs-auth-upgrade/frontend && pnpm run type-check`
Expected: no remaining references to missing `@/lib/auth` or `auth()` on these pages

- [ ] **Step 5: Commit the server-session rewrite**

```bash
git -C /home/eddiesngu/Desktop/Dang/interviewx/.claude/worktrees/nextjs-auth-upgrade add frontend/src/app/page.tsx frontend/src/app/dashboard/page.tsx frontend/src/app/dashboard/jd/page.tsx frontend/src/app/dashboard/jd/[id]/page.tsx frontend/src/app/dashboard/cv-screenings/[screeningId]/page.tsx
git -C /home/eddiesngu/Desktop/Dang/interviewx/.claude/worktrees/nextjs-auth-upgrade commit -m "fix: use getServerSession in app router pages"
```

## Task 6: Fix Next.js 16 route typing and client auth compatibility

**Files:**
- Modify if failing: `frontend/src/app/dashboard/jd/[id]/page.tsx`
- Modify if failing: `frontend/src/app/dashboard/cv-screenings/[screeningId]/page.tsx`
- Modify if failing: `frontend/src/stores/authStore.ts`
- Test: `pnpm run type-check`

- [ ] **Step 1: If dynamic route props fail, switch to async params typing for the JD page**

```tsx
type PageProps = {
  params: Promise<{
    id: string
  }>
}

export default async function Page({ params }: PageProps) {
  const { id } = await params
  return id
}
```

- [ ] **Step 2: If dynamic route props fail, switch to async params typing for the screening detail page**

```tsx
type PageProps = {
  params: Promise<{
    screeningId: string
  }>
}

export default async function Page({ params }: PageProps) {
  const { screeningId } = await params
  return screeningId
}
```

- [ ] **Step 3: Keep the client auth store on the v4 client API**

```ts
import { signIn, signOut } from "next-auth/react"
```

- [ ] **Step 4: Re-run type-check after these compatibility edits**

Run: `cd /home/eddiesngu/Desktop/Dang/interviewx/.claude/worktrees/nextjs-auth-upgrade/frontend && pnpm run type-check`
Expected: dynamic route and client auth API errors removed

- [ ] **Step 5: Commit the compatibility cleanup**

```bash
git -C /home/eddiesngu/Desktop/Dang/interviewx/.claude/worktrees/nextjs-auth-upgrade add frontend/src/app/dashboard/jd/[id]/page.tsx frontend/src/app/dashboard/cv-screenings/[screeningId]/page.tsx frontend/src/stores/authStore.ts
git -C /home/eddiesngu/Desktop/Dang/interviewx/.claude/worktrees/nextjs-auth-upgrade commit -m "fix: align routes and client auth with upgraded stack"
```

## Task 7: Fix toolchain config only if verification names it

**Files:**
- Modify if failing: `frontend/tsconfig.json`
- Modify if failing: `frontend/eslint.config.mjs`
- Test: `pnpm run type-check` and `pnpm run build`

- [ ] **Step 1: Make only the named TypeScript config change**

```json
{
  "compilerOptions": {
    "strict": true
  }
}
```

- [ ] **Step 2: Make only the named ESLint config change**

```js
export default [
  // preserve the existing config shape and change only the option or import named by the failure output
]
```

- [ ] **Step 3: Re-run type-check after each config edit**

Run: `cd /home/eddiesngu/Desktop/Dang/interviewx/.claude/worktrees/nextjs-auth-upgrade/frontend && pnpm run type-check`
Expected: config-related failures removed

- [ ] **Step 4: Commit only if a real config change was required**

```bash
git -C /home/eddiesngu/Desktop/Dang/interviewx/.claude/worktrees/nextjs-auth-upgrade add frontend/tsconfig.json frontend/eslint.config.mjs
git -C /home/eddiesngu/Desktop/Dang/interviewx/.claude/worktrees/nextjs-auth-upgrade commit -m "fix: align frontend config with nextjs 16"
```

## Task 8: Final verification

**Files:**
- No new code required
- Test: final verification commands

- [ ] **Step 1: Run final type-check**

Run: `cd /home/eddiesngu/Desktop/Dang/interviewx/.claude/worktrees/nextjs-auth-upgrade/frontend && pnpm run type-check`
Expected: PASS with no TypeScript errors

- [ ] **Step 2: Run final production build**

Run: `cd /home/eddiesngu/Desktop/Dang/interviewx/.claude/worktrees/nextjs-auth-upgrade/frontend && pnpm run build`
Expected: PASS with no framework compile errors

- [ ] **Step 3: Review final diff scope**

Run: `git -C /home/eddiesngu/Desktop/Dang/interviewx/.claude/worktrees/nextjs-auth-upgrade diff --stat`
Expected: changes limited to dependency, auth, routing, and toolchain compatibility files

- [ ] **Step 4: Record the resolved state in the handoff note**

```text
Resolved versions:
- next: 16.2.4
- react: 19.2.5
- react-dom: 19.2.5
- next-auth: 4.24.14

Required code fixes:
- shared auth config file added: yes
- v4 route handler rewrite: yes
- server page session access rewrite: yes
- dynamic route async params changes: yes/no
- config changes: yes/no
```

- [ ] **Step 5: Commit the verification-ready state**

```bash
git -C /home/eddiesngu/Desktop/Dang/interviewx/.claude/worktrees/nextjs-auth-upgrade add frontend/package.json frontend/pnpm-lock.yaml frontend/src/lib/auth-options.ts frontend/src/app/api/auth/[...nextauth]/route.ts frontend/src/middleware.ts frontend/src/app/page.tsx frontend/src/app/dashboard/page.tsx frontend/src/app/dashboard/jd/page.tsx frontend/src/app/dashboard/jd/[id]/page.tsx frontend/src/app/dashboard/cv-screenings/[screeningId]/page.tsx frontend/src/stores/authStore.ts frontend/tsconfig.json frontend/eslint.config.mjs
git -C /home/eddiesngu/Desktop/Dang/interviewx/.claude/worktrees/nextjs-auth-upgrade commit -m "chore: complete next-auth v4 rewrite"
```
