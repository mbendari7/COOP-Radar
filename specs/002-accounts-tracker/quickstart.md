# Quickstart: Accounts & Application Tracker

**Feature**: `002-accounts-tracker` | **Date**: 2026-10-10

---

## Prerequisites

- Feature 001 stack running: `docker compose up --build`
- Migration 0001 applied and seed data loaded
- `httpie` or `curl` for manual API validation

---

## Stack startup

```bash
docker compose up --build
docker compose exec api alembic upgrade head   # applies 0002 migration
```

---

## End-to-end validation

### 1 — Register a new account

```bash
curl -s -c cookies.txt -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password1234"}' | jq .

# Expected: {"id":"...","email":"test@example.com"}
# cookies.txt now contains the session cookie
```

### 2 — Verify the cookie is HttpOnly

Check the response headers — `Set-Cookie` must include `HttpOnly` and `SameSite=Lax`:

```
Set-Cookie: session=<token>; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=604800
```

### 3 — Hit a protected endpoint without the cookie (expect 401)

```bash
curl -s http://localhost:8000/api/saved | jq .
# Expected: {"detail":"Not authenticated","code":"NOT_AUTHENTICATED"}
```

### 4 — Hit the same endpoint with the cookie (expect 200)

```bash
curl -s -b cookies.txt http://localhost:8000/api/saved | jq .
# Expected: {"items":[],"total":0,"page":1,"page_size":25,"status_counts":{...}}
```

### 5 — Save a posting

```bash
# Get a posting ID first
POSTING_ID=$(curl -s http://localhost:8000/api/postings | jq -r '.items[0].id')

curl -s -b cookies.txt -c cookies.txt -X POST http://localhost:8000/api/saved \
  -H "Content-Type: application/json" \
  -d "{\"posting_id\":\"$POSTING_ID\"}" | jq .
# Expected: {"id":"...","saved_at":"...","status":null}
```

### 6 — View saved postings

```bash
curl -s -b cookies.txt http://localhost:8000/api/saved | jq '.items | length'
# Expected: 1
```

### 7 — Set application status

```bash
SAVED_ID=$(curl -s -b cookies.txt http://localhost:8000/api/saved | jq -r '.items[0].id')

curl -s -b cookies.txt -c cookies.txt -X PATCH \
  "http://localhost:8000/api/saved/$SAVED_ID/status" \
  -H "Content-Type: application/json" \
  -d '{"status":"applied"}' | jq .
# Expected: {"id":"...","status":"applied","saved_at":"..."}
```

### 8 — Log out

```bash
curl -s -b cookies.txt -c cookies.txt -X POST http://localhost:8000/api/auth/logout
# Expected: 204 No Content

# Confirm session is gone
curl -s -b cookies.txt http://localhost:8000/api/saved | jq .
# Expected: 401
```

### 9 — Frontend smoke tests

- Open http://localhost:5173
- A "Sign in / Register" button should be visible in the header
- Register → the header shows the user's email
- Click any posting's bookmark icon → it fills in
- Navigate to /saved → the posting appears
- Set status → badge updates without reload
- Log out → bookmark icons become unfilled

---

## Automated test commands

```bash
# Backend (excludes perf)
docker compose exec api pytest -q -m "not perf"

# Frontend
docker compose exec web npm test
```
