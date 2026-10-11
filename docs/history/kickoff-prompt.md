Read CLAUDE.md and the skills in .claude/skills. We're building CoopRadar from an empty repo.

Goal of this session: Milestone 1 only, a working vertical slice.
1. Scaffold the monorepo exactly as CLAUDE.md's Layout says: docker-compose.yml (postgres with pgvector, redis, api, web), backend (FastAPI), frontend (Vite React TS), .env.example, GitHub Actions CI running lint, type checks and tests for both sides.
2. Data model + first Alembic migration: companies, postings (title, company_id, location, city, province, remote_type, term e.g. "Summer 2027", duration_months, skills text[], description, url, source, posted_at, deadline, search tsvector), and a seed script with ~50 realistic fake postings across Toronto, Waterloo, Guelph, Hamilton, Vancouver.
3. GET /postings with keyword search, filters (city, term, remote_type, skill), server-side sort (posted_at, deadline, company, title) and pagination, following api-conventions. Plus GET /postings/{id}. Tests for both.
4. Frontend: Postings page with a TanStack table (sortable headers, filter bar, pagination, URL state) and a posting detail drawer, following frontend-tables.
5. README with setup steps and an architecture diagram in Mermaid.

How to work:
- Use plan mode first: show me the file tree and schema before writing code, and wait for my OK.
- Build in small steps; after each step run the tests and commit with a conventional message.
- Do NOT start the agent, ingestion, or embeddings yet. Those are Milestones 2–3.
- If something in CLAUDE.md is unclear or seems wrong, ask instead of guessing.
- At the end, tell me exactly how to run it and what to check in the browser.
