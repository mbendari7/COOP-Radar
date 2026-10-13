"""
AI with the visitor's own key. One way to talk to Claude, ChatGPT and Gemini.

How keys move
The browser keeps the visitor's key and sends it with each AI request in these headers
    X-AI-Provider  anthropic or openai or gemini
    X-AI-Key       the visitor's API key
    X-AI-Model     the model picked on the AI key page
We pass it to that provider for this one request and that is it. It is never saved,
logged or shown in an error. If there is no key and the site owner set ANTHROPIC_API_KEY
we use the owner's key instead and the daily AI limit applies.

What lives here
credentials_from_headers  picks the key to use or answers 400
complete                  gets the whole reply at once
stream                    gets the reply piece by piece
list_models               lists the chat models a key can use for Check key
"""

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Literal

from fastapi import Header, HTTPException, status

from app.config import get_settings

Provider = Literal["anthropic", "openai", "gemini"]
PROVIDERS: tuple[Provider, ...] = ("anthropic", "openai", "gemini")

# Used when the browser sends no model. OpenAI has none on purpose because the page always
# sends one from the key's own model list so it never goes out of date
DEFAULT_MODELS: dict[Provider, str | None] = {
    "anthropic": "claude-opus-5-5",
    "gemini": "gemini-flash-latest",
    "openai": None,
}

_MAX_KEY_LENGTH = 512


@dataclass(frozen=True)
class AICredentials:
    provider: Provider
    api_key: str = field(repr=False)  # never shows up in logs or tracebacks
    model: str
    # user is the visitor's own key with no limit and server is the owner's key with a daily cap
    source: Literal["user", "server"]


class AIProviderError(Exception):
    """A provider call failed in a way the visitor should hear about, like a bad key."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message

    def to_http(self) -> HTTPException:
        return HTTPException(
            status_code=self.status_code, detail={"detail": self.message, "code": self.code}
        )


def _bad_request(code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail={"detail": message, "code": code}
    )


def credentials_from_headers(
    provider: str | None,
    api_key: str | None,
    model: str | None,
    task: Literal["rank", "chat"],
) -> AICredentials:
    """
    Work out which AI account to use for this request.
    Answers 400 AI_KEY_REQUIRED when the visitor sent no key and the site has none either.
    """
    if api_key:
        if provider not in PROVIDERS:
            raise _bad_request("AI_PROVIDER_INVALID", "Choose Claude, ChatGPT (OpenAI), or Gemini.")
        if len(api_key) > _MAX_KEY_LENGTH or any(c.isspace() for c in api_key.strip()):
            raise _bad_request("AI_KEY_INVALID", "That doesn't look like a valid API key.")
        chosen = (model or "").strip() or DEFAULT_MODELS[provider]
        if not chosen:
            raise _bad_request("AI_MODEL_REQUIRED", "Pick a model on the AI key page first.")
        return AICredentials(provider, api_key.strip(), chosen, "user")

    settings = get_settings()
    if settings.anthropic_api_key:
        server_model = settings.fast_model if task == "rank" else settings.agent_model
        return AICredentials("anthropic", settings.anthropic_api_key, server_model, "server")

    raise _bad_request(
        "AI_KEY_REQUIRED", "Add your own AI key (Claude, ChatGPT, or Gemini) to use AI features."
    )


# Turning provider errors into plain ones

_PROVIDER_NAMES = {"anthropic": "Claude (Anthropic)", "openai": "OpenAI", "gemini": "Gemini"}


def _translate(provider: Provider, exc: Exception) -> AIProviderError:
    """Turn each SDK's errors into one of three plain outcomes. Never repeats the key."""
    name = _PROVIDER_NAMES[provider]
    status_code = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    # Google answers a bad key with 400 INVALID_ARGUMENT and reason API_KEY_INVALID instead of 401
    bad_google_key = "API_KEY_INVALID" in str(getattr(exc, "details", "") or "")
    if status_code in (401, 403) or bad_google_key:
        return AIProviderError(
            400, "AI_KEY_INVALID", f"{name} rejected the API key. Check it and try again."
        )
    if status_code == 404:
        return AIProviderError(
            400, "AI_MODEL_INVALID", f"{name} doesn't offer that model to this key."
        )
    if status_code == 429:
        return AIProviderError(
            429, "AI_PROVIDER_RATE_LIMITED",
            f"{name} says this key is out of credit or over its rate limit.",
        )
    return AIProviderError(
        502, "AI_PROVIDER_ERROR", f"{name} returned an error. Try again shortly."
    )


# Calling the models


async def complete(creds: AICredentials, system: str, user: str, max_tokens: int = 8000) -> str:
    """One request and the whole reply."""
    try:
        if creds.provider == "anthropic":
            from app.llm import get_client, response_text

            message = await get_client(creds.api_key).messages.create(
                model=creds.model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            if getattr(message, "stop_reason", None) == "refusal":
                return ""
            return response_text(message)

        if creds.provider == "openai":
            import openai

            client = openai.AsyncOpenAI(api_key=creds.api_key)
            response = await client.chat.completions.create(
                model=creds.model,
                max_completion_tokens=max_tokens,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            )
            return response.choices[0].message.content or ""

        from google import genai
        from google.genai import types

        gclient = genai.Client(api_key=creds.api_key)
        gresponse = await gclient.aio.models.generate_content(
            model=creds.model,
            contents=user,
            config=types.GenerateContentConfig(
                system_instruction=system, max_output_tokens=max_tokens
            ),
        )
        return gresponse.text or ""
    except AIProviderError:
        raise
    except Exception as exc:  # noqa: BLE001 every SDK has its own error classes
        raise _translate(creds.provider, exc) from exc


async def stream(
    creds: AICredentials, system: str, user: str, max_tokens: int = 4000
) -> AsyncIterator[str]:
    """Hand back the reply bit by bit as it is written."""
    try:
        if creds.provider == "anthropic":
            from app.llm import get_client

            async with get_client(creds.api_key).messages.stream(
                model=creds.model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            ) as s:
                async for text in s.text_stream:
                    yield text
                final = await s.get_final_message()
                if getattr(final, "stop_reason", None) == "refusal":
                    yield "I can't help with that request."
            return

        if creds.provider == "openai":
            import openai

            client = openai.AsyncOpenAI(api_key=creds.api_key)
            chunks = await client.chat.completions.create(
                model=creds.model,
                max_completion_tokens=max_tokens,
                stream=True,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            )
            async for chunk in chunks:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
            return

        from google import genai
        from google.genai import types

        gclient = genai.Client(api_key=creds.api_key)
        gstream = await gclient.aio.models.generate_content_stream(
            model=creds.model,
            contents=user,
            config=types.GenerateContentConfig(
                system_instruction=system, max_output_tokens=max_tokens
            ),
        )
        async for gchunk in gstream:
            if gchunk.text:
                yield gchunk.text
    except AIProviderError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise _translate(creds.provider, exc) from exc


# Checking a key and which models it can use

_OPENAI_CHAT_PREFIXES = ("gpt-", "o1", "o3", "o4", "chatgpt")
_OPENAI_EXCLUDE = ("audio", "realtime", "tts", "transcribe", "search", "image", "embedding",
                   "instruct", "moderation", "codex")
# Our favourite defaults best first. The first model id that starts with one of these gets picked
_PREFERRED: dict[Provider, tuple[str, ...]] = {
    "anthropic": ("claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-5-5", "claude-"),
    "openai": ("gpt-5", "gpt-4.1", "gpt-4o", "gpt-"),
    "gemini": ("gemini-flash-latest", "gemini-2.5-flash", "gemini-"),
}


def recommended_model(provider: Provider, model_ids: list[str]) -> str | None:
    for prefix in _PREFERRED[provider]:
        # The shortest id with the prefix is the main model and not a dated snapshot
        matches = sorted((m for m in model_ids if m.startswith(prefix)), key=len)
        if matches:
            return matches[0]
    return model_ids[0] if model_ids else None


async def list_models(provider: Provider, api_key: str) -> list[dict[str, str]]:
    """Chat models this key can use as id and label pairs. Raises AIProviderError on a bad key."""
    try:
        models: list[dict[str, str]] = []
        if provider == "anthropic":
            from app.llm import get_client

            async for m in get_client(api_key).models.list(limit=100):
                models.append({"id": m.id, "label": getattr(m, "display_name", None) or m.id})
        elif provider == "openai":
            import openai

            async for om in openai.AsyncOpenAI(api_key=api_key).models.list():
                mid = om.id
                is_chat = mid.startswith(_OPENAI_CHAT_PREFIXES)
                if is_chat and not any(x in mid for x in _OPENAI_EXCLUDE):
                    models.append({"id": mid, "label": mid})
            models.sort(key=lambda m: m["id"])
        else:
            from google import genai

            pager: Any = await genai.Client(api_key=api_key).aio.models.list()
            async for gm in pager:
                if "generateContent" in (gm.supported_actions or []) and gm.name:
                    mid = gm.name.removeprefix("models/")
                    models.append({"id": mid, "label": gm.display_name or mid})
        return models
    except Exception as exc:  # noqa: BLE001
        raise _translate(provider, exc) from exc


# FastAPI dependency


def ai_credentials(task: Literal["rank", "chat"], optional: bool = False) -> Any:
    """
    Use it like this  creds: AICredentials = Depends(ai_credentials("chat"))
    With optional=True you get None instead of a 400 when nobody has a key
    so the endpoint can fall back to its free path.
    """

    def dependency(
        x_ai_provider: str | None = Header(default=None),
        x_ai_key: str | None = Header(default=None),
        x_ai_model: str | None = Header(default=None),
    ) -> AICredentials | None:
        if optional and not x_ai_key and not get_settings().anthropic_api_key:
            return None
        return credentials_from_headers(x_ai_provider, x_ai_key, x_ai_model, task)

    return dependency
