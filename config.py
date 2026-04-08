import os
import json
import tempfile
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


def _resolve_credentials() -> str:
    """
    Supports two formats for GOOGLE_CREDENTIALS_JSON:
      1. A file path (local dev): "credentials.json"
      2. Raw JSON content (Render.com env var): '{"type": "service_account", ...}'
    """
    raw = os.getenv("GOOGLE_CREDENTIALS_JSON", "credentials.json")
    if raw.strip().startswith("{"):
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        )
        json.dump(json.loads(raw), tmp)
        tmp.close()
        return tmp.name
    return raw


@dataclass
class Config:
    BOT_TOKEN: str = field(default_factory=lambda: os.getenv("BOT_TOKEN", ""))
    ADMIN_ID: int = field(default_factory=lambda: int(os.getenv("ADMIN_ID", "0")))
    GOOGLE_SHEET_ID: str = field(default_factory=lambda: os.getenv("GOOGLE_SHEET_ID", ""))
    GOOGLE_CREDENTIALS_JSON: str = field(default_factory=_resolve_credentials)
    GROUP_ID: int = field(default_factory=lambda: int(os.getenv("GROUP_ID", "0")))
    WEBHOOK_URL: str = field(default_factory=lambda: os.getenv("WEBHOOK_URL", ""))
    PORT: int = field(default_factory=lambda: int(os.getenv("PORT", "8443")))

    def validate(self) -> None:
        missing = []
        if not self.BOT_TOKEN:
            missing.append("BOT_TOKEN")
        if not self.ADMIN_ID:
            missing.append("ADMIN_ID")
        if missing:
            raise ValueError(f"Missing required env vars: {', '.join(missing)}")


config = Config()
