# Research: AI Resume Matcher

**Feature**: 004-ai-resume-matcher | **Date**: 2026-10-10

---

## PDF Text Extraction

**Decision**: `pypdf>=4.0` (pure-Python, `PdfReader.pages[i].extract_text()`)

**Rationale**: Most widely-used pure-Python PDF library; no system dependencies; handles
multi-page PDFs; available on PyPI; zero native binary install overhead in Docker.

**Alternatives considered**:
- `pdfminer.six` — more accurate for complex PDFs, but slower and more complex API; overkill for resumes
- `pymupdf` — fastest, best quality, but requires MuPDF C library; increases Docker image size significantly
- `pdfplumber` — wrapper over pdfminer; easier API but heavier

**Validation**: Extract text from a typical 2-page resume PDF in < 2 s. Fall back gracefully with
an error message if pypdf raises `PdfReadError` (encrypted or corrupted file).

---

## DOCX Text Extraction

**Decision**: `python-docx>=1.1` (`Document.paragraphs[i].text`)

**Rationale**: The canonical DOCX library for Python; widely-used; returns paragraph text cleanly;
available on PyPI; no system dependencies.

**Alternatives considered**:
- `mammoth` — excellent HTML output but over-engineered for plain-text extraction
- Manual XML parsing — fragile, no maintained library support

---

## Match Pipeline Architecture

**Decision**: Synchronous POST — extract → embed → cosine rank → Haiku re-rank → store → return results

**Rationale**: The 30 s SLA is generous. Embedding one resume takes ~1 s; cosine similarity
query over 10 k posting embeddings takes < 200 ms; batching 20 posting descriptions + resume
summary to Claude Haiku takes ~5–10 s. Total ≤ 15 s typical, well within the 30 s budget.
Keeping it synchronous avoids adding polling complexity on the frontend and a second RQ job type.

**Alternatives considered**:
- RQ background job with polling — adds frontend polling loop and job-status endpoint; unnecessary
  given the timing budget
- Stream match progress via SSE — complex; match results are not useful until all 20 are scored

---

## Match Scoring Approach

**Decision**: Two-stage: (1) OpenAI text-embedding-3-small cosine similarity for candidate
selection (top 40), (2) Claude Haiku structured JSON re-ranking for final top 20 with score + reason

**Rationale**: Stage 1 is fast and cheap (already used for Feature 003). Stage 2 adds semantic
reasoning that embeddings miss (e.g., seniority mismatch, unusual skill synonyms). Claude Haiku
is the cheapest model capable of structured JSON output and is already a project dependency.

**Prompt design**: Send resume extracted text (truncated to 2000 tokens) + posting title/description
(truncated to 1500 tokens) per item. Ask Claude to output `{"score": 0-100, "reason": "<one sentence>"}`.
Parse and validate with Pydantic.

**Alternatives considered**:
- Only embedding cosine — misses semantic nuance, no human-readable reason
- Only LLM scoring all postings — too slow and expensive for 10 k postings
- GPT-4o for re-ranking — higher cost, no advantage for structured scoring

---

## Streaming Q&A

**Decision**: FastAPI `StreamingResponse` with `text/event-stream`, `fetch()` + ReadableStream on frontend

**Rationale**: The Anthropic Python SDK supports streaming via `client.messages.stream()`. FastAPI
`StreamingResponse` wraps any async generator as SSE. The frontend uses `fetch()` with a streaming
reader (not EventSource) to support POST bodies, enabling longer questions without URL-length limits.

**SSE format**:
```
data: {"delta": "word "}\n\n
data: {"delta": "by "}\n\n
data: [DONE]\n\n
```

**Citation grounding prompt design**:
- System prompt: "Answer using ONLY information from RESUME_TEXT and POSTING_TEXT. Cite the exact
  source (e.g. 'Resume: ...', 'Posting: ...'). If you cannot answer from these sources, respond:
  'I don't have enough information to answer that.'"
- User message: `<posting>\n{posting_text}\n</posting>\n<resume>\n{resume_text}\n</resume>\n\nQuestion: {question}`
- Model: `claude-sonnet-4-6` (best reasoning + citation quality for this use case)

**Alternatives considered**:
- EventSource (GET) — browser-native but requires GET; long questions hit URL length limits
- WebSockets — overkill for one-shot Q&A; SSE is simpler and stateless

---

## Eval Suite Design

**Decision**: 25 fixture-based test cases in `backend/tests/eval/test_resume_match_eval.py`;
metrics: citation rate ≥ 80 %, zero factual errors in fixture-based assertions

**Case distribution**:
- 10 cases: Q&A cites resume section correctly
- 5 cases: Q&A cites posting sentence correctly
- 5 cases: AI correctly says "don't know" (question unanswerable from context)
- 5 cases: Match score is in correct range for strong/weak/irrelevant resumes

**Mocking**: Anthropic SDK calls mocked with `unittest.mock.patch`; fixture responses are
pre-crafted strings that contain citations. Citation detection: regex for `Resume:` or `Posting:`
prefix in response text.

**Gate**: Eval test file is part of normal `pytest -q` run. CI will fail if citation rate drops.

---

## New Python Dependencies

| Package | Version | Reason |
|---------|---------|--------|
| `pypdf` | `>=4.0` | PDF text extraction |
| `python-docx` | `>=1.1` | DOCX text extraction |

Both are widely-used, pure-Python, no system dependencies. No novel alternatives considered.
Consistent with Constitution IX (Simplicity).
