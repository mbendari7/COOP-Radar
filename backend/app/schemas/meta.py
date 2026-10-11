"""Schemas for public app metadata."""

from pydantic import BaseModel


class PublicConfig(BaseModel):
    """What the UI should show: demo button, AI features, and the daily AI allowance."""

    demo_enabled: bool
    # True only when both the Anthropic and OpenAI keys are configured on the server
    ai_enabled: bool
    # AI actions (resume uploads + questions) per user per day; 0 = unlimited
    ai_daily_limit: int
