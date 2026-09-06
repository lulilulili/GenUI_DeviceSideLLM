import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    provider: str = "ollama"
    model: str = "qwen2.5:3b"
    base_url: str = "http://127.0.0.1:11434"
    api_key: str = ""
    timeout: float = 60.0
    response_mode: str = "json_schema"

    @classmethod
    def from_env(cls) -> "Settings":
        provider = os.getenv("GENUI_PROVIDER", "ollama")
        default_url = (
            "http://127.0.0.1:11434"
            if provider == "ollama"
            else "http://127.0.0.1:8080/v1"
        )
        return cls(
            provider=provider,
            model=os.getenv("GENUI_MODEL", "qwen2.5:3b"),
            base_url=os.getenv("GENUI_BASE_URL", default_url).rstrip("/"),
            api_key=os.getenv("GENUI_API_KEY", ""),
            timeout=float(os.getenv("GENUI_TIMEOUT", "60")),
        )
