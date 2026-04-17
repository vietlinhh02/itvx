import httpx


class BackendClient:
    def __init__(self, base_url: str, callback_secret: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._callback_secret = callback_secret
        self._client = httpx.AsyncClient(
            headers={"X-Worker-Callback-Secret": self._callback_secret},
            timeout=httpx.Timeout(10.0, connect=5.0),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )

    def turns_endpoint(self, session_id: str) -> str:
        return f"{self._base_url}/api/v1/interviews/sessions/{session_id}/turns"

    def runtime_events_endpoint(self, session_id: str) -> str:
        return f"{self._base_url}/api/v1/interviews/sessions/{session_id}/runtime-events"

    def complete_endpoint(self, session_id: str) -> str:
        return f"{self._base_url}/api/v1/interviews/sessions/{session_id}/complete"

    def expire_reconnect_endpoint(self, session_id: str) -> str:
        return f"{self._base_url}/api/v1/interviews/sessions/{session_id}/expire-reconnect"

    def knowledge_query_endpoint(self, session_id: str) -> str:
        return f"{self._base_url}/api/v1/interviews/sessions/{session_id}/knowledge-query"

    def runtime_state_endpoint(self, session_id: str) -> str:
        return f"{self._base_url}/api/v1/interviews/sessions/{session_id}/runtime-state"

    def build_turn_payload(
        self,
        speaker: str,
        sequence_number: int,
        transcript_text: str,
        provider_event_id: str | None,
    ) -> dict[str, object]:
        return {
            "speaker": speaker,
            "sequence_number": sequence_number,
            "transcript_text": transcript_text,
            "provider_event_id": provider_event_id,
            "event_payload": {},
        }

    def build_runtime_event_payload(
        self,
        event_type: str,
        event_source: str,
        session_status: str | None,
        worker_status: str | None,
        provider_status: str | None,
        payload: dict[str, object],
    ) -> dict[str, object]:
        return {
            "event_type": event_type,
            "event_source": event_source,
            "session_status": session_status,
            "worker_status": worker_status,
            "provider_status": provider_status,
            "payload": payload,
        }

    async def aclose(self) -> None:
        await self._client.aclose()

    async def post_turn(self, session_id: str, payload: dict[str, object]) -> None:
        response = await self._client.post(self.turns_endpoint(session_id), json=payload)
        response.raise_for_status()

    async def post_runtime_event(self, session_id: str, payload: dict[str, object]) -> None:
        response = await self._client.post(self.runtime_events_endpoint(session_id), json=payload)
        response.raise_for_status()

    async def complete_session(self, session_id: str, payload: dict[str, object]) -> None:
        response = await self._client.post(self.complete_endpoint(session_id), json=payload)
        response.raise_for_status()

    async def expire_reconnect(self, session_id: str) -> None:
        response = await self._client.post(self.expire_reconnect_endpoint(session_id))
        response.raise_for_status()

    async def query_company_knowledge(self, session_id: str, query: str) -> dict[str, object]:
        response = await self._client.post(
            self.knowledge_query_endpoint(session_id),
            json={"query": query},
        )
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, dict) else {"query": query, "citations": []}

    async def get_runtime_state(self, session_id: str) -> dict[str, object]:
        response = await self._client.get(self.runtime_state_endpoint(session_id))
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, dict) else {"session_id": session_id}
