"""Schemas for public app metadata."""

from pydantic import BaseModel


class PublicConfig(BaseModel):
    """What the UI should show. Never includes secrets — only which features are on."""

    demo_enabled: bool
    # True when the site owner set ANTHROPIC_API_KEY: visitors without their own key can
    # still use AI features (within ai_daily_limit). Otherwise visitors bring their own key.
    server_ai_enabled: bool
    # True when the site owner set OPENAI_API_KEY: smart (semantic) search + similar postings
    semantic_search_enabled: bool
    # AI actions per user per day on the owner's key; 0 = unlimited. Own keys are never limited.
    ai_daily_limit: int
