"""Shapes for the public site settings."""

from pydantic import BaseModel


class PublicConfig(BaseModel):
    """What the site should show. Never any secrets, just which features are on."""

    demo_enabled: bool
    # True when the owner set ANTHROPIC_API_KEY so people without a key can still use AI
    # up to ai_daily_limit. Otherwise visitors bring their own key
    server_ai_enabled: bool
    # True when the owner set OPENAI_API_KEY which turns on smart search and similar jobs
    semantic_search_enabled: bool
    # AI actions per person per day on the owner's key. 0 means no limit. Own keys never have one
    ai_daily_limit: int
