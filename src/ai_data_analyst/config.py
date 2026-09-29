import os
from dataclasses import dataclass

from dotenv import load_dotenv


def _parse_int(name: str, default: int, minimum: int = 1) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        return max(int(raw), minimum)
    except ValueError:
        return default


def _parse_float(name: str, default: float, minimum: float = 0.1) -> float:
    raw = os.getenv(name, str(default)).strip()
    try:
        return max(float(raw), minimum)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    """Runtime configuration loaded from environment variables."""

    openai_api_key: str
    openai_model: str = "gpt-4o-mini"
    max_result_rows: int = 1_000
    max_prompt_rows: int = 50
    max_preview_rows: int = 200
    max_upload_bytes: int = 50_000_000
    openai_timeout_seconds: float = 60.0

    @classmethod
    def from_environment(cls) -> "Settings":
        load_dotenv()
        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini",
            max_result_rows=_parse_int("MAX_RESULT_ROWS", 1_000),
            max_prompt_rows=_parse_int("MAX_PROMPT_ROWS", 50),
            max_preview_rows=_parse_int("MAX_PREVIEW_ROWS", 200),
            max_upload_bytes=_parse_int("MAX_UPLOAD_BYTES", 50_000_000),
            openai_timeout_seconds=_parse_float("OPENAI_TIMEOUT_SECONDS", 60.0),
        )

    def require_openai(self) -> None:
        if not self.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured. Add it to .env and restart Streamlit.")
