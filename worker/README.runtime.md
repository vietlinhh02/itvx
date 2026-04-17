# Realtime Interview Runtime Notes

## Required environment

- `LIVEKIT_URL`: LiveKit Cloud websocket URL
- `LIVEKIT_API_KEY`: LiveKit Cloud API key
- `LIVEKIT_API_SECRET`: LiveKit Cloud API secret
- `GEMINI_API_KEY`: Gemini Developer API key
- `WORKER_CALLBACK_SECRET`: shared secret used by the worker callback headers

## Startup

Backend stays as-is. Open a separate terminal for the long-lived worker service:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && export LIVEKIT_URL="wss://<project>.livekit.cloud" LIVEKIT_API_KEY="..." LIVEKIT_API_SECRET="..." GEMINI_API_KEY="..." WORKER_CALLBACK_SECRET="..." && bash src/scripts/run_interview_worker_service.sh
```

The backend will push each new interview session to `http://127.0.0.1:8765/dispatch-session` by default.

## Verification

Run these commands and expect them to pass:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/api/test_interview_api.py tests/services/test_interview_session_service.py tests/schemas/test_interview_schema.py
cd "/home/eddiesngu/Desktop/Dang/interviewx/worker" && uv run pytest -q tests/test_backend_client.py tests/test_agent_smoke.py tests/test_gemini_live.py
cd "/home/eddiesngu/Desktop/Dang/interviewx/frontend" && pnpm vitest run src/components/interview/candidate-join.test.tsx src/app/dashboard/interviews/session-page.test.tsx && pnpm tsc --noEmit
```

## Golden path

1. Open one completed screening in the HR dashboard.
2. Publish an interview with a non-empty opening question.
3. Open the share link in a second browser session.
4. Join the room with microphone allowed.
5. Confirm the AI opening question plays as room audio.
6. Speak one answer and confirm the AI replies once.
7. Refresh the HR session page and confirm transcript turns appear.
