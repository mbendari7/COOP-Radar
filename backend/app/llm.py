"""
Small helpers shared by every Claude call in the backend.

Building the client in one place means model names and the API key always come
from settings and are never hard coded, and tests can patch `anthropic.AsyncAnthropic`
once to cover everyone.
"""

import json
import re
from typing import Any

import anthropic

from app.config import get_settings


def get_client(api_key: str | None = None) -> anthropic.AsyncAnthropic:
    """
    Build an async Anthropic client. Uses the visitor's own key when we have one (see app/ai.py)
    and otherwise the owner's ANTHROPIC_API_KEY. An empty server key passes None so the SDK
    looks for credentials the usual way, like the env var or an `ant auth login` profile.
    """
    return anthropic.AsyncAnthropic(api_key=api_key or get_settings().anthropic_api_key or None)


def response_text(message: Any) -> str:
    """
    Join up the text blocks from a Messages API reply.

    Newer models think first, so content[0] is often a thinking block
    and not text. Never read content[0].text directly.
    """
    parts = [getattr(block, "text", None) for block in getattr(message, "content", None) or []]
    return "".join(p for p in parts if isinstance(p, str))


def parse_json(raw: str) -> Any:
    """
    Read JSON out of a model reply even if it is wrapped in ```json fences or extra words.
    Raises ValueError if there is no JSON to be found.
    """
    text = raw.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Fall back to the outermost list or object in the reply
    for open_ch, close_ch in (("[", "]"), ("{", "}")):
        start, end = text.find(open_ch), text.rfind(close_ch)
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                continue
    raise ValueError("No JSON found in model response")
