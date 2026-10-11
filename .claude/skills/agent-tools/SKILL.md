---
name: agent-tools
description: How CoopRadar uses Claude — resume match re-ranking, posting field extraction, the streaming resume Q&A assistant, model configuration, prompt-injection and hallucination guards, and the (planned) tool-use agent, MCP server, and evals. Use when working in backend/app/agent, backend/app/llm.py, backend/app/services/resume.py, backend/app/ingest/extract.py, backend/app/mcp, or backend/evals.
---

# Working with Claude in CoopRadar

## What exists today
| Feature | Code | Model setting | Notes |
|---|---|---|---|
| Resume Q&A (streaming SSE) | `app/agent/resume_qa.py` | `AGENT_MODEL` (default `claude-opus-5-5`) | effort `low`, server-side refusal fallback, cites `Resume:` / `Posting:` |
| Match re-ranking (top 40 → top 20) | `app/services/resume.py` | `FAST_MODEL` (default `claude-haiku-5-5`) | JSON array out; falls back to cosine ranking on any failure |
| Low-confidence field extraction | `app/ingest/extract.py` | `FAST_MODEL` | only when regex confidence < 0.6; skills filtered to the taxonomy |
| Embeddings | `app/ingest/embed.py` | `EMBED_MODEL` (OpenAI `text-embedding-3-small`, 1536 dims) | Anthropic has no embeddings endpoint |

## Rules
- Model IDs come from settings (`app/config.py` ← env vars). Never hard-code a model string in a call site.
- Build clients only via `app.llm.get_client()`; read text with `app.llm.response_text(message)` —
  current models think by default, so `message.content[0]` may be a thinking block, not text.
- Parse model JSON with `app.llm.parse_json` (tolerates code fences/prose). Validate every field you use:
  drop IDs the model invented, clamp scores, dedupe.
- Current-model API facts (Opus 5.5 / Sonnet 5.5 / Haiku 5.5):
  - Set `output_config={"effort": ...}` explicitly (Opus 5.5 and Haiku 5.5 default to `medium`).
  - No assistant prefill; forced `tool_choice` (`any`/`tool`) returns 400 — use `auto` + a prompt instruction,
    `strict: true` tools, or structured outputs.
  - Check `stop_reason == "refusal"` before trusting output; the Q&A uses the `server-side-fallback` beta.
- Prompt-injection: posting descriptions and resumes are **data**. Wrap them in tags (`<posting>`, `<resume>`) and
  say so in the system prompt. Never let model output trigger a write without user confirmation.
- Honest AI (constitution IV): answers cite their source; when the context doesn't contain the answer the model says
  exactly "I don't have enough information to answer that."
- AI must never be a single point of failure: every call has a fallback or a clean 503 `AI_UNAVAILABLE`.

## Testing
- Never call live APIs in tests. Use conftest fixtures: `mock_claude_create(text)`, `mock_claude_stream(text,
  stop_reason=...)`, `mock_embedding`.
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
