"""
Check a visitor's own AI key and list the models it can use.

The key goes to the provider once to list models and is never saved or logged.
There is a per IP limit so nobody can use this to test stolen keys in bulk.
"""

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from app import ai
from app.schemas.ai import AIKeyCheckIn, AIKeyCheckOut, AIModelOption
from app.store import Store, get_store

router = APIRouter(prefix="/ai", tags=["ai"])

_CHECKS_PER_HOUR = 30


@router.post("/check", response_model=AIKeyCheckOut)
async def check_key(
    body: AIKeyCheckIn,
    request: Request,
    x_forwarded_for: str | None = Header(default=None),
    store: Store = Depends(get_store),
) -> AIKeyCheckOut:
    """Ask the provider if the key works. 400 AI_KEY_INVALID if not and 429 when over the limit."""
    ip = (x_forwarded_for or "").split(",")[0].strip() or (
        request.client.host if request.client else "unknown"
    )
    key = f"ai_check:{ip}"
    count = await store.incr(key)
    if count == 1:
        await store.expire(key, 3600)
    if count > _CHECKS_PER_HOUR:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"detail": "Too many key checks. Try again in an hour.", "code": "RATE_LIMITED"},
        )

    try:
        models = await ai.list_models(body.provider, body.api_key.strip())
    except ai.AIProviderError as exc:
        raise exc.to_http() from exc

    ids = [m["id"] for m in models]
    return AIKeyCheckOut(
        provider=body.provider,
        models=[AIModelOption(**m) for m in models],
        recommended=ai.recommended_model(body.provider, ids),
    )
