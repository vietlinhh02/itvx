import httpx
from pydantic import BaseModel


class WorkerDispatchResponse(BaseModel):
    accepted: bool
    session_id: str
    status: str


class InterviewWorkerLauncher:
    def __init__(self, service_url: str, timeout_seconds: float) -> None:
        self._service_url = service_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    async def launch(
        self,
        *,
        session_id: str,
        room_name: str,
        opening_question: str,
        worker_token: str,
        jd_id: str,
    ) -> WorkerDispatchResponse:
        payload = {
            "session_id": session_id,
            "room_name": room_name,
            "opening_question": opening_question,
            "worker_token": worker_token,
            "jd_id": jd_id,
        }
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            response = await client.post(f"{self._service_url}/dispatch-session", json=payload)
            response.raise_for_status()
        return WorkerDispatchResponse.model_validate(response.json())
