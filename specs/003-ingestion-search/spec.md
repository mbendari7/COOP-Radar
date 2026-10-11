# Feature Specification: Real Postings Ingestion & Semantic Search

**Feature Branch**: `003-ingestion-search`

**Created**: 2026-10-10

**Status**: Draft

**Input**: User description: "Real Postings Ingestion & Semantic Search — Feature 003"

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Scheduled Ingestion from Public Sources (Priority: P1)

The system automatically imports co-op postings every 6 hours from a configurable list of company job boards that publish public APIs or RSS feeds. Each run fetches new postings, updates changed ones, closes ones that have disappeared, and records the run result in an audit log. An admin can also trigger a run manually from the Sources page.

**Why this priority**: Without real postings the app has no value for a genuine job hunt. Every other feature depends on having up-to-date data.

**Independent Test**: Configure one source adapter pointing to a recorded fixture response. Trigger a run. Confirm new postings appear in the postings list. Trigger the same run again — confirm no duplicates are created and the run log shows "0 added". Remove a posting from the fixture and re-run — confirm that posting is marked closed.

**Acceptance Scenarios**:

1. **Given** a configured source with 10 new postings, **When** a scheduled run completes, **Then** all 10 postings appear in the postings list and the run log shows "10 added, 0 updated, 0 closed".
2. **Given** a run that already imported a posting, **When** the same run fires again with identical data, **Then** 0 new postings are added and the run is recorded as a no-op.
3. **Given** a posting that existed in the previous run but is absent in the current one, **When** the run completes, **Then** the posting is marked closed and hidden from the default list view.
4. **Given** a source that returns an HTTP error, **When** the run fires, **Then** the error is captured in the run log, no partial data is committed, and the next scheduled run is unaffected.
5. **Given** an admin on the Sources page, **When** they click "Run now" for a source, **Then** a run starts immediately and the page shows live progress feedback.

---

### User Story 2 — CSV Upload and Manual Entry (Priority: P2)

A student can upload a CSV file exported from their school's co-op portal to bulk-import postings. They can also add a single posting manually through a form. Both paths use the same duplicate-detection logic as the scheduled ingestion.

**Why this priority**: School portals are the primary source of real co-op postings; CSV upload unblocks students on day one before automated sources are fully configured.

**Independent Test**: Upload a CSV with 5 valid rows and 1 row missing a required column. Confirm 5 postings are imported, 1 row error is shown to the user, and submitting the same CSV a second time imports 0 new postings (duplicates skipped).

**Acceptance Scenarios**:

1. **Given** a valid CSV with required columns (title, company, city, term, deadline), **When** the student uploads it, **Then** all rows are imported and a summary ("5 postings added") is shown.
2. **Given** a CSV with one row missing the "deadline" column value, **When** the student uploads it, **Then** the valid rows are imported and the invalid row is listed with a clear error message identifying the row number and missing field.
3. **Given** a CSV containing a posting that already exists (same company, title, city), **When** it is uploaded, **Then** no duplicate is created and the summary reports "1 skipped (duplicate)".
4. **Given** a student on the manual entry form, **When** they submit all required fields, **Then** the posting is saved and immediately visible in the postings list.
5. **Given** a manual entry form submitted with an invalid deadline date, **When** the student submits, **Then** a validation error is shown and no posting is saved.

---

### User Story 3 — Semantic ("Smart") Search (Priority: P3)

A student can switch from keyword search to semantic search with a toggle. Semantic search finds postings by meaning — for example, "embedded firmware" also finds postings that mention "microcontroller C developer" — because both the query and all posting descriptions are represented as meaning-vectors. The detail page shows a "Similar postings" sidebar with the top 5 results.

**Why this priority**: Keyword search misses semantically equivalent terms common in job descriptions. Semantic search is the key differentiator of this feature for users.

**Independent Test**: Index 50 postings. Submit the query "embedded firmware" in semantic mode. Confirm at least one result contains "microcontroller" but not "firmware" in its title or description. Open a posting and confirm the "Similar postings" sidebar lists 5 entries none of which is the open posting itself.

**Acceptance Scenarios**:

1. **Given** the student is in keyword mode, **When** they toggle to semantic mode, **Then** the results update to reflect meaning-based ranking and the toggle reflects the active mode.
2. **Given** a query of "embedded firmware", **When** submitted in semantic mode, **Then** results include postings about microcontroller development even if they do not contain the word "firmware".
3. **Given** a posting detail page, **When** the page loads, **Then** a "Similar postings" section lists up to 5 postings ranked by semantic similarity, none of which is the current posting.
4. **Given** fewer than 5 postings exist, **When** the similar postings section loads, **Then** it shows as many as are available (may be empty if only 1 posting exists).
5. **Given** the student submits a semantic query, **When** results load, **Then** they appear within the same 2-second budget as keyword search.

---

### User Story 4 — Admin Sources Page (Priority: P4)

An admin user can view all configured ingestion sources, see each source's last run time, the counts of postings added/updated/closed, any errors, and trigger a manual run. Admins can add new sources and flag individual fields on a posting as needing review.

**Why this priority**: Operational visibility is required to maintain data quality; low-confidence field flags protect students from bad data without blocking imports.

**Independent Test**: Log in as admin. Navigate to /admin/sources. Confirm all configured sources appear with last-run status. Click "Run now" — confirm the run log updates. Open a posting with a low-confidence field — confirm the yellow warning icon is visible to the admin but not to students on the public detail page.

**Acceptance Scenarios**:

1. **Given** an admin on /admin/sources, **When** the page loads, **Then** all configured sources are listed with name, last run time, and counts (added/updated/closed/errors).
2. **Given** a source that last ran with errors, **When** the admin views the Sources page, **Then** the error count is highlighted and clicking it shows the error message(s).
3. **Given** an admin clicks "Run now" on a source, **When** the run completes, **Then** the run log entry is added and counts update on the page without a full reload.
4. **Given** an admin views a posting with one or more low-confidence auto-extracted fields, **When** they open the posting in the admin view, **Then** a yellow warning icon labels each flagged field.
5. **Given** a student viewing the same posting, **When** they open the detail page, **Then** no warning icons or admin controls are visible.

---

### Edge Cases

- What happens if the embedding service is unavailable during ingestion? Postings are imported without embeddings and queued for embedding generation; semantic search degrades gracefully to keyword-only mode until embeddings are available.
- What happens if a CSV upload contains 10,000 rows? The system validates and imports up to 1,000 rows per upload; larger files are rejected with a clear message instructing the student to split the file.
- What happens if a posting's company, title, and city all match an existing posting but the deadline changed? The existing posting is updated (not duplicated) and the run log counts it as "1 updated".
- What happens when two different sources import the same posting (same company + title + city)? The second import is treated as a duplicate; the source that ingested it later is noted in the posting's metadata.
- What happens if an admin source URL is unreachable for 3 consecutive runs? The source is automatically paused and the admin receives a status badge "Auto-paused" on the Sources page.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST import postings from configured public sources on a 6-hour schedule and on demand via a "Run now" action.
- **FR-002**: System MUST treat two postings as duplicates when they share the same company name, a title with Levenshtein similarity > 0.85, and the same city; duplicates MUST NOT create a new row.
- **FR-003**: System MUST mark a previously-imported posting as closed when it is absent from its source in the current run; closed postings MUST be hidden from the default postings list.
- **FR-004**: System MUST record every ingestion run in an audit log: source name, start time, duration, counts (added/updated/closed/errors), and any error messages.
- **FR-005**: System MUST auto-extract city, work mode, term, duration, and required skills from posting text using rule/regex matching against the skills taxonomy first; LLM extraction is used only when rule-based confidence is below 0.6.
- **FR-006**: Fields extracted with confidence below 0.6 MUST be flagged; flagged fields are visible only to admins, never to students.
- **FR-007**: System MUST allow a student to upload a CSV with required columns (title, company, city, term, deadline); each row with a validation error MUST be reported individually without blocking valid rows.
- **FR-008**: CSV uploads MUST be limited to 1,000 rows per submission; files exceeding this limit MUST be rejected with a clear message.
- **FR-009**: System MUST allow any authenticated user to add a single posting manually through a validated form.
- **FR-010**: System MUST store a vector embedding (1536 dimensions) for every posting and use it for semantic similarity queries; embeddings MUST be generated asynchronously and not block ingestion.
- **FR-011**: System MUST provide a semantic search mode that ranks postings by cosine similarity to the query embedding; the toggle between keyword and semantic mode MUST be preserved in the page URL.
- **FR-012**: The posting detail page MUST show up to 5 similar postings ranked by cosine similarity, excluding the current posting.
- **FR-013**: The admin Sources page MUST be accessible only to users with the admin flag set; non-admin access MUST return 403.
- **FR-014**: Source adapters MUST respect each source's robots.txt and terms of service; scraping pages behind a login is prohibited.
- **FR-015**: If a source fails for 3 consecutive runs, it MUST be automatically paused and its status on the Sources page MUST read "Auto-paused".
- **FR-016**: Ingestion tests MUST use recorded fixture responses; no test MUST make live network calls.

### Key Entities

- **IngestSource**: A configured ingestion source. Key attributes: name, adapter type (json-api/rss/csv/manual), URL or config, enabled flag, auto-paused flag, last-run timestamp.
- **IngestRun**: A single execution of one source adapter. Key attributes: source reference, start/end timestamp, counts (added/updated/closed), error messages, status (success/partial/failed).
- **PostingEmbedding**: The meaning-vector for a posting. Key attributes: posting reference, vector (1536 floats), model name used, generated-at timestamp.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After the first scheduled run against configured sources, at least 200 real, de-duplicated postings with correct locations and terms are visible in the postings list.
- **SC-002**: Semantic search returns results within 2 seconds on a dataset of 10,000 postings (same budget as keyword search).
- **SC-003**: Duplicate detection correctly identifies and skips at least 95% of exact-duplicate postings across sources, verified by a seed test with known duplicates.
- **SC-004**: A student can upload a 100-row CSV and see all import results (successes and per-row errors) within 10 seconds.
- **SC-005**: The "Similar postings" sidebar loads within 1 second after the detail page is displayed.
- **SC-006**: All ingestion tests pass without making live network calls; tests use recorded fixtures exclusively.
- **SC-007**: The admin Sources page correctly shows run counts and errors for all sources without requiring a page refresh after a manual run.

---

## Assumptions

- The embedding model is OpenAI `text-embedding-3-small` (vector dimension 1536); the model name is configurable via an `EMBED_MODEL` environment variable.
- The skills taxonomy (approx. 150 skills) is seeded into the database and is editable by admins through a simple CRUD UI or seed script; it is not managed through a third-party taxonomy service.
- "Admin" is a boolean flag on the existing User model; no separate admin account type is introduced.
- Source adapters for this feature support three types: JSON API, RSS feed, and the CSV/manual path. SOAP, GraphQL, and proprietary integrations are out of scope.
- The scheduler runs inside the same Docker Compose stack using RQ (Redis Queue) and rq-scheduler; no external cron or task broker is introduced.
- Posting text used for embedding and skill extraction is the concatenation of title, description, and required skills fields.
- pgvector is already available in the PostgreSQL image used by the project (the `postgres:16-pgvector` image is specified in docker-compose.yml).
- The student-facing CSV upload is rate-limited to 3 uploads per user per hour to prevent abuse.
- Password-protected or login-gated source pages are out of scope; only public URLs and APIs are supported.
