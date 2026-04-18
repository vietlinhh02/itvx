import hashlib
from pathlib import Path

from pydantic import BaseModel, model_validator


REPO_ROOT = Path(__file__).resolve().parents[2]


def _derive_local_secret(purpose: str) -> str:
    digest = hashlib.sha256(f"interviewx:{purpose}:{REPO_ROOT}".encode("utf-8")).hexdigest()
    return digest


class WorkerConfig(BaseModel):
    backend_base_url: str = "http://localhost:8000"
    backend_callback_secret: str = ""
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash-native-audio"
    livekit_url: str = "wss://your-project.livekit.cloud"
    worker_host: str = "127.0.0.1"
    worker_port: int = 8765

    @model_validator(mode="after")
    def populate_local_secret(self) -> "WorkerConfig":
        if not self.backend_callback_secret:
            self.backend_callback_secret = _derive_local_secret("worker-callback")
        return self
