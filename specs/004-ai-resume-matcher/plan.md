# Implementation Plan: AI Resume Matcher

**Branch**: `004-ai-resume-matcher` | **Date**: 2026-10-10 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/004-ai-resume-matcher/spec.md`

## Summary

Students upload a PDF or DOCX resume; the server extracts its text, embeds it with OpenAI
text-embedding-3-small, ranks all co-op postings by cosine similarity, re-ranks the top 20 using
Claude Haiku to produce a 0–100 match score and a one-sentence reason, and stores the results in
`match_results`. A separate streaming Q&A endpoint lets students ask free-text questions about any
matched posting; Claude claude-sonnet-4-6 answers citing only resume or posting text, streaming
word-by-word via SSE. Students can view stored resume metadata and permanently delete it.

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript / React 18 (frontend)

**Primary Dependencies**:
- FastAPI, SQLAlchemy 2.0 async, Pydantic v2, Alembic (existing)
- `pypdf>=4.0` — PDF text extraction (pure-Python, widely-used)
- `python-docx>=1.1` — DOCX text extraction (widely-used)
- `anthropic>=0.29` — Claude Haiku re-ranking + claude-sonnet-4-6 streaming Q&A (existing)
- `openai>=1.30` — text-embedding-3-small embeddings (existing)
- `pgvector>=0.3` — cosine similarity query (existing)
- TanStack Query v5, React Router v6, Tailwind CSS v3 (existing)

**Storage**: PostgreSQL 16 + pgvector; two new tables — `resumes`, `match_results`

**Testing**: pytest + respx (backend), vitest (frontend); eval suite at `backend/tests/eval/`

**Target Platform**: Linux server via Docker Compose; browser (mobile-first)

**Performance Goals**:
- Resume upload + ranked results: ≤ 30 s end-to-end (synchronous POST)
- Stored match page load: ≤ 2 s (SC6)
- Streaming Q&A: first token ≤ 3 s

**Constraints**:
- File upload: PDF/DOCX only, ≤ 5 MB
- Raw file never persisted; only `extracted_text` stored
- All resume data scoped to authenticated user (FR-014)
- AI must cite resume/posting text; "don't know" fallback required (IV. Honest AI)

**Scale/Scope**: ~10,000 postings with existing embeddings; one resume per user

## Constitution Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Correctness First | PASS | Every new endpoint ships with Pydantic schema + pytest |
| II. Data in DB | PASS | Cosine ranking runs in SQL (`<=>` operator); re-ranking via LLM returns structured JSON stored in DB |
| III. Performance | PASS | Embedding + cosine < 1 s; Haiku batch ~5 s; total < 30 s; return-visit results load from DB in < 2 s |
| IV. Honest AI | PASS | System prompt constrains Claude to cite resume section or posting sentence; "I don't have enough information" fallback enforced; eval suite gates at ≥ 80 % citation rate |
| V. Privacy | PASS | Resumes scoped to user; delete cascades immediately; text only sent to AI provider per-request; no raw file persisted |
| VI. Responsible Data | N/A | No external source ingestion in this feature |
| VII. Accessible UI | PASS | File input with accessible label, WCAG-AA contrast, keyboard-reachable buttons, 375 px width |
| VIII. Small Changes | PASS | Feature branch + conventional commits |
| IX. Simplicity | PASS | pypdf + python-docx are the canonical libraries; no novel abstractions; match pipeline is a single service function |

All gates pass — no Complexity Tracking table required.

## Project Structure

### Documentation (this feature)

```text
specs/004-ai-resume-matcher/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code

```text
backend/
├── app/
│   ├── models/
│   │   ├── resume.py          (new) Resume ORM
│   │   └── match_result.py    (new) MatchResult ORM
│   ├── schemas/
│   │   └── resume.py          (new) Upload, metadata, match, ask schemas
│   ├── services/
│   │   └── resume.py          (new) extract, embed, rank, store, delete, ask
│   ├── api/
│   │   └── resume.py          (new) /api/resume routes + SSE stream
│   └── agent/
│       └── resume_qa.py       (new) Streaming Q&A with citation prompt
├── alembic/versions/
│   └── 0005_add_resume_matcher.py  (new)
├── pyproject.toml             (modified: add pypdf, python-docx)
└── tests/
    ├── resume/
    │   ├── test_resume_upload.py   (new)
    │   ├── test_match_service.py   (new)
    │   └── test_resume_qa.py       (new)
    └── eval/
        └── test_resume_match_eval.py  (new, 25 cases)

frontend/
└── src/
    ├── api/
    │   └── resume.ts          (new) TanStack Query hooks for resume + matches + SSE
    ├── components/
    │   ├── ResumeUploadForm.tsx    (new)
    │   └── ConversationPanel.tsx   (new) streaming Q&A inline panel
    ├── pages/
    │   └── MatchResultsPage.tsx    (new) /matches route
    └── App.tsx                (modified: add /matches route + nav link)
```

**Structure Decision**: Web application (monorepo). Backend additions follow existing
`backend/app/{models,schemas,services,api}/` conventions. Agent Q&A logic placed in
`backend/app/agent/` consistent with CLAUDE.md layout.


---

## Amendment — 2026-10-10 (post-implementation review)

Changes made after this plan was implemented. The decisions above are kept as the original record.

- **Models are configuration, not code**: `AGENT_MODEL` (default `claude-opus-5-5`) answers Q&A; `FAST_MODEL`
  (default `claude-haiku-5-5`) re-ranks matches and extracts fields. Shared client helpers live in `app/llm.py`.
- **Q&A**: explicit `effort: low`, server-side refusal fallback, posting/resume marked as data (prompt-injection
  guard), and in-band SSE `{"error": ...}` events instead of a broken stream when the API fails.
- **Re-ranking**: reads text blocks only (current models emit thinking blocks first), tolerates fenced JSON, drops
  invented/duplicate posting IDs, and falls back to cosine-similarity scores if Claude is unavailable.
  An embedding outage returns 503 `AI_UNAVAILABLE` instead of a 500.
- **Matching scope**: only open, unexpired postings are candidates.
- **Not yet built** (still open from this plan's original scope): agent tool use (`app/agent/tools.py`),
  MCP server, `agent_runs` logging, and the YAML eval runner in `backend/evals/`. See the agent-tools skill.
