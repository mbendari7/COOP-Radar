# Research: Bring Your Own AI Key and a Resume First Site

**Feature**: 005-byok-resume-first
**Date**: 2026-10-11 (written up 2026-11-17)

## 1. How visitors give us their key

**Decision**: The browser keeps the key in session storage (or local storage if the visitor ticks remember) and
sends it on three headers, `X-AI-Provider`, `X-AI-Key` and `X-AI-Model`, only on AI requests.

**Why**: Nothing to store or encrypt on the server, and the key goes away when the visitor clears it. Headers keep
it out of URLs and out of access logs.

**Turned down**: Saving keys in the database encrypted. That makes the server a place worth attacking and the
owner responsible for other people's secrets.

## 2. One wrapper or a framework

**Decision**: A small `app/ai.py` with `complete()`, `stream()` and `list_models()` that calls the three official
SDKs directly.

**Why**: The project needs three calls, not agents or chains. The official SDKs get fixes first and have the best
error types to map from.

**Turned down**: LangChain and LiteLLM. Both are big for three calls and hide the errors we need to tell apart.

## 3. Telling errors apart

**Decision**: `_translate()` maps every SDK error to one of `AI_KEY_INVALID`, `AI_MODEL_INVALID`,
`AI_PROVIDER_RATE_LIMITED` or `AI_PROVIDER_ERROR`, and the message never includes the key.

**Found while testing live**: Google answers a bad key with a 400 and `API_KEY_INVALID` in the body, not a 401.
It is handled and has a test.

## 4. Matching with no AI

**Decision**: Stage 1 finds which posting skills appear in the resume (`skill_match.mentions`, whole words, with
special rules for C, R, Go and Spring) and ranks open postings in SQL by matched skills divided by
`greatest(cardinality(skills), 3)`. Stage 2, only with a key, sends the top candidates to the visitor's model for a
0 to 100 score and a reason.

**Why**: SQL compares every posting for free in milliseconds. A model is better at the final order but costs the
visitor per posting, so it only sees a short list.

**Turned down**: Embeddings for everyone. They need an OpenAI key for every posting, which is the owner's cost.
They stay an option when the owner sets `OPENAI_API_KEY`.

## 5. No sign up

**Decision**: `POST /api/auth/guest` makes a temporary user when a signed out visitor uploads. `POST
/api/auth/demo` makes one with sample data. Both are `is_demo = true`, deleted after 7 days, 10 per network per
hour. `POST /api/me/claim` turns one into a normal account.

**Why**: Every extra form loses students. A temporary account still lets the tracker and the resume work the same
way as a real one, so no code has two paths.

## 6. Reading model replies

**Decision**: `app/llm.py → response_text()` joins only the text blocks.

**Why**: Current Claude models can send thinking blocks first. Reading `content[0].text` broke on them (found in
the 2026-10-10 review).

## 7. Prompt injection

**Decision**: Resume and posting text go inside tags and every system prompt says the tagged text is data, not
instructions. Replies are rendered from a safe Markdown subset (`RichText.tsx`), never as HTML.
