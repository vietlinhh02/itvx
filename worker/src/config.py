from pydantic import BaseModel


class WorkerConfig(BaseModel):
    backend_base_url: str = "http://localhost:8000"
    backend_callback_secret: str = "change-me"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash-native-audio"
    livekit_url: str = "wss://your-project.livekit.cloud"
    worker_host: str = "127.0.0.1"
    worker_port: int = 8765
