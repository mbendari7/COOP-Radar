---

description: "Task list for bring your own AI key and a resume first site"
---

# Tasks: Bring Your Own AI Key and a Resume First Site

**Input**: Design documents from `/specs/005-byok-resume-first/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md

**Tests**: Included for every endpoint and every provider error, as the constitution asks.

**Organization**: Grouped by user story. This list was written after the code, so finished work is ticked.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run at the same time (different files)
- **[Story]**: Which user story it is for

---

## Phase 1: Setup

- [X] T001 Add `openai` and `google-genai` to `backend/pyproject.toml` next to `anthropic` (reason in research.md)
- [X] T002 [P] Add `DEMO_ENABLED` and `AI_DAILY_LIMIT` to `backend/app/config.py` and `.env.example`

---

## Phase 2: Foundational

- [X] T003 Write `backend/app/ai.py`: `AICredentials` (key hidden from `repr()`), `ai_credentials()` dependency
  reading `X-AI-*` headers with the owner key as fallback, `complete()`, `stream()`, `list_models()`,
  `recommended_model()`, `_translate()` for errors
- [X] T004 [P] Tests for `ai.py` with each SDK faked, including Google's 400 `API_KEY_INVALID` in
  `backend/tests/api/test_ai.py`
- [X] T005 Migration `backend/alembic/versions/0006_add_demo_users.py` for `users.is_demo`
- [X] T006 Migration `backend/alembic/versions/0007_job_boards_and_insights.py` for `resumes.insights` and the board
  adapter types
- [X] T007 [P] `backend/app/services/usage.py` with `consume_ai_quota()` on the owner's key only

**Checkpoint**: `alembic check` clean, `ai.py` tests pass

---

## Phase 3: User Story 1 - Matches with no account and no key (Priority: P1) 🎯 MVP

### Tests for User Story 1 ⚠️

- [X] T008 [P] [US1] Free matching tests (no key, skill reasons, senior titles ranked lower) in
  `backend/tests/resume/test_match_service.py`
- [X] T009 [P] [US1] Guest account tests (made on demand, rate limited, session works on the next request) in
  `backend/tests/api/test_guest.py`
- [X] T010 [P] [US1] Guest then upload flow in `frontend/tests/ResumePage.test.tsx`

### Implementation for User Story 1

- [X] T011 [US1] Stage 1 SQL skill coverage in `backend/app/services/resume.py → find_candidates()`
- [X] T012 [US1] Make AI optional on upload (`ai_credentials("rank", optional=True)`) in `backend/app/api/resume.py`
- [X] T013 [US1] Free insights (skills found, top missing skills with `unnest ... GROUP BY`) in
  `backend/app/services/insights.py`
- [X] T014 [US1] `POST /api/auth/guest` and cleanup of old temporary accounts in `backend/app/services/demo.py`
- [X] T015 [US1] Rebuild `frontend/src/pages/ResumePage.tsx` as the main page with `ResumeDropzone` (guest login
  then upload)
- [X] T016 [US1] `students_only` and `hide_senior` filters in `backend/app/services/postings.py`

**Checkpoint**: A signed out visitor gets matches with no key

---

## Phase 4: User Story 2 - My own AI key (Priority: P2)

### Tests for User Story 2 ⚠️

- [X] T017 [P] [US2] `POST /api/ai/check` tests in `backend/tests/api/test_ai.py`
- [X] T018 [P] [US2] Insights POST, rematch and ask modes tests in `backend/tests/resume/test_insights.py` and
  `backend/tests/resume/test_resume_qa.py`
- [X] T019 [P] [US2] Rerank output handling cases (made up ids, duplicates, scores out of range) in
  `backend/tests/eval/test_resume_match_eval.py`
- [X] T020 [P] [US2] AI key store and page tests in `frontend/tests/`

### Implementation for User Story 2

- [X] T021 [US2] `backend/app/api/ai.py` with `POST /api/ai/check`, rate limited per network
- [X] T022 [US2] Stage 2 `rank_with_ai()` through `ai.complete()` with output checks in `backend/app/services/resume.py`
- [X] T023 [US2] `POST /api/resume/rematch` and `POST /api/resume/insights` in `backend/app/api/resume.py`
- [X] T024 [US2] Modes `question`, `tailor`, `cover_letter` in `backend/app/agent/resume_qa.py` streaming through
  `ai.stream()`
- [X] T025 [US2] `frontend/src/api/aiKey.ts` (session or local storage, `aiHeaders()`) and
  `frontend/src/pages/AiKeyPage.tsx` with `PROVIDER_GUIDES`
- [X] T026 [US2] `components/ConversationPanel.tsx` and `components/RichText.tsx` (safe Markdown subset)

**Checkpoint**: All three providers work with a real key and fail cleanly with a fake one

---

## Phase 5: User Story 3 - Demo account (Priority: P3)

- [X] T027 [P] [US3] Demo and claim tests in `backend/tests/api/test_auth.py` and `backend/tests/api/test_me.py`
- [X] T028 [US3] `POST /api/auth/demo` with a filled tracker, resume and matches in `backend/app/services/demo.py`
- [X] T029 [US3] `POST /api/me/claim` in `backend/app/api/me.py`
- [X] T030 [US3] `DemoButton`, `DemoBanner` and `ClaimAccountForm` in `frontend/src/components/`

---

## Phase 6: User Story 4 - Owner key with a limit (Priority: P4)

- [X] T031 [P] [US4] Daily limit tests in `backend/tests/api/test_ai.py`
- [X] T032 [US4] Call `consume_ai_quota()` only when the owner's key is used, in each AI route
- [X] T033 [US4] `GET /api/config` in `backend/app/api/meta.py` and read it in `frontend/src/api/meta.ts`

---

## Phase N: Polish

- [X] T034 Live check of fake keys against the real Anthropic, OpenAI and Google APIs
- [X] T035 [P] Docs: README, guides, `docs/AI_KEYS.md` (later folded into the guides), CLAUDE.md, the `agent-tools`
  skill
- [X] T036 Log entry in `docs/agentic-workflow.md`
- [ ] T037 Check a full answer from each provider with a real key (not done, needs paid or free keys)

---

## Dependencies & Execution Order

- Phase 2 (`ai.py` and the migrations) blocks every story
- Story 1 does not need any AI and was built first
- Story 2 needs `ai.py`. Stories 3 and 4 only need Phase 2

## Notes

- This list was written after the code from the commits and the workflow log
- T037 is left open on purpose so `/speckit-converge` can pick it up
