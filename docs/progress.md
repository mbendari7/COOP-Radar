# CoopRadar — Progress Log

**Repo**: `C:\Users\myfun\OneDrive\Documents\GitHub\COOP-Radar`
**Note on path**: Ground rules reference `C:\dev\COOP-Radar`; actual path is above. Update any CI/script references accordingly.

---

## Current phase

**Phase 0 complete** — repo skeleton ready.
**Next**: Gate 0 review, then Phase 1 (Feature 001 — Browse & Search).

---

## Phase 0 — Repo readiness (2026-10-10)

### Completed
- `CLAUDE.md` copied to repo root (source: `coopradar-claude-setup/CLAUDE.md`)
- `.gitattributes` added — enforces LF line endings globally
- `.editorconfig` added — indent, charset, and newline rules
- `docs/progress.md` (this file) created
- Constitution confirmed at `coopradar/coopradar/.specify/memory/constitution.md`

### Skills locations
| Skill set | Path |
|-----------|------|
| Spec Kit (`speckit-*`) | `coopradar/coopradar/.claude/skills/` |
| Project skills (`api-conventions`, `frontend-tables`, `agent-tools`, `db-migration`, `log-agentic-work`) | `coopradar/coopradar/skills/` |
| `SPECKIT_PROMPTS.md` | `coopradar/coopradar/.claude/skills/SPECKIT_PROMPTS.md` |

### Open issues from Phase 0
- Repo path mismatch: ground rules say `C:\dev\COOP-Radar`; actual is `C:\Users\myfun\OneDrive\Documents\GitHub\COOP-Radar`. Confirm correct path with user.

---

## Pre-existing implementation (built in earlier sessions)

Features 001 and 002 were substantially implemented before this structured workflow began.
At Gate 0 the user will decide: validate and continue from Phase 3, or re-run the loop from Phase 1.

### Feature 001 — Browse & Search Postings
**Status**: Code exists, not yet validated against spec success criteria in this session.

Files present:
- `backend/app/models/posting.py` — `Posting` ORM, `WorkMode` enum
- `backend/alembic/versions/0001_create_postings.py` — tsvector GIN index, all B-tree indexes
- `backend/seed/` — ~62 seeded postings
- `backend/app/services/postings.py` — list/search/filter/sort/paginate, `get_filter_meta`
- `backend/app/api/postings.py` — `GET /api/postings`, `GET /api/postings/{id}`, `GET /api/postings/meta/filters`
- `backend/tests/api/test_postings.py` — 16 tests + perf test
- `frontend/src/api/postings.ts` — TanStack Query hooks
- `frontend/src/components/PostingsTable.tsx`, `PostingCard.tsx`, `FilterBar.tsx`, `SearchBox.tsx`
- `frontend/src/pages/PostingsListPage.tsx`, `PostingDetailPage.tsx`
- `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile`
- `.github/workflows/ci.yml`

### Feature 002 — Accounts & Application Tracker
**Status**: Code exists, not yet validated against spec success criteria in this session.

Files present:
- `backend/app/models/user.py`, `saved_posting.py`
- `backend/alembic/versions/0002_add_auth.py`
- `backend/app/services/auth.py`, `saved_postings.py`
- `backend/app/api/auth.py`, `me.py`, `saved.py`
- `backend/app/deps.py`, `redis.py`
- `backend/tests/api/test_auth.py`, `test_me.py`, `test_saved.py`
- `frontend/src/api/auth.ts`, `saved.ts`
- `frontend/src/components/AuthModal.tsx`, `BookmarkButton.tsx`, `StatusBadge.tsx`
- `frontend/src/pages/SavedPostingsPage.tsx`, `AccountSettingsPage.tsx`
- `frontend/src/App.tsx` — header with auth slot, all routes

---

## Phase 1 — Feature 001: Browse & Search (pending)

Branch: `001-browse-search`
Status: **Pending Gate 0 decision** (code may already exist; needs spec loop validation)

---

## Phase 2 — Feature 002: Accounts & Application Tracker (pending)

Branch: `002-accounts-tracker`
Status: **Pending Gate 0 decision**

---

## Phase 3 — Feature 003: Real Postings & Semantic Search (not started)

Branch: `003-ingestion-search`
Status: Not started

---

## Phase 4 — Feature 004: AI Resume Matcher & Assistant (not started)

Branch: `004-ai-matcher`
Status: Not started
