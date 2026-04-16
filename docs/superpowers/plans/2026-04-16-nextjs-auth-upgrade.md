# Next.js 16.2.4 and Auth Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the frontend to Next.js 16.2.4 with a current compatible React/Auth stack and fix only the direct regressions introduced by the upgrade.

**Architecture:** Keep the existing App Router and shared auth module design. Update framework and auth dependencies first, then fix breakages at the dependency boundary, auth module, and dynamic route typing layer until the frontend type-checks and builds cleanly.

**Tech Stack:** Next.js App Router, React, TypeScript, next-auth v5, pnpm

---

## File structure

- Modify: `frontend/package.json`
  - Pin the upgraded framework, React, auth, and type package versions.
- Modify: `frontend/pnpm-lock.yaml`
  - Capture the dependency graph after install.
- Modify if needed: `frontend/tsconfig.json`
  - Apply only compatibility changes required by Next.js 16 or React 19 types.
- Modify if needed: `frontend/eslint.config.mjs`
  - Apply only compatibility fixes required by upgraded dependencies.
- Modify if needed: `frontend/src/lib/auth.ts`
  - Keep the shared auth module working with the upgraded `next-auth` package.
- Modify if needed: `frontend/src/stores/authStore.ts`
  - Keep `signIn` and `signOut` usage compatible with upgraded auth packages.
- Modify if needed: `frontend/src/app/dashboard/jd/[id]/page.tsx`
  - Fix dynamic route typing or async params usage required by Next.js 16.
- Modify if needed: `frontend/src/app/dashboard/cv-screenings/[screeningId]/page.tsx`
  - Fix dynamic route typing or async params usage required by Next.js 16.

## Task 1: Upgrade the dependency manifest

**Files:**
- Modify: `frontend/package.json`
- Test: dependency diff only in this task

- [ ] **Step 1: Edit the frontend dependency versions**

```json
{
  "dependencies": {
    "@auth/core": "REMOVE if no longer directly required after install resolution check",
    "next": "16.2.4",
    "next-auth": "use current stable v5 release resolved during install",
    "react": "use current compatible 19.x release resolved during install",
    "react-dom": "use current compatible 19.x release resolved during install"
  },
  "devDependencies": {
    "@types/react": "use matching current version",
    "@types/react-dom": "use matching current version",
    "eslint-config-next": "16.2.4"
  }
}
```

- [ ] **Step 2: Keep unrelated dependency versions unchanged**

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

Run: `git diff -- frontend/package.json`
Expected: only framework, auth, React, and matching type/tooling version lines changed

- [ ] **Step 4: Commit the manifest edit**

```bash
git add frontend/package.json
git commit -m "chore: bump nextjs auth upgrade targets"
```

## Task 2: Install dependencies and capture the real resolved versions

**Files:**
- Modify: `frontend/pnpm-lock.yaml`
- Modify if needed: `frontend/package.json`
- Test: install output

- [ ] **Step 1: Install dependencies in the frontend workspace**

Run: `cd /home/eddiesngu/Desktop/Dang/interviewx/frontend && pnpm install`
Expected: lockfile updated without unresolved peer dependency failure

- [ ] **Step 2: If install rewrites package versions, keep the resolved stable versions**

```json
{
  "dependencies": {
    "next-auth": "<resolved stable v5>",
    "react": "<resolved 19.x>",
    "react-dom": "<resolved 19.x>"
  }
}
```

- [ ] **Step 3: Confirm the resolved framework stack**

Run: `cd /home/eddiesngu/Desktop/Dang/interviewx/frontend && pnpm list next react react-dom next-auth --depth 0`
Expected: `next@16.2.4`, React 19.x, and a non-beta `next-auth` v5 release

- [ ] **Step 4: Commit the lockfile update**

```bash
git add frontend/package.json frontend/pnpm-lock.yaml
git commit -m "chore: install upgraded frontend dependencies"
```

## Task 3: Capture the first failing verification signal

**Files:**
- No code changes required in this task
- Test: build and type-check output

- [ ] **Step 1: Run type-check on the upgraded frontend**

Run: `cd /home/eddiesngu/Desktop/Dang/interviewx/frontend && pnpm run type-check`
Expected: FAIL, with concrete file paths and TypeScript errors to fix in later tasks

- [ ] **Step 2: Run production build on the upgraded frontend**

Run: `cd /home/eddiesngu/Desktop/Dang/interviewx/frontend && pnpm run build`
Expected: PASS or FAIL with concrete Next.js 16 compile/runtime compatibility errors

- [ ] **Step 3: Save the first real error list in working notes**

```text
Auth module errors:
- frontend/src/lib/auth.ts:...

Dynamic route errors:
- frontend/src/app/dashboard/jd/[id]/page.tsx:...
- frontend/src/app/dashboard/cv-screenings/[screeningId]/page.tsx:...

Tooling/config errors:
- frontend/tsconfig.json:...
- frontend/eslint.config.mjs:...
```

- [ ] **Step 4: Do not fix anything not named by the failing output**

```text
Scope rule:
- fix only errors introduced or exposed by the upgrade
- no unrelated refactors
- no auth architecture rewrite
```

## Task 4: Fix auth module compatibility

**Files:**
- Modify if failing: `frontend/src/lib/auth.ts`
- Modify if failing: `frontend/src/stores/authStore.ts`
- Test: `pnpm run type-check`

- [ ] **Step 1: Write down the exact auth failure before editing**

```text
Hypothesis format:
I think the auth breakage is caused by <specific changed API or type> because <exact error output>.
```

- [ ] **Step 2: Apply the minimal auth compatibility fix required by the error**

```ts
import NextAuth from "next-auth"
import Google from "next-auth/providers/google"

export const {
  handlers: { GET, POST },
  auth,
  signIn,
  signOut,
} = NextAuth({
  providers: [Google({ authorization: { params: { prompt: "select_account" } } })],
  callbacks: {
    async jwt({ token, account }) {
      return token
    },
    async session({ session, token }) {
      return session
    },
  },
  pages: {
    signIn: "/login",
  },
})
```

- [ ] **Step 3: Keep the client store imports aligned with the package API actually installed**

```ts
import { signIn, signOut } from "next-auth/react"
```

- [ ] **Step 4: Re-run type-check to confirm auth errors are gone or reduced**

Run: `cd /home/eddiesngu/Desktop/Dang/interviewx/frontend && pnpm run type-check`
Expected: auth-specific errors removed, or a smaller remaining error set pointing to the next exact incompatibility

- [ ] **Step 5: Commit the auth compatibility fix**

```bash
git add frontend/src/lib/auth.ts frontend/src/stores/authStore.ts
git commit -m "fix: restore auth compatibility after upgrade"
```

## Task 5: Fix Next.js 16 dynamic route typing

**Files:**
- Modify if failing: `frontend/src/app/dashboard/jd/[id]/page.tsx`
- Modify if failing: `frontend/src/app/dashboard/cv-screenings/[screeningId]/page.tsx`
- Test: `pnpm run type-check`

- [ ] **Step 1: Update route props to the async params style if the build requires it**

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

- [ ] **Step 2: Use the same pattern for the screening detail route if it fails**

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

- [ ] **Step 3: Keep existing page logic unchanged apart from the required typing/request API changes**

```tsx
const session = await auth()
if (!session?.accessToken || !backendBaseUrl) {
  redirect("/login")
}
```

- [ ] **Step 4: Re-run type-check**

Run: `cd /home/eddiesngu/Desktop/Dang/interviewx/frontend && pnpm run type-check`
Expected: dynamic route errors removed

- [ ] **Step 5: Commit the route compatibility fix**

```bash
git add frontend/src/app/dashboard/jd/[id]/page.tsx frontend/src/app/dashboard/cv-screenings/[screeningId]/page.tsx
git commit -m "fix: update app router pages for nextjs 16"
```

## Task 6: Fix config-level compatibility only if verification names it

**Files:**
- Modify if failing: `frontend/tsconfig.json`
- Modify if failing: `frontend/eslint.config.mjs`
- Test: `pnpm run type-check` and `pnpm run build`

- [ ] **Step 1: Change TypeScript config only if the upgraded toolchain names a specific incompatibility**

```json
{
  "compilerOptions": {
    "strict": true
  }
}
```

- [ ] **Step 2: Change ESLint config only if the upgraded toolchain names a specific incompatibility**

```js
export default [
  // keep existing config shape, update only broken imports or options required by Next 16
]
```

- [ ] **Step 3: Re-run type-check after each config edit**

Run: `cd /home/eddiesngu/Desktop/Dang/interviewx/frontend && pnpm run type-check`
Expected: config-related failures removed

- [ ] **Step 4: Commit only if a real config change was needed**

```bash
git add frontend/tsconfig.json frontend/eslint.config.mjs
git commit -m "fix: align frontend config with upgraded toolchain"
```

## Task 7: Final verification

**Files:**
- No new code required
- Test: final verification commands

- [ ] **Step 1: Run final type-check**

Run: `cd /home/eddiesngu/Desktop/Dang/interviewx/frontend && pnpm run type-check`
Expected: PASS with no TypeScript errors

- [ ] **Step 2: Run final production build**

Run: `cd /home/eddiesngu/Desktop/Dang/interviewx/frontend && pnpm run build`
Expected: PASS with no framework compile errors

- [ ] **Step 3: Review final diff for upgrade-only scope**

Run: `git diff --stat`
Expected: changes limited to dependency, auth, routing, and config compatibility files

- [ ] **Step 4: Record the resolved versions and any required code changes in the handoff note**

```text
Resolved versions:
- next: ...
- react: ...
- react-dom: ...
- next-auth: ...

Required code fixes:
- auth module compatibility: yes/no
- dynamic route async params changes: yes/no
- config changes: yes/no
```

- [ ] **Step 5: Commit the final verification-ready state**

```bash
git add frontend/package.json frontend/pnpm-lock.yaml frontend/src/lib/auth.ts frontend/src/stores/authStore.ts frontend/src/app/dashboard/jd/[id]/page.tsx frontend/src/app/dashboard/cv-screenings/[screeningId]/page.tsx frontend/tsconfig.json frontend/eslint.config.mjs
git commit -m "chore: complete nextjs auth upgrade"
```
