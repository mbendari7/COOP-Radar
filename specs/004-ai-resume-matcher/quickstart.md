# Quickstart Validation Guide: AI Resume Matcher

**Feature**: 004-ai-resume-matcher | **Date**: 2026-10-10

This guide documents how to verify the AI Resume Matcher feature end-to-end after implementation.
See [data-model.md](data-model.md) for entity definitions and [contracts/api.md](contracts/api.md)
for full request/response schemas.

---

## Prerequisites

1. Stack running: `docker compose up --build`
2. Migration applied: `docker compose exec api alembic upgrade head`
3. Skills taxonomy seeded: `docker compose exec api python -m seed.skills`
4. Postings seeded with embeddings (Feature 003 seeds): `docker compose exec api python -m seed.ingest_sources`
5. A test PDF resume ready (≤ 5 MB, at least 3 skills mentioned)
6. A test DOCX resume ready

---

## Scenario A — Happy Path Upload (US1)

```bash
# 1. Register + log in (or use existing test user)
curl -X POST http://localhost:8000/api/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"student@test.com","password":"Test1234!"}'

# 2. Get auth token
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"student@test.com","password":"Test1234!"}' | jq -r '.access_token')

# 3. Upload resume
curl -X POST http://localhost:8000/api/resume \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@backend/tests/fixtures/resume/sample_resume.pdf"
```

**Expected**: `200 OK` with `resume` metadata and `matches` array containing up to 20 items,
each with `score` (0–100), `reason` (one sentence), and posting fields. Response arrives in < 30 s.

---

## Scenario B — Invalid File Type (US1, FR-001)

```bash
curl -X POST http://localhost:8000/api/resume \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@some_image.png"
```

**Expected**: `400 Bad Request`, body contains `"code": "INVALID_FILE_TYPE"`.

---

## Scenario C — Oversized File (US1, FR-001)

```bash
# Create a 6 MB dummy file
dd if=/dev/zero of=/tmp/big.pdf bs=1M count=6
curl -X POST http://localhost:8000/api/resume \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/big.pdf"
```

**Expected**: `400 Bad Request`, body contains `"code": "FILE_TOO_LARGE"`.

---

## Scenario D — View Stored Resume Metadata (US3)

```bash
curl http://localhost:8000/api/resume \
  -H "Authorization: Bearer $TOKEN"
```

**Expected**: `200 OK` with `filename`, `file_size`, `uploaded_at`.

---

## Scenario E — Re-upload Replaces Previous (US1, FR-006)

```bash
# Upload a second resume; check that matches are refreshed
curl -X POST http://localhost:8000/api/resume \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@backend/tests/fixtures/resume/sample_resume_v2.docx"

curl http://localhost:8000/api/resume/matches \
  -H "Authorization: Bearer $TOKEN"
```

**Expected**: `GET /api/resume/matches` returns results with `ranked_at` matching the new upload time.

---

## Scenario F — Return Visit Loads Stored Results (US1, SC6)

```bash
time curl http://localhost:8000/api/resume/matches \
  -H "Authorization: Bearer $TOKEN"
```

**Expected**: Response arrives in < 2 s (reads from DB; no re-computation).

---

## Scenario G — Ask Follow-up Question with Citation (US2)

```bash
# Get a posting_id from the matches list
POSTING_ID=$(curl -s http://localhost:8000/api/resume/matches \
  -H "Authorization: Bearer $TOKEN" | jq -r '.items[0].posting_id')

curl -X POST "http://localhost:8000/api/resume/matches/$POSTING_ID/ask" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question": "What Python skills from my resume match this job?"}' \
  --no-buffer
```

**Expected**: `text/event-stream` response; tokens stream word-by-word; response contains
`Resume:` or `Posting:` citation prefix; ends with `data: [DONE]`.

---

## Scenario H — AI Says It Doesn't Know (US2, FR-009)

```bash
curl -X POST "http://localhost:8000/api/resume/matches/$POSTING_ID/ask" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question": "Will this company hire someone with a 2.5 GPA?"}' \
  --no-buffer
```

**Expected**: Streamed response includes the phrase "I don't have enough information".

---

## Scenario I — Delete Resume (US3)

```bash
curl -X DELETE http://localhost:8000/api/resume \
  -H "Authorization: Bearer $TOKEN"
# Verify gone
curl http://localhost:8000/api/resume \
  -H "Authorization: Bearer $TOKEN"
curl http://localhost:8000/api/resume/matches \
  -H "Authorization: Bearer $TOKEN"
```

**Expected**:
- DELETE returns `204 No Content`
- GET /api/resume returns `404`
- GET /api/resume/matches returns `{"items": [], "resume": null}`

---

## Scenario J — Cross-user Isolation (FR-014)

```bash
# Register a second user and verify they cannot see the first user's resume
TOKEN2=$(curl -s -X POST http://localhost:8000/api/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"other@test.com","password":"Test1234!"}' | jq -r '.access_token')

curl http://localhost:8000/api/resume -H "Authorization: Bearer $TOKEN2"
```

**Expected**: `404 Not Found` — the second user has no resume.

---

## Backend Tests

```bash
# Unit + integration tests
docker compose exec api pytest backend/tests/resume/ -v

# Eval suite (citation rate + factual accuracy)
docker compose exec api pytest backend/tests/eval/test_resume_match_eval.py -v
```

**Gate**: All tests pass. Eval suite citation rate ≥ 80 %. Zero factual errors in 25 fixture cases.

---

## Frontend Smoke Test

1. Navigate to `http://localhost:5173`
2. Sign in as `student@test.com`
3. Click **Matches** in the nav
4. Verify upload prompt shown (if no resume) or ranked match cards (if resume exists)
5. Upload `sample_resume.pdf` → cards appear within 30 s with score badges and reasons
6. Click **Ask about this role** on any card → panel opens
7. Type a question → response streams word-by-word
8. Navigate to **Account** → resume metadata shown with **Delete resume** button
9. Click **Delete resume** → confirm modal → resume and matches cleared
