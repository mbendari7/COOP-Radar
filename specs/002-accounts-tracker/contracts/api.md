# API Contracts: Accounts & Application Tracker

**Feature**: `002-accounts-tracker` | **Date**: 2026-10-10

Base URL: `http://localhost:8000` | Prefix: `/api`

Auth endpoints: `/api/auth/*`
Saved postings endpoints: `/api/saved/*`
Account management: `/api/me`

Session is carried via **cookie** `session=<token>`. All endpoints marked
**[auth required]** return `401` if the cookie is absent or invalid.

---

## POST /api/auth/register

Create a new account and start a session.

### Request body

```json
{ "email": "student@uwaterloo.ca", "password": "supersecret99" }
```

| Field | Type | Validation |
|-------|------|-----------|
| `email` | string | valid email format; normalised to lowercase |
| `password` | string | min 10 characters |

### Response 201 Created

```json
{ "id": "<uuid>", "email": "student@uwaterloo.ca" }
```

Sets cookie: `session=<token>; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=604800`

### Response 409 Conflict

```json
{ "detail": "An account with this email already exists", "code": "EMAIL_TAKEN" }
```

### Response 422 Unprocessable Entity

Pydantic validation failure (invalid email format, password too short).

---

## POST /api/auth/login

Authenticate and start a session.

### Request body

```json
{ "email": "student@uwaterloo.ca", "password": "supersecret99" }
```

### Response 200 OK

```json
{ "id": "<uuid>", "email": "student@uwaterloo.ca" }
```

Sets cookie: `session=<token>; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=604800`

### Response 401 Unauthorized

```json
{ "detail": "Invalid email or password", "code": "INVALID_CREDENTIALS" }
```

Note: The same error is returned whether the email doesn't exist or the password
is wrong — preventing account enumeration (FR-014).

---

## POST /api/auth/logout

**[auth required]**

Invalidate the current session.

### Response 204 No Content

Clears cookie: `session=; Max-Age=0; HttpOnly; Secure; SameSite=Lax; Path=/`

### Response 401 Unauthorized

Already logged out or session expired.

---

## GET /api/me

**[auth required]**

Return the current user's profile.

### Response 200 OK

```json
{ "id": "<uuid>", "email": "student@uwaterloo.ca", "created_at": "2026-10-10T12:00:00Z" }
```

---

## PATCH /api/me/password

**[auth required]**

Change the current user's password.

### Request body

```json
{ "current_password": "supersecret99", "new_password": "evenbetter123" }
```

### Response 204 No Content

Password updated.

### Response 401 Unauthorized

```json
{ "detail": "Current password is incorrect", "code": "WRONG_PASSWORD" }
```

### Response 422

New password fails validation (< 10 characters).

---

## DELETE /api/me

**[auth required]**

Permanently delete the account and all associated data.

### Request body

```json
{ "password": "supersecret99" }
```

Password confirmation prevents accidental deletion.

### Response 204 No Content

Account, saved postings, and session deleted.

### Response 401 Unauthorized

```json
{ "detail": "Current password is incorrect", "code": "WRONG_PASSWORD" }
```

---

## GET /api/saved

**[auth required]**

Return the current user's saved postings, ordered by most recently saved.
Accepts same pagination params as `/api/postings` (page, page_size).
Optionally filter by `status`.

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `status` | string | — | Filter: `applied` / `interviewing` / `offer` / `rejected` |
| `page` | integer | 1 | 1-based page number |
| `page_size` | integer | 25 | 10 / 25 / 50 |

### Response 200 OK

```json
{
  "items": [
    {
      "id": "<saved-posting-uuid>",
      "saved_at": "2026-10-10T14:00:00Z",
      "status": "applied",
      "posting": {
        "id": "<posting-uuid>",
        "title": "Backend Developer Co-op",
        "company": "Shopify",
        "city": "Toronto",
        "province": "ON",
        "work_mode": "hybrid",
        "term": "Summer 2027",
        "duration_months": 4,
        "deadline": "2027-02-28",
        "posted_at": "2026-09-15T10:00:00Z",
        "skills": ["Python", "Django"],
        "source_url": "https://example.com/job/1",
        "is_expired": false
      }
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 25,
  "status_counts": {
    "applied": 3,
    "interviewing": 1,
    "offer": 0,
    "rejected": 2,
    "none": 4
  }
}
```

---

## POST /api/saved

**[auth required]**

Save a posting. Idempotent — returns the existing record if already saved.

### Request body

```json
{ "posting_id": "<uuid>" }
```

### Response 201 Created (or 200 OK if already saved)

```json
{ "id": "<saved-posting-uuid>", "saved_at": "2026-10-10T14:00:00Z", "status": null }
```

### Response 404 Not Found

```json
{ "detail": "Posting not found", "code": "POSTING_NOT_FOUND" }
```

---

## DELETE /api/saved/{saved_posting_id}

**[auth required]**

Remove a saved posting. Returns 404 if the saved posting doesn't exist or belongs to another user.

### Response 204 No Content

---

## PATCH /api/saved/{saved_posting_id}/status

**[auth required]**

Update the application status on a saved posting.

### Request body

```json
{ "status": "interviewing" }
```

Pass `null` to clear the status.

### Response 200 OK

```json
{ "id": "<saved-posting-uuid>", "status": "interviewing", "saved_at": "..." }
```

### Response 404 Not Found

Saved posting not found or belongs to another user.

### Response 422

Invalid status value.

---

## GET /api/postings — saved indicator

The existing postings list endpoint returns an optional `is_saved` boolean for
authenticated users. Unauthenticated requests omit the field entirely.

When the frontend includes the session cookie, each item in the list includes:

```json
{ ...existing fields..., "is_saved": true }
```

---

## Pydantic Schemas (reference)

```python
# backend/app/schemas/auth.py

class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10)

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: str
    created_at: datetime

class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=10)

class DeleteAccountIn(BaseModel):
    password: str

# backend/app/schemas/saved_posting.py

class SaveIn(BaseModel):
    posting_id: UUID

class StatusUpdateIn(BaseModel):
    status: ApplicationStatus | None

class SavedPostingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    saved_at: datetime
    status: ApplicationStatus | None
    posting: PostingListItem     # reused from Feature 001

class SavedPostingsPage(BaseModel):
    items: list[SavedPostingOut]
    total: int
    page: int
    page_size: int
    status_counts: dict[str, int]
```
