from fastapi import APIRouter

from app.schemas.email import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    # Liveness only: deliberately does not touch SMTP.
    return HealthResponse(status="healthy")
