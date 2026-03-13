"""
Health / readiness endpoint.
"""

from datetime import datetime, timezone

from fastapi import APIRouter

from app.core.config import settings
from app.schemas.responses import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check():
    """Basic health check — always returns 200 if the server is up."""
    from app.main import app_state

    return HealthResponse(
        status="healthy" if app_state.datasets_loaded else "degraded",
        model_configured=settings.has_openai_key,
        datasets_loaded=app_state.datasets_loaded,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
