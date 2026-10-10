import logging

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from app.config import get_settings
from app.errors import unhandled_exception_handler, validation_exception_handler
from app.routes import email, health

settings = get_settings()
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s %(levelname)s [email-service] %(name)s: %(message)s",
)

# Internal service: no CORS on purpose -- browsers must never call it directly.
app = FastAPI(
    title="Email Microservice",
    description="Sends emails over SMTP. Internal service, called by the Main Backend.",
    version="1.0.0",
)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

app.include_router(health.router)
app.include_router(email.router)
