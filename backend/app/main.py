import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import FRONTEND_DIR, get_settings
from app.errors import unhandled_exception_handler, validation_exception_handler
from app.routes import health, send

settings = get_settings()
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s %(levelname)s [backend] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # One pooled client for all calls to the Email Microservice, with explicit timeouts.
    app.state.http_client = httpx.AsyncClient(
        base_url=settings.email_service_url,
        timeout=httpx.Timeout(settings.email_service_timeout, connect=5.0),
    )
    logger.info("Email service URL: %s", settings.email_service_url)
    yield
    await app.state.http_client.aclose()


app = FastAPI(
    title="Main Backend",
    description="Application API. Sends emails by calling the Email Microservice.",
    version="1.0.0",
    lifespan=lifespan,
)

# Explicit origins only (no "*"). The frontend is same-origin anyway; this covers local dev setups.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

app.include_router(health.router)
app.include_router(send.router)

# Serve the frontend at "/". Mounted last so the API routes above take precedence.
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
