# Natural Interview Runtime Design

## Goal

Make the realtime interview flow feel natural and non-abrupt. Signals that HR should review later must not end the conversation mid-session. The worker should continue clarifying or move to other topics, then mention HR review only in the final wrap-up or after the candidate leaves.

## Current Problem

Today the runtime uses `escalate_hr` as both:

- a semantic signal that HR should review later
- a hard stop signal that causes the worker to close the interview early

That coupling makes the conversation feel unnatural. It can terminate while the candidate is still providing useful evidence.

## Design

### Runtime state model

Add a new runtime decision status: `continue_with_hr_flag`.

Meaning:

- `continue`: normal probing
- `adjust`: clarify or recover inside the current competency
- `continue_with_hr_flag`: continue interviewing, but keep a visible HR-review signal for the final summary
- `ready_to_wrap`: start the natural closing turn

`escalate_hr` stops being a runtime interview-control state. It remains valid as a historical completion reason for already-finished sessions and transcript review output.

### Backend evaluation behavior

When the system sees ambiguity, inconsistency, or low-confidence evidence that should remain visible to HR:

- keep `needs_hr_review=true` in semantic/final plan artifacts
- return `continue_with_hr_flag` instead of `escalate_hr`
- continue with a recovery or clarification question when useful
- move on to another competency when the current one is no longer productive

The backend should reserve `ready_to_wrap` as the only normal runtime close signal.

### Worker behavior

The worker must treat `continue_with_hr_flag` like a continue-style state:

- fetch runtime state
- ask the next question
- do not call `end_interview`
- do not say "HR will review" mid-session

Only `ready_to_wrap` should cause the worker to prepare the closing turn and complete the session.

### Runtime-state payload

`runtime-state` should keep returning `current_question` for:

- `continue`
- `adjust`
- `continue_with_hr_flag`

It should hide `current_question` only when the runtime is actually closing, such as `ready_to_wrap`.

### Final summary and closing language

The summary layer should infer HR review from:

- `continue_with_hr_flag` in the final plan
- `needs_hr_review`
- unresolved recovery markers such as `needs_recovery`

If those signals are present, the final recommendation can still say HR review is required, but that should happen after the interview has naturally concluded or after the candidate disconnects.

## Files

- Modify: `backend/src/services/interview_session_service.py`
- Modify: `backend/src/services/interview_summary_service.py`
- Modify: `backend/src/schemas/interview.py`
- Modify: `worker/src/agent.py`
- Modify: `worker/tests/test_agent_smoke.py`
- Modify: `backend/tests/services/test_interview_session_service.py`
- Modify: `frontend/src/components/interview/interview-types.ts`
- Modify: `frontend/src/components/interview/live-room/live-room-utils.ts`

## Acceptance Criteria

- The interview never ends mid-session just because a turn sets an HR-review signal.
- Recovery and clarification can continue naturally after HR review is flagged.
- The worker only completes the interview on `ready_to_wrap` or candidate disconnect flow.
- The final summary can still recommend HR review when the session carried unresolved ambiguity.
- Runtime UI labels remain readable for the new status.
