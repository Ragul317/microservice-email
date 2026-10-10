"""Environment-based configuration for the Email Microservice.

Values come from environment variables, optionally loaded from email-service/.env.
SMTP credentials are never hardcoded and never logged.
"""
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def _bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    smtp_from: str
    smtp_use_ssl: bool
    smtp_timeout: float
    log_level: str

    def missing_fields(self) -> list[str]:
        required = {
            "SMTP_HOST": self.smtp_host,
            "SMTP_USERNAME": self.smtp_username,
            "SMTP_PASSWORD": self.smtp_password,
            "SMTP_FROM": self.smtp_from,
        }
        return [name for name, value in required.items() if not value]


def get_settings() -> Settings:
    """Read settings from the environment on every call (cheap, and test-friendly)."""
    return Settings(
        smtp_host=os.getenv("SMTP_HOST", "").strip(),
        smtp_port=int(os.getenv("SMTP_PORT", "").strip() or 587),
        smtp_username=os.getenv("SMTP_USERNAME", "").strip(),
        smtp_password=os.getenv("SMTP_PASSWORD", "").strip(),
        smtp_from=os.getenv("SMTP_FROM", "").strip(),
        smtp_use_ssl=_bool(os.getenv("SMTP_USE_SSL", "false")),
        smtp_timeout=float(os.getenv("SMTP_TIMEOUT", "").strip() or 10),
        log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper() or "INFO",
    )
