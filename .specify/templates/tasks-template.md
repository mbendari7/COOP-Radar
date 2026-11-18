---

description: "Task list template for feature implementation"
---

# Tasks: [FEATURE NAME]

**Input**: Design documents from `/specs/[###-feature-name]/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: In CoopRadar tests are not optional. The constitution says every new endpoint gets a happy path and a
bad request test, and every bug fix gets a regression test. Write the test task before the code task it covers.

**Organization**: Tasks are grouped by user story so each story can be built and tested on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run at the same time as other [P] tasks (different files, nothing it waits on)
- **[Story]**: Which user story the task is for (US1, US2, US3)
- Every task names the real file it changes

## Path Conventions

- Backend code: `backend/app/api/`, `backend/app/services/`, `backend/app/schemas/`, `backend/app/models/`,
  `backend/app/ingest/`, `backend/app/agent/`
- Migrations: `backend/alembic/versions/00NN_short_name.py` (use the `/db-migration` skill)
- Seed data: `backend/seed/`
- Backend tests: `backend/tests/api/`, `backend/tests/ingest/`, `backend/tests/resume/`, `backend/tests/eval/`,
  `backend/tests/perf/`, recorded replies in `backend/tests/fixtures/`
- Frontend code: `frontend/src/api/`, `frontend/src/pages/`, `frontend/src/components/`
- Frontend tests: `frontend/tests/` (Vitest), `frontend/e2e/*.e2e.ts` (Playwright)
- Docs that carry numbers: `README.md`, `guides/*/README.md`, `docs/PROJECT_GUIDE.md`, `docs/DEPLOY.md`

<!--
  The tasks below are examples of the shape only. /speckit-tasks MUST replace them with real tasks from:
  - the user stories and priorities in spec.md
  - the stack and structure in plan.md
  - the tables in data-model.md
  - the endpoints in contracts/api.md

  Keep them grouped by user story so each story can be built, tested and shipped on its own.
  Do not leave these example tasks in the real tasks.md.
-->

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Anything every story needs before work starts

- [ ] T001 Add [library] to `backend/pyproject.toml` with the reason from research.md
- [ ] T002 [P] Add recorded replies for [source] under `backend/tests/fixtures/ingest/`
- [ ] T003 [P] Add any new env vars to `backend/app/config.py` and `.env.example`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The parts every story depends on

**⚠️ CRITICAL**: No user story work starts until this phase is done

- [ ] T004 Add the [column or table] to `backend/app/models/[model].py` with its index in `__table_args__`
- [ ] T005 Write migration `backend/alembic/versions/00NN_[name].py` with the same index, then upgrade, downgrade,
  upgrade and `alembic check`
- [ ] T006 [P] Add request and reply schemas in `backend/app/schemas/[area].py`
- [ ] T007 [P] Add the TypeScript types and hook in `frontend/src/api/[area].ts`

**Checkpoint**: `alembic check` is clean and the app starts with `python start.py`

---

## Phase 3: User Story 1 - [Title] (Priority: P1) 🎯 MVP

**Goal**: [What this story gives the student]

**Independent Test**: [How to check it on its own]

### Tests for User Story 1 ⚠️

> **Write these first and watch them fail before the code exists**

- [ ] T008 [P] [US1] Endpoint test for [endpoint] in `backend/tests/api/test_[area].py` (happy path and a bad request)
- [ ] T009 [P] [US1] Component test for [component] in `frontend/tests/[Component].test.tsx`

### Implementation for User Story 1

- [ ] T010 [US1] Add [function] to `backend/app/services/[area].py` (filters and sorting in SQL, whitelisted)
- [ ] T011 [US1] Add the route in `backend/app/api/[area].py` that calls the service and nothing else
- [ ] T012 [US1] Build [component] in `frontend/src/components/[Component].tsx` with loading, empty and error states
- [ ] T013 [US1] Wire it into `frontend/src/pages/[Page].tsx` with the state kept in the URL

**Checkpoint**: Story 1 works on its own and its tests pass

---

## Phase 4: User Story 2 - [Title] (Priority: P2)

**Goal**: [What this story gives the student]

**Independent Test**: [How to check it on its own]

### Tests for User Story 2 ⚠️

- [ ] T014 [P] [US2] Test for [behaviour] in `backend/tests/[folder]/test_[name].py`

### Implementation for User Story 2

- [ ] T015 [US2] [Change] in `backend/app/[folder]/[file].py`
- [ ] T016 [US2] [Change] in `frontend/src/[folder]/[file].tsx`

**Checkpoint**: Stories 1 and 2 both work on their own

---

## Phase 5: User Story 3 - [Title] (Priority: P3)

**Goal**: [What this story gives the student]

**Independent Test**: [How to check it on its own]

### Tests for User Story 3 ⚠️

- [ ] T017 [P] [US3] Test for [behaviour] in `backend/tests/[folder]/test_[name].py`

### Implementation for User Story 3

- [ ] T018 [US3] [Change] in `backend/app/[folder]/[file].py`

**Checkpoint**: Every story works on its own

---

[Add more story phases the same way]

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Things that touch every story

- [ ] TXXX Run the perf budget `pytest -q -m perf -s` and add an index if p95 is over 300 ms
- [ ] TXXX [P] Add or update a Playwright test in `frontend/e2e/` and run `npm run test:e2e` against a local site
- [ ] TXXX [P] Check the new UI at 375 px and with only the keyboard
- [ ] TXXX Update the numbers in `README.md`, the guides, `docs/PROJECT_GUIDE.md` and `docs/DEPLOY.md`
- [ ] TXXX Run every check in `CLAUDE.md` and the steps in quickstart.md
- [ ] TXXX Write the `docs/agentic-workflow.md` entry with `/log-agentic-work`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Nothing to wait on
- **Foundational (Phase 2)**: Waits on Setup and blocks every story
- **User Stories (Phase 3 and up)**: Wait on Foundational
  - They can go at the same time if more than one person is working
  - Or one after the other in priority order (P1, then P2, then P3)
- **Polish (last phase)**: Waits on the stories you want in this release

### User Story Dependencies

- **User Story 1 (P1)**: Starts after Foundational. Does not need the other stories
- **User Story 2 (P2)**: Starts after Foundational. Can use Story 1 but still tests on its own
- **User Story 3 (P3)**: Starts after Foundational. Can use Stories 1 and 2 but still tests on its own

### Within Each User Story

- Tests first, and they fail before the code exists
- Models and migration, then services, then routes, then hooks, then UI
- Finish the story before moving to the next priority

### Parallel Opportunities

- Setup and Foundational tasks marked [P] can run together
- Once Foundational is done, stories can run together
- Tests in one story marked [P] can be written together
- Backend and frontend tasks in one story can usually run together once the schema is agreed

---

## Parallel Example: User Story 1

```bash
# Write the tests for Story 1 together:
Task: "Endpoint test for [endpoint] in backend/tests/api/test_[area].py"
Task: "Component test for [component] in frontend/tests/[Component].test.tsx"

# Then the backend service and the frontend hook together:
Task: "Add [function] to backend/app/services/[area].py"
Task: "Add the hook in frontend/src/api/[area].ts"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Finish Setup
2. Finish Foundational (this blocks every story)
3. Finish Story 1
4. **Stop and check**: test Story 1 on its own with `python start.py`
5. Push it if it is ready

### Incremental Delivery

1. Setup and Foundational, so the base is ready
2. Story 1, test it, push it (the MVP)
3. Story 2, test it, push it
4. Story 3, test it, push it
5. Each story adds something without breaking the ones before

### Checks before every push

```bash
cd backend && ruff check . && mypy app && pytest -q -m 'not perf' && alembic check
cd frontend && npm run lint && npm run typecheck && npm test && npm run build
```

---

## Notes

- [P] tasks touch different files and do not wait on each other
- The [Story] label ties each task to a story so you can trace it back
- Each story should be finished and tested on its own
- Watch the tests fail before writing the code
- Commit after each task or small group with a conventional message and no AI attribution
- Stop at any checkpoint to test the story on its own
- Avoid vague tasks, two tasks editing the same file at once, and stories that only work together
