# API Contracts: Bring Your Own AI Key and a Resume First Site

**Feature**: 005-byok-resume-first
**Date**: 2026-10-11 (written up 2026-11-17)

Errors look like `{"detail": "...", "code": "SNAKE_CASE"}`. AI routes read the visitor's key from these headers:

| Header | Example | Notes |
|---|---|---|
| `X-AI-Provider` | `anthropic`, `openai`, `gemini` | |
| `X-AI-Key` | | Never stored, logged or echoed |
| `X-AI-Model` | `claude-sonnet-5-5` | The model picked on the AI key page |

With no headers, the owner's `ANTHROPIC_API_KEY` is used if set, up to `AI_DAILY_LIMIT` actions per person per day.

AI error codes: `AI_KEY_REQUIRED`, `AI_PROVIDER_INVALID`, `AI_MODEL_REQUIRED`, `AI_KEY_INVALID`, `AI_MODEL_INVALID`,
`AI_PROVIDER_RATE_LIMITED` (429), `AI_LIMIT_REACHED` (429, the owner's daily limit), `AI_PROVIDER_ERROR` and
`AI_BAD_RESPONSE` (502).

---

## `POST /api/ai/check`

Checks a key and lists the models it can use. Rate limited per network.

**Body**: `{"provider": "anthropic" | "openai" | "gemini", "api_key": "..."}`

**200**: `{"provider": "anthropic", "models": [{"id": "...", "label": "..."}], "recommended": "..."}`

**400**: `AI_KEY_INVALID` **429**: `RATE_LIMITED`

## `GET /api/config`

Public settings the site reads at start. Never any secrets.

**200**: `{"demo_enabled": true, "server_ai_enabled": false, "semantic_search_enabled": false, "ai_daily_limit": 20}`

## `POST /api/auth/guest` and `POST /api/auth/demo`

Make a temporary account and sign in (sets the session cookie). Demo also fills a tracker, a resume and matches.

**201**: `UserOut` with `is_demo: true`
**429**: `RATE_LIMITED`, too many from this network
**404**: demo turned off (`DEMO_ENABLED=false`)

## `POST /api/me/claim`

Keep a temporary account. **Body**: `{"email": "...", "password": "..."}` (password at least 10 characters)

**200**: `UserOut` with `is_demo: false`
**409**: `EMAIL_TAKEN` **400**: `ALREADY_CLAIMED`

## `POST /api/resume`

Multipart upload: `file` (PDF or DOCX, up to 5 MB) and optional `preferences` (JSON). AI is optional. With a key
the matches are re-ranked by the visitor's model, without one they are ranked by skills.

**200**: `UploadResponse` with skills found, matches count and how they were ranked
**400**: `FILE_TOO_LARGE` or `INVALID_FILE_TYPE` **422**: `EXTRACTION_FAILED` (no text found)

## `POST /api/resume/rematch`

Re-rank the stored resume with the visitor's AI. Needs a key. **200**: `UploadResponse`

## `GET /api/resume/insights` and `POST /api/resume/insights`

GET is free: skills found, the 8 most asked for skills that are missing, and the cached AI review if there is one.
POST asks the visitor's AI for a review, caches it and returns it. **502** `AI_BAD_RESPONSE` if the reply can not be
read.

## `POST /api/resume/matches/{posting_id}/ask`

Streams Server Sent Events. The posting must be in this visitor's matches (404 otherwise).

**Body**: `{"mode": "question" | "tailor" | "cover_letter", "question": "..."}` (question needed only for
`question`)

**Stream**: `data: {"delta": "..."}` lines, then `data: [DONE]`. An error after the stream started comes as
`data: {"error": "..."}` because the status is already 200.

## `GET /api/postings` (changed)

New query flags: `students_only` (only intern, co-op, student and new grad titles) and `hide_senior`.
