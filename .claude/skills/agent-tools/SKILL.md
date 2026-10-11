---
name: agent-tools
description: How CoopRadar uses AI — bring-your-own-key across Claude, ChatGPT (OpenAI), and Gemini (app/ai.py), the free no-AI matching it builds on, resume match ranking, the AI resume review (insights), the streaming tailor / cover-letter / Q&A assistant, key handling and safety, prompt-injection and hallucination guards, and the (planned) tool-use agent, MCP server, and evals. Use when working in backend/app/ai.py, backend/app/agent, backend/app/llm.py, backend/app/services/resume.py, backend/app/services/insights.py, backend/app/api/ai.py, frontend/src/api/aiKey.ts, backend/app/mcp, or backend/evals.
---

# Working with AI in CoopRadar

## What exists today — bring your own key
Visitors supply their own **Claude (Anthropic), ChatGPT (OpenAI), or Gemini (Google)** key in the browser
(`frontend/src/api/aiKey.ts`, `pages/AiKeyPage.tsx`). It's sent as `X-AI-Provider` / `X-AI-Key` / `X-AI-Model`
headers on AI routes only, forwarded per request, and never stored or logged.

| Feature | Code | Model | Notes |
|---|---|---|---|
| Provider layer | `app/ai.py` | visitor's choice | `complete()`, `stream()`, `list_models()`, `credentials_from_headers()`, error translation |
| Free matching (no AI) | `app/services/resume.py` | — | SQL skill coverage (÷ max(n, 3)) × `_student_fit`; used whenever no key is sent (upload uses `ai_credentials("rank", optional=True)`) |
| Assistant (streaming SSE) | `app/agent/resume_qa.py` | visitor's model | `mode`: `question` (cites `Resume:`/`Posting:`), `tailor`, `cover_letter`; never invent experience; errors in-band |
| Match re-rank (top 40 → top 20) | `app/services/resume.py` → `POST /api/resume/rematch` | visitor's model | prompt scores senior roles low for students; unusable output falls back to free order; bad key is raised |
| Resume review (insights) | `app/services/insights.py` → `POST /api/resume/insights` | visitor's model | strict JSON, every field validated + truncated, cached in `resumes.insights`; 502 `AI_BAD_RESPONSE` if unparseable |
| Key check | `app/api/ai.py` → `POST /api/ai/check` | — | lists models the key can use; rate-limited per IP |
| Owner fallback (optional) | `ANTHROPIC_API_KEY` + `AGENT_MODEL`/`FAST_MODEL` | `claude-opus-5-5` / `claude-haiku-5-5` | used only when the visitor sent no key; `AI_DAILY_LIMIT` applies |
| Field extraction (ingest) | `app/ingest/extract.py` | owner's `FAST_MODEL` | background job; skipped without an owner key |
| Embeddings (optional) | `app/ingest/embed.py` | owner's `EMBED_MODEL` | smart search + similar postings only |

## Rules
- AI is an add-on: every core flow (upload, insights' free part, matches) must keep working with no key at all.
- Every new AI call goes through `app/ai.py` (`complete`/`stream`) with `AICredentials` — never construct a provider
  SDK client elsewhere, never log `creds.api_key`, never put it in an error message or response.
- New AI-backed routes take `creds: AICredentials = Depends(ai_credentials("rank" | "chat"))` and call
  `consume_ai_quota` **only** when `creds.source == "server"`.
- Model ids are never hard-coded at call sites: visitors pick from `list_models()`; owner models come from settings.
- Provider differences belong inside `app/ai.py`: map new error shapes in `_translate()` (test the real shape — e.g.
  Gemini reports a bad key as 400 + `API_KEY_INVALID`).
- Parse model JSON with `app.llm.parse_json`; validate every field (drop invented IDs, clamp scores, dedupe).
- Prompt-injection: posting descriptions and resumes are **data** — wrap them in tags and say so in the system prompt.
- Honest AI (constitution IV): cite sources; reply exactly "I don't have enough information to answer that." when
  the context lacks the answer. A rejected key is surfaced to the user, never silently replaced by non-AI output.

## Testing
- Never call live APIs in tests. The `client` fixture sends test `X-AI-*` headers (Claude). Use conftest fixtures
  `mock_claude_create(text)`, `mock_claude_stream(text, stop_reason=...)`, `mock_embedding`, `test_creds`; mock
  `openai.AsyncOpenAI` / `google.genai.Client` for the other providers (see `tests/api/test_ai.py`).
- Safe live check (costs nothing): call `POST /api/ai/check` with an obviously fake key for each provider and
  confirm the answer is `AI_KEY_INVALID`.
- `tests/eval/test_resume_match_eval.py` checks the pipeline's handling of model output (citations, don't-know
  phrase, score bounds) with mocked responses. It does **not** measure live model quality.
- When you change a prompt: describe the change, run the eval file, and (with an API key) spot-check real answers.

## Planned (spec 004, not built yet)
- `app/agent/tools.py`: Pydantic-typed tools calling the service layer (`search_postings`, `get_posting`,
  `score_fit`, `compare_postings`, `save_posting`, `update_status`); read-only by default, writes need a UI
  confirmation round-trip. Prefer the SDK tool runner (`client.beta.messages.tool_runner`) for the loop.
- `app/mcp/server.py`: expose the same tools over MCP — no duplicated logic.
- `agent_runs` table logging tool calls, tokens, latency, cost.
- `backend/evals/`: 25 YAML cases + `python -m evals.run` that reports pass rate / tokens / latency and exits
  non-zero under 80% so CI can gate on it. Report before/after numbers for every prompt or tool change.
