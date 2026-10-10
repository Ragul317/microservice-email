"""Client for the Email Microservice. The Main Backend never talks SMTP itself."""
import logging

import httpx

from app.utils import mask_email

logger = logging.getLogger(__name__)


class EmailServiceError(Exception):
    """The Email Microservice could not send the email. `public_message` is safe for the frontend."""

    status_code = 502

    def __init__(self, public_message: str = "Email sending failed"):
        super().__init__(public_message)
        self.public_message = public_message


class EmailServiceUnavailable(EmailServiceError):
    status_code = 503

    def __init__(self):
        super().__init__("Email service is unavailable. Please try again later.")


class EmailServiceTimeout(EmailServiceError):
    status_code = 504

    def __init__(self):
        super().__init__("Email service timed out. Please try again later.")


async def send_email(client: httpx.AsyncClient, to: str, subject: str, message: str) -> None:
    """POST {to, subject, body} to the Email Microservice's /send-email. Raises EmailServiceError on failure."""
    payload = {"to": to, "subject": subject, "body": message}
    recipient = mask_email(to)

    logger.info("Calling email service %s/send-email for %s", client.base_url, recipient)
    try:
        response = await client.post("/send-email", json=payload)
    except httpx.TimeoutException as exc:
        logger.error("Email service timed out for %s: %r", recipient, exc)
        raise EmailServiceTimeout() from exc
    except httpx.TransportError as exc:  # connection refused, DNS failure, network errors
        logger.error("Email service unavailable for %s: %r", recipient, exc)
        raise EmailServiceUnavailable() from exc

    try:
        data = response.json()
    except ValueError:
        data = None

    if response.is_success and isinstance(data, dict) and data.get("success") is True:
        return

    upstream_message = data.get("message") if isinstance(data, dict) else None
    logger.error(
        "Email service returned an error for %s: HTTP %s %s", recipient, response.status_code, upstream_message
    )
    # The Email Microservice only returns generic, user-safe messages, so they can be forwarded.
    if isinstance(upstream_message, str) and upstream_message:
        raise EmailServiceError(upstream_message)
    raise EmailServiceError()
