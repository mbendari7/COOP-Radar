# Tasks: AI Resume Matcher

**Input**: Design documents from `specs/004-ai-resume-matcher/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md, quickstart.md

**Tests**: Included — eval suite (25 cases) and endpoint tests are required per spec SC3/SC4 and constitution.

**Organization**: Tasks grouped by user story. US1 is MVP; US2 and US3 can begin after US1 completes or in parallel.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to
- Paths relative to repo root (`C:\Users\myfun\OneDrive\Documents\GitHub\COOP-Radar`)

---

## Phase 1: Setup

**Purpose**: Add new dependencies and test fixtures before any model/service work.

- [X] T001 Add `pypdf>=4.0` and `python-docx>=1.1` to `[project].dependencies` in `backend/pyproject.toml` (justification in research.md)
- [X] T002 [P] Create `backend/tests/fixtures/resume/` directory and `backend/tests/fixtures/resume/conftest.py` with `sample_pdf_bytes` and `sample_docx_bytes` pytest fixtures that generate minimal valid PDF (via pypdf) and DOCX (via python-docx) in memory — include at least three skill keywords ("Python", "Django", "PostgreSQL") in the text
- [X] T003 [P] Create `backend/tests/resume/__init__.py` (empty) and `backend/tests/eval/__init__.py` (empty) to make test packages discoverable

---

## Phase 2: Foundational

**Purpose**: Database schema, ORM models, and Alembic migration. All US phases depend on this.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T004 Create `backend/app/models/resume.py` with `Resume` SQLAlchemy ORM (Mapped[] style): `id: UUID PK DEFAULT gen_random_uuid()`, `user_id: UUID NOT NULL UNIQUE FK→users(id) ON DELETE CASCADE`, `filename: TEXT NOT NULL`, `file_size: INTEGER NOT NULL CHECK(file_size > 0)`, `extracted_text: TEXT NOT NULL`, `uploaded_at: TIMESTAMPTZ NOT NULL DEFAULT now()`; add `Index("idx_resumes_user_id", "user_id")`
- [X] T005 [P] Create `backend/app/models/match_result.py` with `MatchResult` SQLAlchemy ORM: `id: UUID PK DEFAULT gen_random_uuid()`, `resume_id: UUID NOT NULL FK→resumes(id) ON DELETE CASCADE`, `posting_id: UUID NOT NULL FK→postings(id) ON DELETE CASCADE`, `score: SMALLINT NOT NULL CHECK(score >= 0 AND score <= 100)`, `reason: TEXT NOT NULL`, `ranked_at: TIMESTAMPTZ NOT NULL DEFAULT now()`; `UniqueConstraint("resume_id", "posting_id")`; `Index("idx_match_results_resume_score", "resume_id", desc("score"))`
- [X] T006 Add `Resume` and `MatchResult` exports to `backend/app/models/__init__.py`
- [X] T007 Create `backend/alembic/versions/0005_add_resume_matcher.py` Alembic migration: upgrade creates `resumes` table (id UUID PK, user_id UUID NOT NULL UNIQUE FK→users CASCADE, filename TEXT NOT NULL, file_size INTEGER NOT NULL CHECK > 0, extracted_text TEXT NOT NULL, uploaded_at TIMESTAMPTZ NOT NULL DEFAULT now()), index `idx_resumes_user_id`; creates `match_results` table (id UUID PK, resume_id UUID NOT NULL FK→resumes CASCADE, posting_id UUID NOT NULL FK→postings CASCADE, score SMALLINT NOT NULL CHECK 0-100, reason TEXT NOT NULL, ranked_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(resume_id, posting_id)), index `idx_match_results_resume_score`; downgrade drops both tables

**Checkpoint**: Run `alembic upgrade head` — both tables created with correct constraints.

---

## Phase 3: US1 — Upload Resume and Get Ranked Matches (Priority: P1) MVP

**Goal**: Student uploads PDF/DOCX, text is extracted, match pipeline runs synchronously, ranked results stored and returned within 30 s.

**Independent Test**: POST a sample PDF → 200 with `resume` metadata + `matches` array up to 20 items, each with `score` (0–100) and `reason`. GET /api/resume/matches returns same results in < 2 s.

### Tests for US1

- [X] T008 [P] [US1] Create `backend/tests/resume/test_resume_upload.py` with tests: happy path PDF upload returns 200 with resume metadata + matches list; happy path DOCX upload returns 200; `.png` file returns 400 `INVALID_FILE_TYPE`; file > 5 MB returns 400 `FILE_TOO_LARGE`; PDF with no extractable text returns 422 `EXTRACTION_FAILED`; re-upload replaces previous resume and match_results rows; unauthenticated request returns 401 — use `sample_pdf_bytes` / `sample_docx_bytes` fixtures; mock Anthropic and OpenAI calls with respx/unittest.mock
- [X] T009 [P] [US1] Create `backend/tests/resume/test_match_service.py`: test `extract_pdf_text` returns non-empty string from `sample_pdf_bytes`; test `extract_docx_text` returns non-empty string from `sample_docx_bytes`; test unsupported extension raises `ValueError`; test `embed_and_rank` returns list of ≤ 20 items each with score 0–100 and non-empty reason (mock OpenAI embed + DB cosine query + Anthropic Haiku re-rank)

### Implementation for US1

- [X] T010 [P] [US1] Create `backend/app/schemas/resume.py` with Pydantic v2 models: `ResumeOut(id: UUID, filename: str, file_size: int, uploaded_at: datetime)`, `MatchResultOut(posting_id: UUID, title: str, company: str, city: str, province: str, term: str, deadline: str, score: int, reason: str)` (score validated `0 ≤ score ≤ 100`, reason max 500 chars), `UploadResponse(resume: ResumeOut, matches: list[MatchResultOut])`, `MatchesResponse(items: list[MatchResultOut], resume: ResumeOut | None)`
- [X] T011 [P] [US1] Implement text extraction in `backend/app/services/resume.py`: `extract_pdf_text(data: bytes) -> str` using `pypdf.PdfReader`; `extract_docx_text(data: bytes) -> str` iterating `Document.paragraphs`; `extract_text(filename: str, data: bytes) -> str` dispatches on lowercase extension (`.pdf` / `.docx`), raises `ValueError` on unknown extension
- [X] T012 [US1] Implement `embed_and_rank(db: AsyncSession, extracted_text: str) -> list[MatchResultOut]` in `backend/app/services/resume.py`: call `generate_embedding(extracted_text[:8000])` (Feature 003 helper); run raw SQL `SELECT posting_id, description, title, company, city, province, term, deadline FROM posting_embeddings pe JOIN postings p ON p.id = pe.posting_id ORDER BY pe.embedding <=> :vec::vector LIMIT 40`; batch Haiku re-rank: send `[{posting_id, title, description[:1500]}]` + resume text truncated to 2000 chars in a single Claude Haiku message requesting JSON array `[{"posting_id": "...", "score": 0-100, "reason": "..."}]`; parse + validate with Pydantic; return top 20 sorted by score DESC
- [X] T013 [US1] Implement `upload_resume(db: AsyncSession, user_id: UUID, filename: str, file_bytes: bytes) -> UploadResponse` in `backend/app/services/resume.py`: validate `len(file_bytes) <= 5_242_880` → raise `HTTPException(400, "FILE_TOO_LARGE")`; validate extension `.pdf`/`.docx` → raise `HTTPException(400, "INVALID_FILE_TYPE")`; call `extract_text` → if blank raise `HTTPException(422, "EXTRACTION_FAILED")`; delete existing `Resume` + cascaded `MatchResult` rows for this user; insert new `Resume` row; call `embed_and_rank`; bulk-insert `MatchResult` rows; return `UploadResponse`
- [X] T014 [US1] Implement `get_matches(db: AsyncSession, user_id: UUID) -> MatchesResponse` in `backend/app/services/resume.py`: query `Resume` by `user_id`; if none return `MatchesResponse(items=[], resume=None)`; query `MatchResult` `WHERE resume_id = :id ORDER BY score DESC LIMIT 20`; join `postings` for display fields; return `MatchesResponse`
- [X] T015 [US1] Create `backend/app/api/resume.py` router (`prefix="/api/resume"`): `POST /` accepts `file: UploadFile = File(...)`, requires `current_user`, calls `upload_resume`, returns `UploadResponse`; `GET /matches` requires `current_user`, calls `get_matches`, returns `MatchesResponse`
- [X] T016 [US1] Import and include resume router in `backend/app/main.py`
- [X] T017 [P] [US1] Create `frontend/src/api/resume.ts`: types `ResumeOut`, `MatchResultOut`, `MatchesResponse`, `UploadResponse`; `useResume()` hook — GET `/api/resume`; `useUploadResume()` mutation — POST `/api/resume` multipart; `useMatches()` hook — GET `/api/resume/matches`
- [X] T018 [P] [US1] Create `frontend/src/components/ResumeUploadForm.tsx`: controlled file input (`accept=".pdf,.docx"`); client-side check rejects files > 5 MB with error message before upload; `useUploadResume()` mutation with loading state; on success invalidates `useResume` and `useMatches` queries; shows stored resume metadata (filename, formatted file_size in KB/MB, formatted uploaded_at) when resume exists
- [X] T019 [US1] Create `frontend/src/pages/MatchResultsPage.tsx`: if `resume === null` show `<ResumeUploadForm />`; else show ranked match cards — each card: score badge (color: green ≥ 70, yellow 40–69, red < 40), one-sentence reason, title, company, city, term, deadline; skeleton loader while `useMatches` is loading; page title "My Matches"
- [X] T020 [US1] Add `/matches` route in `frontend/src/App.tsx` (lazy-loaded `MatchResultsPage`) and "Matches" nav link in `Header` (visible only when `me` exists)

**Checkpoint**: Upload PDF → 200 response with match cards rendered. Return visit loads in < 2 s.

---

## Phase 4: US2 — Ask Follow-up Questions about a Match (Priority: P2)

**Goal**: Student clicks "Ask about this role" on a match card, types a question, and receives a streamed cited response.

**Independent Test**: POST `/api/resume/matches/{posting_id}/ask` with `{"question": "What Python skills match?"}` → `text/event-stream` response with `data: {"delta": "..."}` lines ending in `data: [DONE]`. At least one line references "Resume:" or "Posting:".

### Tests for US2

- [X] T021 [P] [US2] Create `backend/tests/resume/test_resume_qa.py`: happy path streams multiple delta events and final `[DONE]` (mock Anthropic streaming); posting not in user's matches returns 404 `MATCH_NOT_FOUND`; no resume on file returns 404 `RESUME_NOT_FOUND`; empty question string returns 400 `EMPTY_QUESTION`; mocked "don't know" response contains "I don't have enough information"

### Implementation for US2

- [X] T022 [P] [US2] Add `AskRequest(question: str)` schema to `backend/app/schemas/resume.py` with validator: `question` must not be empty or whitespace-only (raise `ValueError`)
- [X] T023 [P] [US2] Create `backend/app/agent/resume_qa.py` with `async def stream_answer(posting_text: str, resume_text: str, question: str) -> AsyncIterator[str]`: system prompt = "Answer ONLY using information from the RESUME and POSTING provided. Cite your source inline using 'Resume: ...' or 'Posting: ...'. If you cannot answer from these sources, respond exactly: 'I don't have enough information to answer that.'"; user message wraps `<posting>{posting_text[:6000]}</posting>` + `<resume>{resume_text[:8000]}</resume>` + `Question: {question}`; call `anthropic.AsyncAnthropic().messages.stream(model="claude-sonnet-4-6", ...)` yielding each `text_delta`; yield `[DONE]` sentinel at end
- [X] T024 [US2] Add `POST /matches/{posting_id}/ask` endpoint to `backend/app/api/resume.py`: validate resume exists for user (404 `RESUME_NOT_FOUND`); validate posting_id in user's `match_results` (404 `MATCH_NOT_FOUND`); validate `body.question` non-empty (400 `EMPTY_QUESTION`); fetch `posting.description` from DB; return `StreamingResponse(stream_answer(...), media_type="text/event-stream")` where each yielded chunk is formatted as `data: {"delta": "<text>"}\n\n` and the sentinel as `data: [DONE]\n\n`
- [X] T025 [P] [US2] Add `useAskAboutPosting(postingId: string)` in `frontend/src/api/resume.ts`: function `askAboutPosting(postingId, question)` that calls `fetch(POST /api/resume/matches/${postingId}/ask)`, reads `response.body` as a `ReadableStream`, parses `data: {...}` SSE lines, calls an `onDelta` callback per token and `onDone` on `[DONE]`
- [X] T026 [US2] Create `frontend/src/components/ConversationPanel.tsx`: "Ask about this role" button on each match card (toggles panel open/closed); inline panel (below card, not modal) pre-loaded with posting title + company as context label; `<textarea>` for question input; "Send" button triggers `askAboutPosting`; response rendered word-by-word as tokens arrive; "Thinking…" spinner until first token; bold any text preceded by `Resume:` or `Posting:` prefix; clears conversation on close
- [X] T027 [US2] Integrate `ConversationPanel` into each match card in `frontend/src/pages/MatchResultsPage.tsx` — one panel per card, independently openable

**Checkpoint**: Click "Ask about this role" on any card, type question, see streamed response with citation.

---

## Phase 5: US3 — View and Delete Stored Resume (Priority: P3)

**Goal**: Student can see stored resume metadata on Account page and permanently delete it with a confirmation modal.

**Independent Test**: GET /api/resume returns filename + file_size + uploaded_at. DELETE /api/resume returns 204, subsequent GET returns 404, GET /api/resume/matches returns `{"items": [], "resume": null}`.

### Tests for US3

- [X] T028 [P] [US3] Add to `backend/tests/resume/test_resume_upload.py`: GET `/api/resume` returns 200 with metadata when resume exists; GET `/api/resume` returns 404 when no resume; DELETE `/api/resume` returns 204 and subsequent GET returns 404; DELETE when no resume returns 404; confirm cross-user isolation — user B cannot GET or DELETE user A's resume

### Implementation for US3

- [X] T029 [P] [US3] Implement `get_resume(db: AsyncSession, user_id: UUID) -> Resume | None` and `delete_resume(db: AsyncSession, user_id: UUID) -> None` (raises `HTTPException(404)` if not found) in `backend/app/services/resume.py`
- [X] T030 [P] [US3] Add `GET /` and `DELETE /` endpoints to `backend/app/api/resume.py`: `GET /` calls `get_resume`, returns `ResumeOut` or 404 `RESUME_NOT_FOUND`; `DELETE /` calls `delete_resume`, returns `Response(status_code=204)` (cascade removes `match_results`)
- [X] T031 [US3] Add resume management section to `frontend/src/pages/AccountSettingsPage.tsx`: call `useResume()` to check if resume exists; if yes show: filename, file_size (formatted), uploaded_at (formatted), "Delete resume" button; clicking opens a `<dialog>` confirmation modal with text "Are you sure? This will remove your resume and match results."; on confirm call `useDeleteResume()` mutation then invalidate `useResume` and `useMatches` queries; on delete success show upload prompt area

**Checkpoint**: Account page shows resume metadata + delete button. Delete removes all data. Matches page shows upload prompt after delete.

---

## Phase 6: Polish & Eval Suite

**Purpose**: Eval suite gates citation rate + factual accuracy. Required by constitution (≥ 80 % pass) and spec SC3/SC4.

- [X] T032 [P] Create `backend/tests/eval/test_resume_match_eval.py` with 25 fixture-based cases: 10 cases where mocked Q&A response contains `Resume:` citation → assert citation regex matches; 5 cases where mocked response contains `Posting:` citation → assert; 5 cases where question is unanswerable → mocked response = "I don't have enough information to answer that." → assert contains expected phrase; 5 cases where `embed_and_rank` returns mocked scores for strong resume (≥70), mid resume (40–69), irrelevant resume (<40) → assert correct score bucket; compute citation_rate = cited_cases / 20; assert `citation_rate >= 0.80`; assert zero factual error cases (all "don't know" mocks return the exact phrase)
- [X] T033 [P] Add `useDeleteResume()` mutation hook to `frontend/src/api/resume.ts` (DELETE `/api/resume`, invalidates `resume` and `matches` query keys on success)
- [X] T034 [P] Verify `backend/pyproject.toml` includes `pypdf>=4.0` and `python-docx>=1.1` in dev fixtures; run `ruff check backend/app/` and `mypy --strict backend/app/` locally — fix any type errors in new files
- [X] T035 Run quickstart.md validation scenarios A–J end-to-end against running Docker stack; mark any failures

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — **blocks all user stories**
- **US1 (Phase 3)**: Depends on Foundational — no dependency on US2/US3
- **US2 (Phase 4)**: Depends on Foundational + US1 (needs resume + match_results data)
- **US3 (Phase 5)**: Depends on Foundational + US1 (needs resume row to delete)
- **Polish (Phase 6)**: Depends on US1 + US2 + US3

### User Story Dependencies

- **US1 (P1)**: Independent after Phase 2
- **US2 (P2)**: Requires US1 complete (needs resume + matches in DB to ask about)
- **US3 (P3)**: Requires US1 complete (needs a resume to delete); independent of US2

### Within Each User Story

- Schemas [P] and text extraction [P] can be written together
- Service functions depend on schemas
- Endpoints depend on service functions
- Frontend hooks [P] and backend work can proceed in parallel
- Frontend pages depend on hooks

### Parallel Opportunities

- T002, T003 (Setup) — parallel
- T004, T005 (Foundational models) — parallel
- T008, T009 (US1 tests) — parallel
- T010, T011 (US1 schemas + text extraction) — parallel
- T017, T018 (US1 frontend hooks + component) — parallel with backend US1 work
- T022, T023 (US2 schema + agent) — parallel
- T025, T026 (US2 frontend hook + component) — parallel
- T029, T030 (US3 service + endpoints) — parallel
- T032, T033, T034 (Polish) — parallel

---

## Parallel Example: US1

```bash
# Launch together (parallel):
Task T010: Create schemas in backend/app/schemas/resume.py
Task T011: Implement text extraction in backend/app/services/resume.py
Task T017: Create frontend hooks in frontend/src/api/resume.ts
Task T018: Create ResumeUploadForm component

# Then sequential:
Task T012: embed_and_rank (depends on T011)
Task T013: upload_resume service (depends on T012)
Task T014: get_matches service
Task T015: API router (depends on T013, T014)
Task T019: MatchResultsPage (depends on T017, T018)
Task T020: Wire route + nav
```

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1: Setup (T001–T003)
2. Complete Phase 2: Foundational (T004–T007) — apply migration
3. Complete Phase 3: US1 (T008–T020)
4. **VALIDATE**: Upload PDF → ranked match cards appear within 30 s; return visit < 2 s
5. Deploy/demo

### Incremental Delivery

1. Setup + Foundational → DB ready
2. US1 complete → Upload + ranked matches (MVP)
3. US2 complete → Streaming Q&A with citations
4. US3 complete → Resume metadata view + delete
5. Eval suite + polish → CI gates green

---

## Notes

- Tasks marked [P] touch different files and have no inter-task dependencies
- [Story] labels trace each task to a spec user story
- Anthropic and OpenAI SDK calls MUST be mocked in all unit/integration tests (no live API calls)
- The eval suite (T032) counts as part of `pytest -q` — CI will fail if citation_rate < 80 %
- Commit after each phase checkpoint using conventional commit messages

---

## Phase 7: Convergence

- [X] T036 Move `sample_pdf_bytes` and `sample_docx_bytes` pytest fixtures from `backend/tests/fixtures/resume/conftest.py` to `backend/tests/resume/conftest.py` so pytest fixture discovery works for tests in `backend/tests/resume/` (pytest only loads conftest.py from ancestor directories, not siblings) per tasks.md T002/T003 (partial)
- [X] T037 [P] In `backend/app/models/match_result.py` replace `Index("idx_match_results_resume_score", "resume_id", desc("score"))` with `Index("idx_match_results_resume_score", "resume_id", "score")` — `desc()` on a bare string is not valid SQLAlchemy Index DDL and will cause `Base.metadata.create_all` (used in test conftest) to fail; the Alembic migration already creates the correct `score DESC` index via raw SQL per plan.md Foundational (partial)
- [X] T038 [P] In `backend/app/models/resume.py` merge the two separate `from sqlalchemy import` statements (lines 4 and 6) into one to satisfy ruff I001 lint gate per Constitution I (partial)
