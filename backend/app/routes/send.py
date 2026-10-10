import logging

import httpx
from fastapi import APIRouter, Depends

from app.dependencies import get_http_client
from app.errors import error_response
from app.schemas.email import SendRequest, SendResponse
from app.services import email_client
from app.utils import mask_email

logger = logging.getLogger(__name__)

router = APIRouter(tags=["email"])

ERROR_RESPONSES = {
    422: {"description": "Validation failed"},
    500: {"description": "Unexpected error"},
    502: {"description": "Email Microservice failed to send the email"},
    503: {"description": "Email Microservice unavailable"},
    504: {"description": "Email Microservice timed out"},
}


@router.post("/send", response_model=SendResponse, responses=ERROR_RESPONSES)
async def send(payload: SendRequest, client: httpx.AsyncClient = Depends(get_http_client)):
    recipient = mask_email(payload.to)
    logger.info("Send request received for %s", recipient)

    try:
        await email_client.send_email(client, payload.to, payload.subject, payload.message)
    except email_client.EmailServiceError as exc:
        return error_response(exc.status_code, exc.public_message)
    except Exception:
        logger.exception("Unexpected error while sending email to %s", recipient)
        return error_response(500, "Internal server error")

    logger.info("Email sent via email service for %s", recipient)
    return SendResponse(success=True, message="Email sent successfully")
