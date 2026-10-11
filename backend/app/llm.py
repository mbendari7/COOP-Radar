"""
Shared helpers for every Claude call in the backend.

Keeping client construction in one place means model names and the API key come
from settings (never hard-coded), and tests can patch `anthropic.AsyncAnthropic`
once to cover every caller.
"""

import json
import re
from typing import Any

import anthropic

from app.config import get_settings


def get_client() -> anthropic.AsyncAnthropic:
    """
    Build an async Anthropic client.

    An empty ANTHROPIC_API_KEY passes None so the SDK falls back to its normal
    credential resolution (env var, `ant auth login` profile, etc.).
    """
    return anthropic.AsyncAnthropic(api_key=get_settings().anthropic_api_key or None)


def response_text(message: Any) -> str:
    """
    Join the text blocks of a Messages API response.

    Current models think by default, so content[0] is often a thinking block
    rather than text — never index content[0].text directly.
    """
    parts = [getattr(block, "text", None) for block in getattr(message, "content", None) or []]
    return "".join(p for p in parts if isinstance(p, str))


def parse_json(raw: str) -> Any:
    """
    Parse JSON from a model reply, tolerating ```json fences or surrounding prose.
    Raises ValueError if no JSON value can be recovered.
    """
    text = raw.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Fall back to the outermost array or object in the reply
    for open_ch, close_ch in (("[", "]"), ("{", "}")):
        start, end = text.find(open_ch), text.rfind(close_ch)
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                continue
    raise ValueError("No JSON found in model response")
