"""
Streaming Q&A with citation grounding for the AI Resume Matcher.

stream_answer() yields SSE-formatted chunks then a [DONE] sentinel.
Each chunk: 'data: {"delta": "..."}\n\n'
Final:       'data: [DONE]\n\n'

Claude is constrained to cite only from the provided POSTING and RESUME context.
When it cannot answer, it must reply: "I don't have enough information to answer that."
"""

import json
import os
from collections.abc import AsyncIterator

_MODEL = "claude-sonnet-4-6"
_RESUME_CHARS = 8000   # ~2000 tokens
_POSTING_CHARS = 6000  # ~1500 tokens

_SYSTEM_PROMPT = (
    "You are a co-op application assistant helping a student understand how well they match "
    "a specific job posting.\n\n"
    "RULES:\n"
    "1. Answer ONLY using information from the <resume> and <posting> sections below.\n"
    "2. Cite your source inline. Prefix each claim with either 'Resume: ' or 'Posting: ' "
    "followed by a short verbatim or paraphrased excerpt.\n"
    "3. If you cannot answer from the provided context, respond EXACTLY with: "
    "'I don't have enough information to answer that.'\n"
    "4. Do not guess, infer company culture, or use external knowledge.\n"
    "5. Keep your answer concise and directly relevant to the question."
)


async def stream_answer(
    posting_text: str,
    resume_text: str,
    question: str,
) -> AsyncIterator[str]:
    """
    Stream a cited Q&A response as SSE events.

    Yields strings already formatted as SSE lines, e.g.:
        'data: {"delta": "Based "}\n\n'
    Ends with:
        'data: [DONE]\n\n'
    """
    import anthropic

    client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

    user_message = (
        f"<posting>\n{posting_text[:_POSTING_CHARS]}\n</posting>\n\n"
        f"<resume>\n{resume_text[:_RESUME_CHARS]}\n</resume>\n\n"
        f"Question: {question}"
    )

    async with client.messages.stream(
        model=_MODEL,
        max_tokens=1024,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    ) as stream:
        async for text_chunk in stream.text_stream:
            payload = json.dumps({"delta": text_chunk})
            yield f"data: {payload}\n\n"

    yield "data: [DONE]\n\n"
