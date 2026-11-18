---

description: "Task list for co-op matching and a job board layout"
---

# Tasks: Co-op Matching and a Job Board Layout

**Input**: Design documents from `/specs/007-coop-matching-job-board/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md

**Tests**: Included. Each reader has tests built from real titles and resumes that broke it.

**Organization**: Grouped by user story. Written after the code, so finished work is ticked.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Foundational

- [X] T001 Migration `0009_resume_preferences.py` for `resumes.preferences`
- [X] T002 Migration `0010_postings_country_education.py` for `country`, `fields_of_study`, `grad_years` with an
  index on `country`
- [X] T003 Migration `0011_term_season_workday.py` for generated `season` and `term_start` and a nullable
  `duration_months`
- [X] T004 Migration `0013_real_lengths_simplify.py` for `first_seen_at` and real lengths
- [X] T005 [P] `backend/app/services/categories.py` with job type title patterns, tuned on the live titles
- [X] T006 [P] `backend/app/services/education.py` with `PROGRAMS`, `detect_education()`, fields and grad years from
  job text

**Checkpoint**: Migrations round trip and `alembic check` is clean

---

## Phase 2: User Story 1 - Ranked for my program, grad year and term (Priority: P1) 🎯 MVP

### Tests ⚠️

- [X] T007 [P] [US1] `backend/tests/ingest/test_education.py` (stock purchase program, undergraduate, graduate
  students, work term phrases)
- [X] T008 [P] [US1] `backend/tests/ingest/test_terms.py` (S27, Fall '27, May to August, 12 weeks, one year)
- [X] T009 [P] [US1] `backend/tests/resume/test_preferences.py` and `backend/tests/resume/test_coop_matching.py`

### Implementation

- [X] T010 [US1] `backend/app/ingest/terms.py` and call it on import and re import in `backend/app/ingest/runner.py`
- [X] T011 [US1] Store fields, grad years, location and country on every import in the runner
- [X] T012 [US1] `JobPreferences`, `effective_preferences()`, `preference_filters()` in `backend/app/services/resume.py`
- [X] T013 [US1] `_student_fit` weights and `fit_notes()`; rebalance after scores bunched at 100
- [X] T014 [US1] Lenient matching: other grad years minus 10 with a note, up to 60 matches
- [X] T015 [US1] `PUT /api/resume/preferences` in `backend/app/api/resume.py`
- [X] T016 [US1] Resume page steps (About you, What are you looking for, upload) and "why it fits" on
  `MatchCard` in `frontend/src/pages/ResumePage.tsx`

---

## Phase 3: User Story 2 - Job board filters (Priority: P2)

### Tests ⚠️

- [X] T017 [P] [US2] Filter and sort tests in `backend/tests/api/test_postings.py` and
  `backend/tests/api/test_terms_api.py`
- [X] T018 [P] [US2] `frontend/tests/FilterBar.test.tsx` and `frontend/tests/PostingCard.test.tsx`
- [X] T019 [P] [US2] Playwright tests for the sidebar, details panel and phone layout in `frontend/e2e/`

### Implementation

- [X] T020 [US2] New filters, `include_unstated`, new sorts and `page_size` 100 in
  `backend/app/services/postings.py` and `backend/app/schemas/posting.py`
- [X] T021 [US2] Filter counts and employer list in `get_filter_meta()`, cached 2 minutes
- [X] T022 [US2] Jobs page layout in `frontend/src/pages/PostingsListPage.tsx` with `?job=` in the URL
- [X] T023 [US2] `FilterBar.tsx` sidebar with counts, chips on phones only, Clear all
- [X] T024 [US2] Three line `PostingCard.tsx` and `PostingDetailView.tsx` with the postmark and days left bar
- [X] T025 [US2] Remove the filter drawer and the sign in popup, add `frontend/src/pages/SignInPage.tsx` with a safe
  `?next=`
- [X] T026 [US2] Design pass with the Impeccable skill, written into `DESIGN.md` and `PRODUCT.md`

---

## Phase 4: User Story 3 - Make my resume fit (Priority: P3)

- [X] T027 [P] [US3] `backend/tests/resume/test_align.py`
- [X] T028 [US3] `backend/app/services/align.py` and `GET /api/resume/align/{posting_id}`
- [X] T029 [US3] `frontend/src/components/ResumeFitPanel.tsx`, loaded only when opened

---

## Phase 5: User Story 4 - What is new (Priority: P4)

- [X] T030 [P] [US4] `backend/tests/api/test_updates_api.py`
- [X] T031 [US4] `added_since` filter, Newly added sort, `backend/app/services/feed.py` and `GET /api/postings/feed.rss`
- [X] T032 [US4] `frontend/src/components/JobUpdates.tsx` and `frontend/src/utils/visits.ts`

---

## Phase N: Polish

- [X] T033 Fix deadlines showing a day early in Canada (plain dates read as UTC) with a test
- [X] T034 Perf test with every filter, cache job type counts after a 374 ms p95
- [X] T035 [P] Screenshots and docs: README, guides, PROJECT_GUIDE, DESIGN.md
- [X] T036 Log entries in `docs/agentic-workflow.md`
- [ ] T037 Show the fit score broken into its parts on each match (PROJECT_GUIDE section 12)
- [ ] T038 Unsave from the jobs list (the list knows `is_saved` but not the saved row id)

## Notes

- T037 and T038 are left open on purpose so `/speckit-converge` can pick them up
