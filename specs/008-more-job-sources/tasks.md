---

description: "Task list for jobs from every field, from public sources"
---

# Tasks: Jobs From Every Field, From Public Sources

**Input**: Design documents from `/specs/008-more-job-sources/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md

**Tests**: Included. Every adapter has recorded reply tests and every location bug has a regression test.

**Organization**: Grouped by user story. Written after the code, so finished work is ticked.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Foundational

- [X] T001 Check robots.txt and terms for each source before writing its adapter (research.md table)
- [X] T002 Add each adapter type to the CHECK constraint in the model and a migration (0007, 0010 to 0016)
- [X] T003 Load boards in two `jsonb_to_recordset` statements in `backend/seed/__main__.py`, repoint moved boards

---

## Phase 2: User Story 1 - Employers' own boards (Priority: P1) 🎯 MVP

### Tests ⚠️

- [X] T004 [P] [US1] `backend/tests/ingest/test_boards.py` (Greenhouse, Lever, Ashby, SmartRecruiters, location
  parsing, Vancouver WA)
- [X] T005 [P] [US1] `backend/tests/ingest/test_workday.py` (scope, Canada split over 2,000, store codes)
- [X] T006 [P] [US1] `backend/tests/ingest/test_more_sources.py` (Recruitee, BambooHR, Rippling, Oracle, GitHub list)
- [X] T007 [P] [US1] `backend/tests/ingest/test_runner.py` and `test_seed.py` (run twice, estimated deadlines,
  re read fields)

### Implementation

- [X] T008 [US1] Greenhouse, Lever and Ashby adapters and `choose_location()` in `backend/app/ingest/boards.py`
- [X] T009 [US1] SmartRecruiters adapter, list then details six at a time
- [X] T010 [US1] `backend/app/ingest/workday.py`, about 50 big employers checked live
- [X] T011 [US1] `backend/app/ingest/ats.py` for Recruitee, BambooHR and Rippling
- [X] T012 [US1] `backend/app/ingest/oracle.py`
- [X] T013 [US1] Estimated deadlines flagged in `low_confidence_fields` in `backend/app/ingest/runner.py`
- [X] T014 [US1] `backend/seed/job_boards.py` hand picked list (185 employers)
- [X] T015 [US1] `backend/seed/discover_boards.py` with Common Crawl, retries on 502 and 504, `--lists`, adds to
  `discovered_boards.json`

**Checkpoint**: Thousands of real jobs from employers' own boards

---

## Phase 3: User Story 2 - Every program (Priority: P2)

- [X] T016 [P] [US2] `backend/tests/ingest/test_jobbank.py`
- [X] T017 [US2] `backend/app/ingest/jobbank.py` with student and apprentice filters and about 30 program searches,
  5 seconds apart, one retry
- [X] T018 [US2] `rolling_window` support in the runner (21 days for Job Bank)
- [X] T019 [US2] "(student)" and "(apprentice)" in titles so `students_only` finds them
- [X] T020 [US2] New job types Health, Public, Trades and Hospitality, wider title patterns in
  `backend/app/services/categories.py`
- [X] T021 [US2] New programs (health, education, hospitality, law and justice and others) in
  `backend/app/services/education.py`
- [X] T022 [US2] About 75 non tech skills in `backend/seed/skills.py`

---

## Phase 4: User Story 3 - Lists and job APIs (Priority: P3)

- [X] T023 [P] [US3] `backend/tests/ingest/test_simplify.py`, `test_workable.py`, `test_job_apis.py`
- [X] T024 [US3] `backend/app/ingest/workable.py` (Canada, plus US student roles)
- [X] T025 [US3] `backend/app/ingest/simplify.py` (terms kept, past terms dropped, 180 day stale skip, season only
  lists get a year)
- [X] T026 [US3] `backend/app/ingest/github_lists.py` for README tables
- [X] T027 [US3] `backend/app/ingest/themuse.py` (90 day cutoff, keep what was read on a 429)
- [X] T028 [US3] `backend/app/ingest/himalayas.py` (only jobs whose country list names Canada)
- [X] T029 [US3] `backend/app/ingest/adzuna.py`, only with the owner's keys

---

## Phase 5: User Story 4 - Right place (Priority: P4)

- [X] T030 [P] [US4] Regression tests for Gap "ON Coral Ridge", Walmart in Ontario OH and Hamilton AL, Fergus store
  codes, spaces around employer names
- [X] T031 [US4] Trust the country Workday, Lever and SmartRecruiters give
- [X] T032 [US4] Workday lists Canada on its own, then each province, when the list hides Canadian jobs
- [X] T033 [US4] "Student Success Manager" and US recruiter roles no longer count as student jobs

---

## Phase N: Polish

- [X] T034 Scheduler 3 at a time, never run first then oldest first, in `backend/app/jobs.py` (shared with 006)
- [X] T035 Re run `discover_boards.py` to grow `discovered_boards.json` to about 1,500 boards
- [X] T036 [P] README sources table, owner handbook, PROJECT_GUIDE section 6.4
- [X] T037 Log entries in `docs/agentic-workflow.md`
- [ ] T038 Re run `discover_boards.py` with the newer finders (SmartRecruiters, Recruitee, BambooHR, Rippling,
  Oracle) to completion. The 2026-10-17 run was stopped by low memory before checking what it found
- [ ] T039 An Admin page form for adding sources and reviewing low confidence fields (today it is SQL or a seed line)
- [ ] T040 Schools' public co-op feeds where their terms allow

## Notes

- T038 to T040 are left open on purpose so `/speckit-converge` can pick them up
