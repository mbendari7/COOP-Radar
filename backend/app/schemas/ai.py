"""Shapes for the AI key endpoints."""

from typing import Literal

from pydantic import BaseModel, Field


class AIKeyCheckIn(BaseModel):
    """A visitor's provider and key to check. The key is used once and never saved."""

    provider: Literal["anthropic", "openai", "gemini"]
    api_key: str = Field(min_length=8, max_length=512)


class AIModelOption(BaseModel):
    id: str
    label: str


class AIKeyCheckOut(BaseModel):
    """The chat models this key can use plus the one we suggest picking."""

    provider: Literal["anthropic", "openai", "gemini"]
    models: list[AIModelOption]
    recommended: str | None
