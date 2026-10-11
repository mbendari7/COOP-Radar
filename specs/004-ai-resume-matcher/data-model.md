# Data Model: AI Resume Matcher

**Feature**: 004-ai-resume-matcher | **Date**: 2026-10-10

---

## Entities

### Resume

Stores uploaded resume metadata and extracted text for one user. Only one resume per user is
retained at any time; re-uploading replaces the existing row and cascades to delete `match_results`.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | UUID | PK, DEFAULT gen_random_uuid() | |
| `user_id` | UUID | NOT NULL, FK → users(id) ON DELETE CASCADE, UNIQUE | One resume per user |
| `filename` | TEXT | NOT NULL | Original upload filename (e.g., `resume.pdf`) |
| `file_size` | INTEGER | NOT NULL, CHECK > 0 | Bytes; stored for display in UI |
| `extracted_text` | TEXT | NOT NULL | Raw text extracted server-side; raw file is NOT stored |
| `uploaded_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

**Indexes**:
- `idx_resumes_user_id` on `(user_id)` — supports `WHERE user_id = $1` lookup

**Validation rules**:
- `file_size` ≤ 5,242,880 (5 MB) enforced in the upload endpoint before text extraction
- `filename` must end in `.pdf` or `.docx` (case-insensitive) — enforced in the upload endpoint
- `extracted_text` must be non-empty after extraction; return 422 if extraction yields blank text

---

### MatchResult

One row per (resume, posting) pair produced by the last match run. All rows for a resume are
replaced atomically when a new match run completes.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | UUID | PK, DEFAULT gen_random_uuid() | |
| `resume_id` | UUID | NOT NULL, FK → resumes(id) ON DELETE CASCADE | Cascade delete with resume |
| `posting_id` | UUID | NOT NULL, FK → postings(id) ON DELETE CASCADE | Cascade delete if posting removed |
| `score` | SMALLINT | NOT NULL, CHECK 0 ≤ score ≤ 100 | Match quality 0–100 |
| `reason` | TEXT | NOT NULL | One-sentence reason from Claude Haiku |
| `ranked_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | When this match run completed |

**Indexes**:
- `idx_match_results_resume_score` on `(resume_id, score DESC)` — fetching top-ranked results
- `UNIQUE (resume_id, posting_id)` — prevents duplicate entries per match run

**Validation rules**:
- `score` 0–100 inclusive enforced by CHECK constraint and Pydantic schema
- `reason` must be a non-empty string (max 500 chars enforced in schema, not DB)

---

## Relationships

```
users (1) ──────── (0..1) resumes
resumes (1) ───── (*) match_results
postings (1) ───── (*) match_results
```

- A user has at most one resume at a time (UNIQUE on `resumes.user_id`)
- Deleting a user cascades to delete their resume (via users FK CASCADE)
- Deleting a resume cascades to delete all its match_results
- Deleting a posting cascades to delete any match_results referencing it

---

## Migration

**Alembic migration**: `0005_add_resume_matcher.py`

```sql
-- Up
CREATE TABLE resumes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    file_size INTEGER NOT NULL CHECK (file_size > 0),
    extracted_text TEXT NOT NULL,
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_resumes_user_id ON resumes (user_id);

CREATE TABLE match_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resume_id UUID NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,
    posting_id UUID NOT NULL REFERENCES postings(id) ON DELETE CASCADE,
    score SMALLINT NOT NULL CHECK (score >= 0 AND score <= 100),
    reason TEXT NOT NULL,
    ranked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (resume_id, posting_id)
);

CREATE INDEX idx_match_results_resume_score ON match_results (resume_id, score DESC);

-- Down
DROP TABLE IF EXISTS match_results;
DROP TABLE IF EXISTS resumes;
```
