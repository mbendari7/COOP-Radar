# API Contracts: Real Postings Ingestion & Semantic Search

**Feature**: 003-ingestion-search
**Date**: 2026-10-10

All endpoints follow the existing conventions in `skills/api-conventions.md`.
All requests/responses use `application/json` unless stated otherwise.
Admin endpoints require `is_admin = true` on the authenticated user; non-admin returns `403 FORBIDDEN`.

---

## Modified Endpoints

### `GET /api/postings`

Existing endpoint extended with `search_mode` and `closed` parameters.

**New query parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `search_mode` | `"keyword" \| "semantic"` | `"keyword"` | Switch between tsvector and cosine-similarity ranking |
| `show_closed` | `boolean` | `false` | Include closed postings (those with `closed_at` set) |

**Behaviour change**: When `search_mode=semantic` and `q` is provided, results are ranked by cosine similarity to the query embedding instead of tsvector rank. All existing filter/sort/pagination parameters remain unchanged. If no embedding exists for a posting yet, that posting is excluded from semantic results but appears in keyword results.

---

### `GET /api/postings/{id}`

Existing endpoint; the response body gains one new field:

```json
{
  "id": "...",
  "title": "...",
  "...": "...",
  "closed_at": null,
  "low_confidence_fields": {}
}
```

`low_confidence_fields` is only populated for admin users; the field is omitted (not present) in responses to non-admin users.

---

## New Endpoints

### `GET /api/postings/{id}/similar`

Return up to 5 postings most similar to the given posting by cosine similarity.

**Auth**: None required (public).

**Response `200 OK`**:
```json
{
  "items": [
    {
      "id": "uuid",
      "title": "string",
      "company": "string",
      "city": "string",
      "province": "string",
      "work_mode": "remote",
      "term": "Summer 2027",
      "deadline": "2027-03-01",
      "similarity": 0.87
    }
  ]
}
```

**Error `404 NOT_FOUND`**: Posting does not exist.
**Error `503 EMBEDDINGS_UNAVAILABLE`**: Embedding service is down; no similarity results available.

---

### `POST /api/postings/upload`

Upload a CSV file to bulk-import postings. Rate-limited to 3 uploads per user per hour.

**Auth**: Authenticated user required.

**Request**: `multipart/form-data` with field `file` (CSV).

**Required CSV columns**: `title`, `company`, `city`, `term`, `deadline`
**Optional CSV columns**: `province`, `work_mode`, `duration_months`, `description`, `skills`, `source_url`

**Response `200 OK`**:
```json
{
  "added": 4,
  "skipped_duplicates": 1,
  "errors": [
    {
      "row": 3,
      "column": "deadline",
      "message": "Invalid date format. Expected YYYY-MM-DD."
    }
  ]
}
```

**Error `400 INVALID_CSV`**: File is not parseable as CSV or is missing required column headers.
**Error `413 FILE_TOO_LARGE`**: More than 1,000 rows.
**Error `429 RATE_LIMITED`**: Upload rate limit exceeded.

---

### `POST /api/postings`

Add a single posting manually.

**Auth**: Authenticated user required.

**Request body**:
```json
{
  "title": "string (required)",
  "company": "string (required)",
  "city": "string (required)",
  "province": "string (optional)",
  "work_mode": "onsite|hybrid|remote (optional)",
  "term": "string (required)",
  "duration_months": "integer (optional)",
  "deadline": "date YYYY-MM-DD (required)",
  "description": "string (optional)",
  "skills": ["string"] ,
  "source_url": "string (optional)"
}
```

**Response `201 CREATED`**: Returns the new `PostingListItem` schema.

**Error `409 DUPLICATE`**: Posting with same company, similar title, and city already exists.
**Error `422 VALIDATION_ERROR`**: Missing required fields or invalid values.

---

### `GET /api/admin/sources`

List all ingestion sources. **Admin only.**

**Response `200 OK`**:
```json
{
  "items": [
    {
      "id": "uuid",
      "name": "string",
      "adapter_type": "json_api",
      "enabled": true,
      "auto_paused": false,
      "last_run_at": "2026-10-10T06:00:00Z",
      "last_run_status": "success",
      "last_run_added": 12,
      "last_run_updated": 3,
      "last_run_closed": 1,
      "last_run_errors": 0
    }
  ]
}
```

---

### `GET /api/admin/sources/{id}/runs`

Paginated run history for a source. **Admin only.**

**Query params**: `page` (default 1), `page_size` (default 20).

**Response `200 OK`**:
```json
{
  "items": [
    {
      "id": "uuid",
      "started_at": "2026-10-10T06:00:00Z",
      "finished_at": "2026-10-10T06:00:47Z",
      "status": "success",
      "added": 12,
      "updated": 3,
      "closed": 1,
      "errors": 0,
      "error_log": []
    }
  ],
  "total": 48,
  "page": 1,
  "page_size": 20
}
```

---

### `POST /api/admin/sources/{id}/run`

Trigger an immediate run for a source. **Admin only.**

**Response `202 ACCEPTED`**:
```json
{
  "run_id": "uuid",
  "message": "Run queued."
}
```

**Error `404 NOT_FOUND`**: Source does not exist.
**Error `409 ALREADY_RUNNING`**: A run is already in progress for this source.
**Error `422 SOURCE_PAUSED`**: Source is auto-paused; admin must re-enable it first.

---

### `PATCH /api/admin/sources/{id}`

Enable, disable, or un-pause a source. **Admin only.**

**Request body** (all fields optional):
```json
{
  "enabled": true,
  "auto_paused": false
}
```

Setting `auto_paused: false` also resets `consecutive_failures` to 0.

**Response `200 OK`**: Returns updated source object.

---

## Error Envelope (unchanged)

All error responses use the existing project envelope:
```json
{ "detail": "Human-readable message", "code": "SCREAMING_SNAKE_CODE" }
```
