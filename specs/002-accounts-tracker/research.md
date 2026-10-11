# Research: Accounts & Application Tracker

**Feature**: `002-accounts-tracker` | **Date**: 2026-10-10

---

## Password Hashing

**Decision**: argon2-cffi (argon2id variant)

**Rationale**: Constitution V mandates argon2. argon2id is the current OWASP-recommended
variant — it combines data-dependent (argon2d) resistance to GPU attacks with
side-channel resistance (argon2i). `argon2-cffi` is the standard Python binding,
well-maintained and used by passlib. Default parameters (time_cost=2, memory_cost=64MB,
parallelism=1) are adequate for a web app with <1000 concurrent logins.

**Alternatives considered**:
- `passlib[argon2]` — thin wrapper around argon2-cffi; adds passlib overhead with no
  benefit for our simple use case; we'll call argon2-cffi directly.
- bcrypt — older; still acceptable but not the current OWASP recommendation.

---

## Session Storage

**Decision**: Redis with a random 32-byte hex token stored in an HTTP-only cookie.
Session data (user_id) stored as a Redis hash under key `session:<token>`.
Expiry: 7-day rolling (EXPIRE reset on every authenticated request).

**Rationale**: Redis is already in the Docker Compose stack (Feature 001). A simple
token-in-cookie + Redis hash approach is straightforward, auditable, and trivially
revocable (DEL the key). We do not need JWT because all our state is server-side,
and revocation (logout) is instant with a Redis delete.

**Alternatives considered**:
- JWT (stateless) — can't revoke without a denylist, which brings back Redis anyway;
  adds complexity with no benefit at our scale.
- Database-backed sessions (PostgreSQL) — works but Redis is faster for the high-frequency
  session lookup on every authenticated request.
- `fastapi-users` library — opinionated, pulls in many dependencies (SQLAlchemy event
  hooks, email verification flows) we don't need yet. Constitution IX (Simplicity) says
  avoid abstractions for hypothetical future requirements.

**Cookie settings**: `HttpOnly=True`, `Secure=True` (HTTPS in prod, accepted over HTTP
in dev), `SameSite=Lax` (protects against CSRF on same-origin navigation).

---

## Session Middleware vs Dependency

**Decision**: FastAPI `Depends` — a `get_current_user` dependency that reads the
cookie, looks up Redis, and returns the User ORM object (or raises 401).

**Rationale**: Middleware runs on every request including unauthenticated routes
(postings list). A dependency only runs on routes that declare it, keeping
unauthenticated routes unaffected (Constitution — FR-015). Simpler to test: inject
a mock user in tests.

---

## Async Redis Client

**Decision**: `redis.asyncio` (the async sub-package of `redis-py` ≥ 5.0).

**Rationale**: `redis-py` 5.x ships built-in async support via `redis.asyncio`. No
separate `aioredis` package needed — it was merged upstream. One fewer dependency
(Constitution IX).

**Alternatives considered**:
- `aioredis` ≥ 2.0 — API is identical; it's been superseded by `redis.asyncio`.

---

## Email Normalisation

**Decision**: `email.lower().strip()` before storage and before every lookup.

**Rationale**: Simple, no external dependency. RFC 5321 says the local part is
case-sensitive but in practice all major providers treat it as case-insensitive.
Normalising prevents "User@example.com" and "user@example.com" from being two accounts.

---

## Database Schema

**Decision**: Two new tables — `users` and `saved_postings` — in the existing
PostgreSQL database via a new Alembic migration (0002).

**Rationale**: Same DB, same async SQLAlchemy session pattern as Feature 001.
No new infrastructure.

**`application_status` enum values**: `applied`, `interviewing`, `offer`, `rejected`.
Stored as a PostgreSQL ENUM type. NULL means "no status set" (not the same as any
of the four values).

---

## Auth Flow Summary

```
POST /api/auth/register
  → validate email unique, hash password
  → INSERT users row
  → create Redis session (set session:<token> = {user_id}, EXPIRE 7d)
  → Set-Cookie: session=<token>; HttpOnly; Secure; SameSite=Lax

POST /api/auth/login
  → look up user by email, verify argon2 hash
  → create Redis session
  → Set-Cookie: session=<token>; ...

POST /api/auth/logout
  → DEL session:<token> from Redis
  → Set-Cookie: session=; Max-Age=0  (clears the cookie)

get_current_user dependency
  → read cookie session=<token>
  → GET session:<token> from Redis → {user_id}
  → SELECT user WHERE id = user_id
  → reset Redis EXPIRE (rolling 7d)
  → return User
```
