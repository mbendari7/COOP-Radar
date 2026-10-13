"""Public settings the site needs to draw itself, like whether to show the demo button."""

from fastapi import APIRouter

from app.config import get_settings
from app.schemas.meta import PublicConfig

router = APIRouter(tags=["meta"])


@router.get("/config", response_model=PublicConfig)
async def public_config() -> PublicConfig:
    """Feature switches for the site. Never any secrets, just whether things are on."""
    settings = get_settings()
    return PublicConfig(
        demo_enabled=settings.demo_enabled,
        server_ai_enabled=bool(settings.anthropic_api_key),
        semantic_search_enabled=bool(settings.openai_api_key),
        ai_daily_limit=settings.ai_daily_limit,
    )
