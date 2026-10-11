---
name: api-conventions
description: CoopRadar backend conventions for FastAPI routers, Pydantic schemas, SQLAlchemy queries, errors, pagination/sorting, and pytest patterns. Use when writing or changing any backend endpoint, model, schema, service, or backend test.
---

# CoopRadar backend conventions

## Layering (one resource = four files)
- `app/api/<resource>.py` — thin router: declare deps, call the service, return. No queries here.
- `app/services/<resource>.py` — all business logic and SQL. Services own `await db.commit()`.
- `app/schemas/<resource>.py` — Pydantic v2 request/response models (`ConfigDict(from_attributes=True)` on outputs).
- `app/models/<table>.py` — SQLAlchemy 2.0 typed `Mapped[...]` models. Use `TIMESTAMP(timezone=True)` for datetimes and
  `sqlalchemy.dialects.postgresql.ARRAY` (not the generic ARRAY) so `.contains()` works.
- Register new routers in `app/main.py` under `prefix="/api"`.

## Errors — one shape everywhere
- Raise `HTTPException(status_code=..., detail={"detail": "Human message", "code": "SNAKE_CASE"})`.
- `app/main.py` flattens it, so clients always get `{"detail": "...", "code": "..."}`.
  Validation errors stay FastAPI's 422 list (frontend maps them to `VALIDATION_ERROR`).
- Chain causes: `raise HTTPException(...) from exc`.

## List endpoints
- Params: filters, `sort`, `order` (`asc|desc`), `page` (1-based), `page_size`.
- Validate query params with a Pydantic model: `params: Annotated[MyListParams, Query()]`.
  Query strings are text, so use `int` + a `field_validator` for allowed numeric values (a `Literal[10, 25, 50]`
  rejects `"10"`). Use `Literal[...]` for string enums like `sort`.
- Map `sort` through a whitelist dict of columns (`_SORT_MAP`); add `Model.id` as a tiebreaker for stable paging.
- Return `{items, total, page, page_size}`; compute `total` with `select(func.count()).select_from(stmt.subquery())`.
- Add a DB index for every new sortable/filterable column — declare it in the model's `__table_args__` AND the migration.

## Queries — never interpolate user input
- SQLAlchemy `select()` with ORM operators: `Posting.skills.contains(list_)` (array `@>`),
  `PostingEmbedding.embedding.cosine_distance(vec)` (pgvector `<=>`), `func.websearch_to_tsquery("english", q)`.
- `text()` is allowed only when the ORM can't express it, and only with bound params (`:name`).
  Cast params with `CAST(:x AS type)`, never `:x::type` (SQLAlchemy mis-parses the colon).
- An f-string inside `text()` is a bug, full stop.

## AI calls
- Never construct Anthropic/OpenAI clients inline. Use `app/llm.py` (`get_client`, `response_text`, `parse_json`)
  and `app/ingest/embed.py` (`generate_embedding`). Model names come from settings (see the agent-tools skill).
- AI failures must degrade, not 500: fall back (cosine ranking, keyword search) or return 503 `AI_UNAVAILABLE`.

## Background work
- Slow work (embeddings, ingestion) goes on the RQ queue via `app.worker.create_queue()`; enqueue *after* commit,
  and treat enqueue failures as non-fatal unless the request is meaningless without the job (then 503).

## Tests (`backend/tests/`)
- Every endpoint: one happy-path + one validation/error test. Bug fixes get a regression test named after the bug.
- Fixtures from `tests/conftest.py`:
  - `client` — httpx client on the real app, sharing the test's DB session; it keeps cookies, so
    `await client.post("/api/auth/register", ...)` logs you in.
  - `db_session` — runs inside a rolled-back transaction; service `commit()`s become savepoints, so tests never leak.
  - `fake_queue` (autouse) — assert on `fake_queue.enqueue`.
  - `mock_claude_create(text)`, `mock_claude_stream(text, stop_reason=...)`, `mock_embedding` — no live AI calls ever.
- Assert errors as `res.json()["code"] == "SOME_CODE"`.
- Run: `docker compose exec api pytest -q` (or locally with `DATABASE_URL` pointing at a throwaway Postgres+pgvector DB).
- Before finishing: `ruff check .`, `mypy app` (strict), `pytest -q -m "not perf"`, `alembic check`.
