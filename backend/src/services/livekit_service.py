import logging
import re
import string
from secrets import choice, token_urlsafe

from livekit import api

from src.config import settings


logger = logging.getLogger(__name__)


class LiveKitService:
    def build_room_name(self, candidate_name: str | None = None) -> str:
        normalized = re.sub(r"[^a-z0-9]+", "-", (candidate_name or "").strip().lower()).strip("-")
        readable_name = normalized[:32] or "candidate"
        return f"{settings.livekit_room_prefix}-{readable_name}-{self._build_short_token(6)}"

    def build_share_token(self) -> str:
        return self._build_short_token(8)

    def build_worker_dispatch_token(self) -> str:
        return token_urlsafe(24)

    def _build_short_token(self, length: int) -> str:
        alphabet = string.ascii_lowercase + string.digits
        return "".join(choice(alphabet) for _ in range(length))

    def create_candidate_identity(self, session_id: str, candidate_name: str) -> str:
        normalized = re.sub(r"[^a-z0-9]+", "-", candidate_name.strip().lower()).strip("-")
        safe_name = normalized[:48] or "guest"
        return f"candidate-{session_id}-{safe_name}"

    def create_worker_identity(self, session_id: str) -> str:
        return f"worker-{session_id}"

    def create_candidate_token(self, room_name: str, identity: str) -> str:
        return (
            api.AccessToken(settings.livekit_api_key, settings.livekit_api_secret)
            .with_identity(identity)
            .with_grants(
                api.VideoGrants(
                    room_join=True,
                    room=room_name,
                    can_publish=True,
                    can_subscribe=True,
                )
            )
            .to_jwt()
        )

    def create_worker_token(self, room_name: str, identity: str) -> str:
        return (
            api.AccessToken(settings.livekit_api_key, settings.livekit_api_secret)
            .with_identity(identity)
            .with_grants(
                api.VideoGrants(
                    room_join=True,
                    room=room_name,
                    can_publish=True,
                    can_subscribe=True,
                )
            )
            .to_jwt()
        )

    async def delete_room(self, room_name: str) -> None:
        if not settings.livekit_api_key or not settings.livekit_api_secret:
            logger.warning("skipping room deletion for %s because LiveKit credentials are missing", room_name)
            return

        async with api.LiveKitAPI(
            url=settings.livekit_url,
            api_key=settings.livekit_api_key,
            api_secret=settings.livekit_api_secret,
        ) as livekit_api:
            await livekit_api.room.delete_room(api.DeleteRoomRequest(room=room_name))
