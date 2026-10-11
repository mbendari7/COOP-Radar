"""
Bring-your-own-key AI: one interface over Claude (Anthropic), ChatGPT (OpenAI), and Gemini (Google).

How keys flow
-------------
The browser stores the visitor's key and sends it with each AI request in headers:
    X-AI-Provider: anthropic | openai | gemini
    X-AI-Key:      the visitor's API key
    X-AI-Model:    model id chosen in the UI (optional for anthropic/gemini)
The server forwards it to that provider for this one request. It is never stored, logged,
or put in error messages. If a request has no key and the site owner configured their own
ANTHROPIC_API_KEY, the owner's key is used instead (with the daily AI limit).

Public surface
--------------
credentials_from_headers()  -> AICredentials (user key, or server fallback, or 400)
complete(creds, system, user)          -> full text reply
stream(creds, system, user)            -> async iterator of text chunks
list_models(provider, api_key)         -> chat models the key can use (for "Check key")
"""

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Literal

from fastapi import Header, HTTPException, status

from app.config import get_settings

Provider = Literal["anthropic", "openai", "gemini"]
PROVIDERS: tuple[Provider, ...] = ("anthropic", "openai", "gemini")

# Used when the browser doesn't send a model. OpenAI has no default: the UI always sends one
# chosen from the key's own model list, so it never goes stale.
DEFAULT_MODELS: dict[Provider, str | None] = {
    "anthropic": "claude-opus-5-5",
    "gemini": "gemini-flash-latest",
    "openai": None,
}

_MAX_KEY_LENGTH = 512


@dataclass(frozen=True)
class AICredentials:
    provider: Provider
    api_key: str = field(repr=False)  # never printed in logs or tracebacks
    model: str
    # "user" = the visitor's own key (no limits); "server" = the site owner's key (daily limit)
    source: Literal["user", "server"]


class AIProviderError(Exception):
    """A provider call failed in a way the user should hear about (bad key, rate limit)."""

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
    Resolve which AI account to use for this request.
    Raises 400 AI_KEY_REQUIRED when the visitor sent no key and the site has none either.
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


# ── Error translation ─────────────────────────────────────────────────────────

_PROVIDER_NAMES = {"anthropic": "Claude (Anthropic)", "openai": "OpenAI", "gemini": "Gemini"}


def _translate(provider: Provider, exc: Exception) -> AIProviderError:
    """Map each SDK's errors to one of three user-facing outcomes. Never echoes the key."""
    name = _PROVIDER_NAMES[provider]
    status_code = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    # Google answers a bad key with 400 INVALID_ARGUMENT + reason API_KEY_INVALID, not 401
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


# ── Calls ─────────────────────────────────────────────────────────────────────


async def complete(creds: AICredentials, system: str, user: str, max_tokens: int = 8000) -> str:
    """One request, full text reply."""
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
    except Exception as exc:  # noqa: BLE001 — every SDK has its own error classes
        raise _translate(creds.provider, exc) from exc


async def stream(
    creds: AICredentials, system: str, user: str, max_tokens: int = 4000
) -> AsyncIterator[str]:
    """Yield the reply as it is generated."""
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


# ── Key check: which models can this key use? ───────────────────────────────

_OPENAI_CHAT_PREFIXES = ("gpt-", "o1", "o3", "o4", "chatgpt")
_OPENAI_EXCLUDE = ("audio", "realtime", "tts", "transcribe", "search", "image", "embedding",
                   "instruct", "moderation", "codex")
# Preferred defaults, best first: the first model id starting with one of these is pre-selected
_PREFERRED: dict[Provider, tuple[str, ...]] = {
    "anthropic": ("claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-5-5", "claude-"),
    "openai": ("gpt-5", "gpt-4.1", "gpt-4o", "gpt-"),
    "gemini": ("gemini-flash-latest", "gemini-2.5-flash", "gemini-"),
}


def recommended_model(provider: Provider, model_ids: list[str]) -> str | None:
    for prefix in _PREFERRED[provider]:
        # Shortest id with the prefix = the base model rather than a dated/variant snapshot
        matches = sorted((m for m in model_ids if m.startswith(prefix)), key=len)
        if matches:
            return matches[0]
    return model_ids[0] if model_ids else None


async def list_models(provider: Provider, api_key: str) -> list[dict[str, str]]:
    """Chat-capable models for this key as [{"id", "label"}]; AIProviderError on a bad key."""
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


# ── FastAPI dependency ────────────────────────────────────────────────────────


def ai_credentials(task: Literal["rank", "chat"], optional: bool = False) -> Any:
    """
    Dependency factory: `creds: AICredentials = Depends(ai_credentials("chat"))`.
    With optional=True the dependency yields None (instead of 400 AI_KEY_REQUIRED) when
    neither the visitor nor the site has a key, so the endpoint can use its free path.
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
