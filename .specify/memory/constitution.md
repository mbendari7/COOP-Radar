# CoopRadar Constitution

## Core Principles

### I. Correctness First

Every backend endpoint MUST have Pydantic request/response schemas and at least one happy-path
and one validation test. CI gates (ruff, mypy, pytest, eslint, tsc, vitest, agent evals) MUST
all pass before any branch is merged. A failing gate is a blocker, not a warning.

### II. Data Stays in the Database Layer

Searching, filtering, sorting, and pagination MUST run in SQL, never in application memory or the
browser. Sortable and filterable fields MUST be whitelisted in the service layer. User-supplied
values MUST never be interpolated into raw query strings; use SQLAlchemy bound parameters only.

### III. Performance Budgets

List and search endpoints MUST return in under 300 ms p95 measured against a dataset of 10,000
postings. Frontend pages MUST show useful content within 2 seconds on a standard laptop
connection. Every new sortable or filterable column MUST ship with a matching DB index. Performance
regressions that exceed these budgets MUST be fixed before merge.

### IV. Honest AI

The assistant MUST only make claims it can support with a posting ID or a verbatim excerpt from
resume text. It MUST say "not enough information" rather than guessing or extrapolating. It MUST
never perform a write action (save posting, update status) without an explicit user confirmation
round-trip in the UI. Any change to a prompt or tool MUST be accompanied by before/after eval
numbers; the eval pass rate MUST NOT drop below 80%.

### V. Privacy and Security

Resumes and all personal data belong to the user. They MUST never be transmitted to any third
party other than the configured AI provider, and only for the purpose of the current request.
Users MUST be able to delete their data at any time with immediate, permanent effect. All secrets
MUST live in environment variables; no secret may be committed to the repository. Passwords MUST
be hashed (argon2). Sessions MUST expire; HTTP-only secure cookies or short-lived JWTs with
refresh tokens are the only permitted session mechanisms.

### VI. Responsible Data Collection

Postings MUST come only from public APIs/feeds, user-uploaded files, or manual entry. The system
MUST respect each source's robots.txt and terms of service. Scraping pages behind a login is
prohibited. Every ingestion source MUST be documented in the plan with a link to its terms.

### VII. Accessible, Mobile-First UI

Every page MUST be usable at 375 px width. All interactive elements MUST be keyboard-reachable
with a visible focus ring. Form controls MUST have accessible labels. Color contrast MUST meet
WCAG AA (4.5:1 normal text, 3:1 large text). The table MUST collapse to a card layout below the
`md` breakpoint.

### VIII. Small, Reviewable Changes

Commits MUST follow the Conventional Commits format. Each feature MUST live on its own branch and
be merged via a pull request. `docs/agentic-workflow.md` MUST be updated after each feature,
describing what the AI agent did, what the developer reviewed or rewrote, and what tests were
added and their result.

### IX. Simplicity

New dependencies MUST have a stated reason in the feature plan before being added. Prefer
well-documented, widely-used libraries over novel alternatives. Do not add abstractions, helpers,
or configuration options for hypothetical future requirements. Three similar lines of code are
preferable to a premature abstraction.

## Quality Gates

The following checks MUST pass on every pull request targeting `main`:

- **Backend**: `ruff check`, `mypy --strict`, `pytest -q` (including agent evals at ≥ 80% pass)
- **Frontend**: `eslint`, `tsc --noEmit`, `vitest run`
- **Performance**: seed-based p95 benchmark on 10,000 postings (list/search ≤ 300 ms)

No manual override of a failing gate is permitted without a documented exception in the PR
description and a follow-up issue to fix the root cause within the same sprint.

## Development Workflow

1. Create a feature branch: `git checkout -b NNN-short-description`
2. Run `/speckit-specify` → `/speckit-clarify` → `/speckit-plan` → `/speckit-checklist`
   → `/speckit-tasks` → `/speckit-analyze` → `/speckit-implement`
   → `/speckit-converge` (repeat until "Converged") → `/log-agentic-work`
3. Open a pull request; all CI gates must be green before review.
4. Merge to `main` only after review approval and green CI.
5. Features are delivered in priority order: 001 Browse & Search → 002 Accounts & Tracker
   → 003 Real Postings & Semantic Search → 004 AI Resume Matcher & Assistant.

## Governance

This constitution supersedes all other practices documented in this repository. Any amendment
requires:

1. A pull request updating this file with a version bump following semantic versioning:
   - **MAJOR**: removal or redefinition of an existing principle.
   - **MINOR**: new principle or materially expanded guidance.
   - **PATCH**: clarification, wording fix, or non-semantic refinement.
2. The Sync Impact Report HTML comment (see top of file) MUST accompany the PR and be removed
   before merge.
3. All open feature branches MUST be assessed for impact and updated if necessary before the
   amended constitution is merged.

Every PR and code review MUST verify compliance with this constitution. Complexity that exceeds
the simplicity principle MUST be justified in the plan with a Complexity Tracking table.

**Version**: 1.0.0 | **Ratified**: 2026-10-09 | **Last Amended**: 2026-10-09
