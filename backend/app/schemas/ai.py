"""Schemas for the bring-your-own-key AI endpoints."""

from typing import Literal

from pydantic import BaseModel, Field


class AIKeyCheckIn(BaseModel):
    """A visitor's provider + key to verify. The key is used once and never stored."""

    provider: Literal["anthropic", "openai", "gemini"]
    api_key: str = Field(min_length=8, max_length=512)


class AIModelOption(BaseModel):
    id: str
    label: str


class AIKeyCheckOut(BaseModel):
    """The chat models this key can use, plus the one we suggest pre-selecting."""

    provider: Literal["anthropic", "openai", "gemini"]
    models: list[AIModelOption]
    recommended: str | None
