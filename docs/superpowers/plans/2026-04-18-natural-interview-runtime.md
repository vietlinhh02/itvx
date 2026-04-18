# Natural Interview Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep realtime interviews natural by continuing to ask clarifying questions or moving topics after HR-review signals, and only mention HR review in the final wrap-up.

**Architecture:** Introduce a dedicated runtime decision state, `continue_with_hr_flag`, for sessions that should continue while preserving HR-review metadata. Update backend evaluation, worker decision routing, and summary behavior so only `ready_to_wrap` closes the session naturally.

**Tech Stack:** FastAPI, Pydantic, LiveKit worker runtime, pytest, TypeScript UI helpers

---

### Task 1: Lock backend runtime behavior with tests

**Files:**
- Modify: `backend/tests/services/test_interview_session_service.py`

- [ ] **Step 1: Write the failing tests**

Add tests that assert:

- semantic or heuristic paths that previously produced `escalate_hr` now produce `continue_with_hr_flag`
- `runtime-state` still returns `current_question` for `continue_with_hr_flag`
- `ready_to_wrap` still hides `current_question`
- final summary can still recommend HR review when the final plan ended with `continue_with_hr_flag`

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --directory backend pytest -q tests/services/test_interview_session_service.py -k 'continue_with_hr_flag or runtime_state_hides_current_question_when_ready_to_wrap'`
Expected: FAIL because backend still emits `escalate_hr` or hides current question too aggressively.

- [ ] **Step 3: Write minimal implementation**

Update backend runtime mapping in `backend/src/services/interview_session_service.py` so HR-review signals map to `continue_with_hr_flag` instead of `escalate_hr`, except for legacy completion reasons.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --directory backend pytest -q tests/services/test_interview_session_service.py -k 'continue_with_hr_flag or runtime_state_hides_current_question_when_ready_to_wrap'`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/services/interview_session_service.py backend/tests/services/test_interview_session_service.py
git commit -m "Keep HR review signals from ending interviews early"
```

### Task 2: Update worker routing so HR review does not close the session

**Files:**
- Modify: `worker/src/agent.py`
- Modify: `worker/tests/test_agent_smoke.py`

- [ ] **Step 1: Write the failing tests**

Add tests that assert:

- `continue_with_hr_flag` does not trigger `end_interview`
- worker continues asking `current_question_vi`
- `ready_to_wrap` remains the only natural auto-close path

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --directory worker pytest -q tests/test_agent_smoke.py -k 'continue_with_hr_flag or ready_to_wrap'`
Expected: FAIL because worker still treats the HR-review runtime state as a close-now condition.

- [ ] **Step 3: Write minimal implementation**

Change worker instructions and runtime sync logic so `continue_with_hr_flag` is treated like `continue` or `adjust`, and remove any mid-session closing branch tied to HR-review runtime status.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --directory worker pytest -q tests/test_agent_smoke.py -k 'continue_with_hr_flag or ready_to_wrap'`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add worker/src/agent.py worker/tests/test_agent_smoke.py
git commit -m "Route HR review flags through continued interview turns"
```

### Task 3: Update summary and UI labels for the new runtime state

**Files:**
- Modify: `backend/src/services/interview_summary_service.py`
- Modify: `backend/src/schemas/interview.py`
- Modify: `frontend/src/components/interview/interview-types.ts`
- Modify: `frontend/src/components/interview/live-room/live-room-utils.ts`

- [ ] **Step 1: Write the failing tests**

Add or update tests so summary and UI expectations handle `continue_with_hr_flag` as a continued-interview status that still implies HR review later.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --directory backend pytest -q tests/services/test_interview_session_service.py -k 'summary'`
Run: `npm --prefix frontend test -- --runInBand live-room`
Expected: FAIL where old code assumes only `escalate_hr` carries HR-review meaning.

- [ ] **Step 3: Write minimal implementation**

Teach summary fallback logic and frontend labels/types to recognize `continue_with_hr_flag`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --directory backend pytest -q tests/services/test_interview_session_service.py -k 'summary'`
Run: `npm --prefix frontend test -- --runInBand live-room`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/services/interview_summary_service.py backend/src/schemas/interview.py frontend/src/components/interview/interview-types.ts frontend/src/components/interview/live-room/live-room-utils.ts
git commit -m "Expose continued HR review status across summary and UI"
```

### Task 4: Verify the targeted runtime flow end to end

**Files:**
- Modify: none

- [ ] **Step 1: Run backend interview session tests**

Run: `uv run --directory backend pytest -q tests/services/test_interview_session_service.py`
Expected: PASS

- [ ] **Step 2: Run worker agent smoke tests**

Run: `uv run --directory worker pytest -q tests/test_agent_smoke.py`
Expected: PASS

- [ ] **Step 3: Run narrow frontend tests if they exist**

Run: `npm --prefix frontend test -- --runInBand live-room`
Expected: PASS or skip if the suite is unavailable in this environment.

- [ ] **Step 4: Record verification notes**

Capture:

- which tests passed
- whether any unrelated lint/typecheck failures remain in the repo
- whether any legacy `escalate_hr` completion reasons are still intentionally preserved for finished sessions

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "Verify natural interview runtime flow"
```
