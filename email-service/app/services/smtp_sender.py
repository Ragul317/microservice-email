"""SMTP sending. The only place in the whole project that talks SMTP."""
import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formatdate, make_msgid

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


class EmailSendError(Exception):
    """Base error. `public_message` is safe to return to callers; str(exc) is for logs only."""

    status_code = 502
    public_message = "Email sending failed"


class SMTPConfigError(EmailSendError):
    status_code = 500
    public_message = "Email service is not configured"


class SMTPConnectionError(EmailSendError):
    status_code = 503
    public_message = "Could not connect to email provider"


class SMTPAuthError(EmailSendError):
    status_code = 502
    public_message = "Email provider authentication failed"


class SMTPRecipientError(EmailSendError):
    status_code = 400
    public_message = "Recipient address was rejected"


class SMTPSendError(EmailSendError):
    pass


def build_message(settings: Settings, to: str, subject: str, body: str) -> EmailMessage:
    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = to
    message["Subject"] = subject
    message["Date"] = formatdate(localtime=True)
    message["Message-ID"] = make_msgid()
    message.set_content(body)
    return message


def send_email(to: str, subject: str, body: str, settings: Settings | None = None) -> None:
    settings = settings or get_settings()

    missing = settings.missing_fields()
    if missing:
        raise SMTPConfigError(f"Missing SMTP settings: {', '.join(missing)}")

    message = build_message(settings, to, subject, body)
    tls_context = ssl.create_default_context()

    try:
        if settings.smtp_use_ssl:
            server = smtplib.SMTP_SSL(
                settings.smtp_host, settings.smtp_port, timeout=settings.smtp_timeout, context=tls_context
            )
        else:
            server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=settings.smtp_timeout)
    except OSError as exc:  # refused, DNS failure, timeout, SMTPConnectError, SSL errors
        raise SMTPConnectionError(f"Connect to {settings.smtp_host}:{settings.smtp_port} failed: {exc!r}") from exc

    # Note: smtplib.SMTPException subclasses OSError, so the specific SMTP errors must come first.
    try:
        with server:
            if not settings.smtp_use_ssl:
                server.starttls(context=tls_context)
            server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(message)
    except smtplib.SMTPAuthenticationError as exc:
        raise SMTPAuthError(f"SMTP authentication failed: {exc.smtp_code}") from exc
    except smtplib.SMTPRecipientsRefused as exc:
        raise SMTPRecipientError("SMTP server refused the recipient") from exc
    except smtplib.SMTPException as exc:
        raise SMTPSendError(f"SMTP error while sending: {exc!r}") from exc
    except OSError as exc:  # connection dropped / timed out mid-session
        raise SMTPConnectionError(f"SMTP connection error while sending: {exc!r}") from exc
