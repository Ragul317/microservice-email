"""Environment-based configuration for the Main Backend (optionally loaded from backend/.env)."""
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BACKEND_DIR.parent / "frontend"

load_dotenv(BACKEND_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    email_service_url: str
    email_service_timeout: float
    cors_origins: list[str]
    log_level: str


def get_settings() -> Settings:
    origins = os.getenv("CORS_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000")
    return Settings(
        email_service_url=os.getenv("EMAIL_SERVICE_URL", "http://localhost:8001").strip().rstrip("/"),
        email_service_timeout=float(os.getenv("EMAIL_SERVICE_TIMEOUT", "").strip() or 20),
        cors_origins=[origin.strip() for origin in origins.split(",") if origin.strip()],
        log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper() or "INFO",
    )
