import smtplib

import pytest
from fastapi.testclient import TestClient

from app.main import app

SMTP_ENV = {
    "SMTP_HOST": "smtp.test.local",
    "SMTP_PORT": "587",
    "SMTP_USERNAME": "sender@test.local",
    "SMTP_PASSWORD": "not-a-real-password",
    "SMTP_FROM": "sender@test.local",
    "SMTP_USE_SSL": "false",
    "SMTP_TIMEOUT": "5",
}


@pytest.fixture(autouse=True)
def smtp_env(monkeypatch):
    """Deterministic fake SMTP config; overrides any real .env values."""
    for key, value in SMTP_ENV.items():
        monkeypatch.setenv(key, value)


@pytest.fixture
def client():
    # raise_server_exceptions=False so 500 handlers can be asserted like a real client would see them.
    return TestClient(app, raise_server_exceptions=False)


class FakeSMTPBase:
    """Stands in for smtplib.SMTP / SMTP_SSL. No network. Records calls; can fail at a chosen step."""

    fail_on: str | None = None
    instances: list

    def __init__(self, host, port, timeout=None, context=None):
        if self.fail_on == "connect":
            raise ConnectionRefusedError("connection refused")
        self.host, self.port, self.timeout = host, port, timeout
        self.calls: list[str] = []
        self.sent: list = []
        type(self).instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.calls.append("quit")
        return False

    def starttls(self, context=None):
        self.calls.append("starttls")

    def login(self, username, password):
        self.calls.append("login")
        if self.fail_on == "login":
            raise smtplib.SMTPAuthenticationError(535, b"5.7.8 Username and Password not accepted")

    def send_message(self, message):
        self.calls.append("send_message")
        if self.fail_on == "send":
            raise smtplib.SMTPDataError(554, b"Message rejected")
        if self.fail_on == "recipient":
            raise smtplib.SMTPRecipientsRefused({message["To"]: (550, b"No such user")})
        if self.fail_on == "disconnect":
            raise TimeoutError("timed out")
        if self.fail_on == "unexpected":
            raise RuntimeError("boom: internal detail")
        self.sent.append(message)


@pytest.fixture
def fake_smtp(monkeypatch):
    """Returns a factory: fake_smtp(fail_on=None) -> fake class patched over smtplib.SMTP and SMTP_SSL."""

    def install(fail_on: str | None = None):
        fake = type("FakeSMTP", (FakeSMTPBase,), {"fail_on": fail_on, "instances": []})
        monkeypatch.setattr(smtplib, "SMTP", fake)
        monkeypatch.setattr(smtplib, "SMTP_SSL", fake)
        return fake

    return install
