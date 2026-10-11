"""Public, unauthenticated app configuration the frontend needs to render (e.g. the demo button)."""

from fastapi import APIRouter

from app.config import get_settings
from app.schemas.meta import PublicConfig

router = APIRouter(tags=["meta"])


@router.get("/config", response_model=PublicConfig)
async def public_config() -> PublicConfig:
    """Feature flags for the UI. Never includes secrets — only whether features are on."""
    settings = get_settings()
    return PublicConfig(
        demo_enabled=settings.demo_enabled,
        ai_enabled=bool(settings.anthropic_api_key and settings.openai_api_key),
        ai_daily_limit=settings.ai_daily_limit,
    )
