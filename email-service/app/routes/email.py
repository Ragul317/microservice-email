import logging

from fastapi import APIRouter

from app.errors import error_response
from app.schemas.email import SendEmailRequest, SendEmailResponse
from app.services import smtp_sender
from app.utils import mask_email

logger = logging.getLogger(__name__)

router = APIRouter(tags=["email"])

ERROR_RESPONSES = {
    400: {"description": "Recipient rejected by SMTP server"},
    422: {"description": "Validation failed"},
    500: {"description": "SMTP not configured or unexpected error"},
    502: {"description": "SMTP authentication or sending failed"},
    503: {"description": "Could not connect to SMTP server"},
}


# Sync `def` on purpose: smtplib is blocking, so FastAPI runs this in its threadpool.
@router.post("/send-email", response_model=SendEmailResponse, responses=ERROR_RESPONSES)
def send_email(payload: SendEmailRequest):
    recipient = mask_email(payload.to)
    logger.info("Send-email request received for %s", recipient)

    try:
        smtp_sender.send_email(payload.to, payload.subject, payload.body)
    except smtp_sender.EmailSendError as exc:
        # Details go to the log only; the caller gets a generic, safe message.
        logger.error("Email sending failed for %s [%s]: %s", recipient, type(exc).__name__, exc)
        return error_response(exc.status_code, exc.public_message)
    except Exception:
        logger.exception("Unexpected error while sending email to %s", recipient)
        return error_response(500, "Internal server error")

    logger.info("Email sent to %s", recipient)
    return SendEmailResponse(success=True, message="Email sent successfully")
