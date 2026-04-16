# Next.js 16.2.4 and Auth Upgrade Design

## Goal
Upgrade the frontend from the current older Next.js and NextAuth stack to a supported, current stack that reduces framework-level incompatibilities and removes the old `next-auth` beta dependency.

## Current state
The frontend currently uses:

- `next@15.5.15`
- `react@18.3.1`
- `react-dom@18.3.1`
- `next-auth@5.0.0-beta.25`
- `@auth/core@0.37.0`

The app already uses the App Router and a shared auth module in `frontend/src/lib/auth.ts`. Server pages call `auth()` and client actions call `signIn` and `signOut` from `next-auth/react`.

## Problem
The current dependency combination is stale and partially mismatched:

- Next.js is not on the requested latest release.
- Auth relies on an old v5 beta release.
- React is behind the current version expected by recent Next.js releases.

This makes framework behavior, type compatibility, and authentication integration more likely to fail in ways that look unrelated at the feature level.

## Decision
Upgrade the frontend auth and framework stack together instead of changing only one package.

### Target versions
- `next` -> `16.2.4`
- `react` -> current compatible 19.x release
- `react-dom` -> current compatible 19.x release
- `@types/react` and `@types/react-dom` -> matching current versions
- `next-auth` -> current stable v5 release for Next.js

### Auth package decision
Keep using the `next-auth` package for the Next.js app.

Auth.js is the ecosystem name, but the official Next.js integration still ships as `next-auth`. The upgrade should move away from the old beta release, not replace the integration pattern with a different auth library.

## Approach
1. Update dependency versions in `frontend/package.json`.
2. Install updated dependencies and refresh the lockfile.
3. Fix compile or runtime breakage caused by the framework upgrade.
4. Keep the existing auth architecture unless the new versions require a minimal compatibility change.
5. Verify with type-checking and production build.

## Expected code changes

### Dependency and config updates
- `frontend/package.json`
- `frontend/pnpm-lock.yaml`
- possibly `frontend/tsconfig.json`
- possibly `frontend/eslint.config.mjs`

### Auth compatibility updates
- `frontend/src/lib/auth.ts`
- any client code that depends on `next-auth/react`

### Next.js 16 compatibility updates
Any pages or route handlers that break under Next.js 16 request API or type changes, especially dynamic App Router pages such as:

- `frontend/src/app/dashboard/jd/[id]/page.tsx`
- `frontend/src/app/dashboard/cv-screenings/[screeningId]/page.tsx`

## Non-goals
- No auth architecture rewrite.
- No provider changes.
- No unrelated refactors.
- No backend API contract changes unless frontend upgrade makes a tiny compatibility adjustment necessary.

## Risks

### Framework-induced type changes
Next.js 16 may require small updates around App Router typing or async request APIs.

### Auth runtime changes
Moving off the old beta may reveal assumptions that were tolerated before. These should be fixed only where they directly block auth or build behavior.

### Tooling drift
The repo currently uses ESLint instead of the newer lint stack described in global preferences. This upgrade will not replace lint tooling unless required for compatibility.

## Verification
The upgrade is considered complete when all of the following are true:

1. dependencies install cleanly
2. `tsc --noEmit` passes in `frontend`
3. `next build` passes in `frontend`
4. the existing auth entry points still compile and the app can resolve the auth module correctly

## Recommended implementation boundary
Keep this as one focused frontend-only change set: update the framework/auth stack, fix direct regressions, and stop there.
