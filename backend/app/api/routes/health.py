from fastapi import APIRouter

from app import __version__
from app.api.dependencies import SettingsDep
from app.models.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health(settings: SettingsDep) -> HealthResponse:
    return HealthResponse(status="ok", version=__version__, environment=settings.environment)
