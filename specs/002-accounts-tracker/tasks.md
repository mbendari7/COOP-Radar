# Tasks: Accounts & Application Tracker

**Input**: Design documents from `/specs/002-accounts-tracker/`

**Prerequisites**: plan.md ✓ spec.md ✓ research.md ✓ data-model.md ✓ contracts/api.md ✓

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US4)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add new dependencies and wire up the shared pieces that every user story needs.

- [X] T001 Add `argon2-cffi>=23` to `[project.dependencies]` in `backend/pyproject.toml`
- [X] T002 [P] Create `backend/app/deps.py` — `get_current_user(request, db, redis)` FastAPI dependency: reads `session` cookie → `GET session:<token>` from Redis → SELECT user → reset EXPIRE 7d → return `User`; raises `HTTP 401` with `{"detail":"Not authenticated","code":"NOT_AUTHENTICATED"}` if cookie absent or Redis key missing
- [X] T003 [P] Create `backend/app/redis.py` — async Redis client: `create_redis_pool()` factory returning `redis.asyncio.Redis`; `get_redis()` FastAPI dependency yielding the pool; pool stored on `app.state.redis`; opened in lifespan startup, closed in shutdown

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: ORM models, Alembic migration, and Pydantic schemas — must be complete before any endpoint can be written.

⚠️ CRITICAL: No user story work can begin until this phase is complete.

- [X] T004 Create `backend/app/models/user.py` — `User` SQLAlchemy mapped class: `id UUID PK default uuid4`, `email TEXT NOT NULL UNIQUE`, `hashed_password TEXT NOT NULL`, `created_at TIMESTAMPTZ server_default NOW()`; `saved_postings` relationship back_populates; import into `backend/app/db.py` so `Base.metadata` sees it
- [X] T005 [P] Create `backend/app/models/saved_posting.py` — `ApplicationStatus(str, Enum)` with values `applied/interviewing/offer/rejected`; `SavedPosting` mapped class: `id UUID PK`, `user_id UUID FK→users.id ON DELETE CASCADE NOT NULL`, `posting_id UUID FK→postings.id ON DELETE CASCADE NOT NULL`, `status Enum(ApplicationStatus) nullable`, `saved_at TIMESTAMPTZ server_default NOW()`; `user` + `posting` relationships; UNIQUE constraint `(user_id, posting_id)`
- [X] T006 Create `backend/alembic/versions/0002_add_auth.py` — Alembic migration: upgrade creates `application_status_enum` ENUM type, `users` table (`id`, `email`, `hashed_password`, `created_at`), `saved_postings` table (`id`, `user_id`, `posting_id`, `status`, `saved_at`), UNIQUE `ux_saved_postings_user_posting(user_id, posting_id)`, indexes `idx_users_email` (unique), `idx_saved_postings_user_id`, `idx_saved_postings_posting_id`, `idx_saved_postings_status`, `idx_saved_postings_saved_at DESC`; downgrade drops tables then type; use `op.execute()` for the ENUM and GENERATED expressions
- [X] T007 [P] Create `backend/app/schemas/auth.py` — Pydantic schemas: `RegisterIn(email: EmailStr, password: str = Field(min_length=10))`, `LoginIn(email: EmailStr, password: str)`, `UserOut(id: UUID, email: str, created_at: datetime, model_config from_attributes=True)`, `ChangePasswordIn(current_password: str, new_password: str = Field(min_length=10))`, `DeleteAccountIn(password: str)`
- [X] T008 [P] Create `backend/app/schemas/saved_posting.py` — Pydantic schemas: `SaveIn(posting_id: UUID)`, `StatusUpdateIn(status: ApplicationStatus | None)`, `SavedPostingOut(id: UUID, saved_at: datetime, status: ApplicationStatus | None, posting: PostingListItem, model_config from_attributes=True)`, `SavedPostingsPage(items: list[SavedPostingOut], total: int, page: int, page_size: int, status_counts: dict[str, int])`; import `PostingListItem` from `app.schemas.posting`
- [X] T009 Update `backend/app/schemas/posting.py` — add `is_saved: bool | None = None` field to `PostingListItem`; this field is omitted (None) for unauthenticated responses and explicitly True/False for authenticated ones

**Checkpoint**: Models, migration, and schemas ready — user story implementation can now begin.

---

## Phase 3: User Story 1 — Register & Log In (Priority: P1) 🎯 MVP

**Goal**: Students can create accounts and authenticate via HTTP-only cookie sessions stored in Redis.

**Independent Test**: `POST /api/auth/register` → 201 + cookie; `POST /api/auth/login` → 200 + cookie; `GET /api/saved` without cookie → 401; `POST /api/auth/logout` → 204 + cookie cleared; subsequent `GET /api/saved` → 401.

### Implementation

- [X] T010 [US1] Create `backend/app/services/auth.py`
- [X] T011 [US1] Create `backend/app/api/auth.py`
- [X] T012 [US1] Create `backend/app/api/me.py`
- [X] T013 [US1] Update `backend/app/main.py`
- [X] T014 [US1] Create `backend/tests/api/test_auth.py`
- [X] T015 [P] [US1] Create `frontend/src/api/auth.ts`
- [X] T016 [P] [US1] Create `frontend/src/components/AuthModal.tsx`
- [X] T017 [P] [US1] Update `frontend/src/App.tsx`

**Checkpoint**: Register, login, logout, and protected-endpoint guard all work end-to-end.

---

## Phase 4: User Story 2 — Save & Unsave Postings (Priority: P2)

**Goal**: Logged-in students can bookmark postings; bookmarks appear on a `/saved` page.

**Independent Test**: Login → bookmark a posting from list → `GET /api/saved` returns it → click again to unsave → `GET /api/saved` returns empty; unauthenticated user clicks bookmark → AuthModal opens.

### Implementation

- [X] T018 [US2] Create `backend/app/services/saved_postings.py`
- [X] T019 [US2] Create `backend/app/api/saved.py`
- [X] T020 [US2] Update `backend/app/api/postings.py` + `backend/app/services/postings.py`
- [X] T021 [US2] Create `backend/tests/api/test_saved.py`
- [X] T022 [P] [US2] Create `frontend/src/api/saved.ts`
- [X] T023 [P] [US2] Create `frontend/src/components/BookmarkButton.tsx`
- [X] T024 [P] [US2] Create `frontend/src/pages/SavedPostingsPage.tsx`
- [X] T025 [P] [US2] Update `frontend/src/components/PostingsTable.tsx`
- [X] T026 [P] [US2] Update `frontend/src/components/PostingCard.tsx`
- [X] T027 [P] [US2] Update `frontend/src/App.tsx` router + nav

**Checkpoint**: Bookmark/unbookmark works from list and /saved page; unauthenticated user is prompted to log in.

---

## Phase 5: User Story 3 — Track Application Status (Priority: P3)

**Goal**: Students can assign and update `applied / interviewing / offer / rejected` status on saved postings; Saved page shows counts and can be filtered by status.

**Independent Test**: Login → save posting → set status "applied" via `PATCH /api/saved/:id/status` → `GET /api/saved` shows `status: "applied"` and `status_counts.applied: 1`; change to "interviewing" → badge updates; `GET /api/saved?status=interviewing` returns only that posting; set status to null → badge cleared.

### Implementation

- [X] T028 [US3] Create `frontend/src/components/StatusBadge.tsx`
- [X] T029 [P] [US3] StatusBadge integrated into `frontend/src/pages/SavedPostingsPage.tsx` (done in T024)

**Checkpoint**: Status badge renders on Saved page, updates without reload, filter by status works.

---

## Phase 6: User Story 4 — Account Management (Priority: P4)

**Goal**: Students can change their password and permanently delete their account (all data removed immediately).

**Independent Test**: Login → change password → logout → login with new password succeeds → delete account → attempt login with new password fails with 401.

### Implementation

- [X] T030 [US4] Verified `backend/app/services/auth.py` has `change_password` and `delete_account`
- [X] T031 [US4] Create `frontend/src/pages/AccountSettingsPage.tsx`
- [X] T032 [P] [US4] `/account` route added to `frontend/src/App.tsx` router
- [X] T033 [US4] Create `backend/tests/api/test_me.py`

**Checkpoint**: Change password and delete account both work; deleted account cannot log back in.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T034 [P] Update `frontend/src/api/postings.ts` — add `is_saved?: boolean | null` to `PostingListItem`
- [X] T035 [P] Update `backend/tests/api/test_postings.py` — add `is_saved` test for unauthenticated requests
- [ ] T036 [P] Run `docker compose exec api alembic upgrade head` and confirm migration clean; run `docker compose exec api pytest -q -m "not perf"` green; run `docker compose exec web npm test` green
- [ ] T037 Manual quickstart.md validation — execute all 9 curl steps from `specs/002-accounts-tracker/quickstart.md`
- [ ] T038 [P] Frontend smoke tests — register, bookmark, /saved, status badge, logout

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 — BLOCKS all user stories
- **Phase 3 (US1 — Auth)**: Depends on Phase 2 — also blocks US2/US3/US4 (login required)
- **Phase 4 (US2 — Save/Unsave)**: Depends on Phase 3 (needs `get_current_user`) — blocks US3
- **Phase 5 (US3 — Status)**: Depends on Phase 4 (StatusBadge lives on SavedPostingsPage)
- **Phase 6 (US4 — Account Mgmt)**: Depends on Phase 3 only — can proceed in parallel with US2/US3
- **Phase 7 (Polish)**: Depends on all user story phases complete

### User Story Dependencies

- **US1 (P1)**: After Foundational phase — no story dependencies
- **US2 (P2)**: After US1 (needs auth cookie + get_current_user)
- **US3 (P3)**: After US2 (status lives on saved postings)
- **US4 (P4)**: After US1 (needs authenticated user), independent of US2/US3

### Parallel Opportunities

- T002 + T003 (deps.py + redis.py) — different files, run together
- T004 + T005 (User + SavedPosting models) — different files, run together
- T007 + T008 + T009 (schema files) — different files, run together after T004/T005
- T015 + T016 + T017 (frontend auth hooks, modal, header) — different files, run together
- T022 + T023 + T024 + T025 + T026 + T027 (frontend save pieces) — different files, run together

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T003)
2. Complete Phase 2: Foundational (T004–T009)
3. Complete Phase 3: US1 auth (T010–T017)
4. **STOP and VALIDATE**: run quickstart steps 1–8; confirm register/login/logout/401
5. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 (auth) → validated with curl + automated tests → Demo checkpoint
3. Add US2 (save/unsave) → `/saved` page working → Demo checkpoint
4. Add US3 (status tracking) → status badges + filter → Demo checkpoint
5. Add US4 (account management) → change password + delete account → Demo checkpoint
6. Polish → full quickstart validation + CI green

---

## Notes

- [P] tasks touch different files — safe to parallelize within a phase
- US4 (account management) can overlap with US2/US3 since it only needs US1
- `is_saved` on `GET /api/postings` requires `get_optional_user` dep — do not break unauthenticated access (FR-015)
- Cookie must be set with `response.set_cookie(...)` not via headers directly — FastAPI's `Response` parameter pattern
- Redis `EXPIRE` reset on every authenticated request implements the rolling 7-day session (FR-004)
- argon2-cffi `PasswordHasher()` with defaults (time_cost=2, memory_cost=65536, parallelism=1) is adequate per research.md
- If Redis is down, `get_current_user` raises HTTP 503 (not 500) to signal a retriable infrastructure error
- T036–T038 require the Docker stack running — manual validation steps
