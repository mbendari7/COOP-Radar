# API Contracts: AI Resume Matcher

**Feature**: 004-ai-resume-matcher | **Date**: 2026-10-10

All endpoints require authentication (`Authorization: Bearer <token>` or session cookie per
existing auth convention). Resume data is scoped to the authenticated user (FR-014).

---

## POST /api/resume

Upload a resume file, extract text, run match pipeline, store results.

**Request**: `multipart/form-data`

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `file` | file | yes | PDF or DOCX; ≤ 5 MB |

**Success response**: `200 OK`
```json
{
  "resume": {
    "id": "uuid",
    "filename": "resume.pdf",
    "file_size": 102400,
    "uploaded_at": "2026-10-10T12:00:00Z"
  },
  "matches": [
    {
      "posting_id": "uuid",
      "title": "Software Developer Co-op",
      "company": "Acme Corp",
      "city": "Toronto",
      "province": "ON",
      "term": "Winter 2027",
      "deadline": "2026-12-01",
      "score": 87,
      "reason": "Your Python and Django experience directly aligns with this role's core requirements."
    }
  ]
}
```

**Error responses**:
- `400 Bad Request` — `{"detail": "Unsupported file type. Upload a PDF or DOCX.", "code": "INVALID_FILE_TYPE"}`
- `400 Bad Request` — `{"detail": "File exceeds 5 MB limit.", "code": "FILE_TOO_LARGE"}`
- `422 Unprocessable Entity` — `{"detail": "Could not extract text from the uploaded file.", "code": "EXTRACTION_FAILED"}`
- `401 Unauthorized` — unauthenticated request
- `504 Gateway Timeout` — match pipeline exceeded 30 s

**Notes**:
- Re-uploading replaces the existing resume row and all match_results atomically
- Matches are returned sorted by `score DESC` (up to 20)
- Extracted text is stored; the raw file is not persisted

---

## GET /api/resume

Return stored resume metadata for the authenticated user.

**Success response**: `200 OK`
```json
{
  "id": "uuid",
  "filename": "resume.pdf",
  "file_size": 102400,
  "uploaded_at": "2026-10-10T12:00:00Z"
}
```

**Error responses**:
- `404 Not Found` — `{"detail": "No resume on file.", "code": "RESUME_NOT_FOUND"}`
- `401 Unauthorized`

---

## DELETE /api/resume

Permanently delete the stored resume and all associated match results.

**Success response**: `204 No Content`

**Error responses**:
- `404 Not Found` — `{"detail": "No resume on file.", "code": "RESUME_NOT_FOUND"}`
- `401 Unauthorized`

---

## GET /api/resume/matches

Return the stored ranked match results for the authenticated user's current resume.

**Success response**: `200 OK`
```json
{
  "items": [
    {
      "posting_id": "uuid",
      "title": "Software Developer Co-op",
      "company": "Acme Corp",
      "city": "Toronto",
      "province": "ON",
      "term": "Winter 2027",
      "deadline": "2026-12-01",
      "score": 87,
      "reason": "Your Python and Django experience directly aligns with this role's core requirements."
    }
  ],
  "resume": {
    "id": "uuid",
    "filename": "resume.pdf",
    "file_size": 102400,
    "uploaded_at": "2026-10-10T12:00:00Z"
  }
}
```

**When no resume**: `200 OK` with `{"items": [], "resume": null}`

**Error responses**:
- `401 Unauthorized`

---

## POST /api/resume/matches/{posting_id}/ask

Stream a Q&A response about the matched posting. Response is streamed as Server-Sent Events.

**Path parameters**:
- `posting_id` — UUID of the posting (must be in the user's match results)

**Request body**: `application/json`
```json
{
  "question": "Do I have enough Python experience for this role?"
}
```

**Success response**: `200 OK`, `Content-Type: text/event-stream`

Each SSE event:
```
data: {"delta": "Based "}\n\n
data: {"delta": "on your "}\n\n
data: {"delta": "resume, "}\n\n
...
data: [DONE]\n\n
```

Final message is always `data: [DONE]\n\n`.

**Error responses** (returned before streaming starts):
- `404 Not Found` — `{"detail": "Posting not in your match results.", "code": "MATCH_NOT_FOUND"}`
- `404 Not Found` — `{"detail": "No resume on file.", "code": "RESUME_NOT_FOUND"}`
- `400 Bad Request` — `{"detail": "Question must not be empty.", "code": "EMPTY_QUESTION"}`
- `401 Unauthorized`

**Notes**:
- Context window = resume `extracted_text` (truncated to 2000 tokens) + posting `description`
  (truncated to 1500 tokens) + posting metadata (title, company, skills)
- Claude is instructed to cite sources inline (`Resume: "..."` or `Posting: "..."`)
- When unanswerable from context, Claude responds: `"I don't have enough information to answer that."`
- No conversation history is persisted; each request is stateless

---

## Frontend Hooks Summary

| Hook | Method | Endpoint |
|------|--------|----------|
| `useResume()` | GET | `/api/resume` |
| `useUploadResume()` | POST | `/api/resume` |
| `useDeleteResume()` | DELETE | `/api/resume` |
| `useMatches()` | GET | `/api/resume/matches` |
| `useAskAboutPosting(postingId)` | POST | `/api/resume/matches/{postingId}/ask` |
