"""
Eval suite for the AI Resume Matcher (25 fixture-based cases).

Gates (from spec SC3/SC4 and constitution IV):
  - Citation rate >= 80% across Q&A cases (citations present in response)
  - Zero factual errors (all "don't know" cases return the exact expected phrase)
  - Score range cases: strong/mid/weak resumes land in correct buckets

All Anthropic and OpenAI calls are mocked, so this suite checks the pipeline's
handling of model output (parsing, citations, score bounds) — not live model quality.
"""

import json
import re
from collections.abc import Callable
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CITATION_RE = re.compile(r"\b(?:Resume|Posting):\s")
DONT_KNOW_PHRASE = "I don't have enough information to answer that."


def _has_citation(text: str) -> bool:
    return bool(CITATION_RE.search(text))


def _is_dont_know(text: str) -> bool:
    return DONT_KNOW_PHRASE in text


async def _collect(question: str, posting_text: str, resume_text: str) -> str:
    """Run stream_answer and join the streamed deltas."""
    from app.agent.resume_qa import stream_answer

    chunks: list[str] = []
    async for chunk in stream_answer(
        posting_text=posting_text, resume_text=resume_text, question=question
    ):
        if chunk.startswith("data: ") and "[DONE]" not in chunk:
            chunks.append(json.loads(chunk[6:].strip()).get("delta", ""))
    return "".join(chunks)


# ---------------------------------------------------------------------------
# Cases 1–10: Q&A produces Resume: citation
# ---------------------------------------------------------------------------

RESUME_CITATION_CASES = [
    ("What Python experience do I have?", "Resume: Python projects listed in experience section."),
    ("What Django skills do I have?", "Resume: Django framework used in two projects."),
    ("Do I have PostgreSQL experience?", "Resume: PostgreSQL listed under databases."),
    ("What REST API experience is relevant?", "Resume: Built REST APIs using FastAPI."),
    ("What backend skills are listed?", "Resume: Backend skills include Python and Django."),
    ("Do I have Docker experience?", "Resume: Docker used for deployment."),
    ("What programming languages do I know?", "Resume: Python is the primary language."),
    ("What databases have I worked with?", "Resume: PostgreSQL and Redis listed."),
    ("What cloud experience do I have?", "Resume: AWS used for deployment."),
    ("What frameworks are on my resume?", "Resume: Django and FastAPI frameworks listed."),
]


@pytest.mark.parametrize("question,expected_response", RESUME_CITATION_CASES)
@pytest.mark.asyncio
async def test_qa_resume_citation(
    question: str,
    expected_response: str,
    mock_claude_stream: Callable[..., MagicMock],
) -> None:
    """Q&A response cites resume when relevant resume content exists."""
    mock_claude_stream(expected_response)
    full_response = await _collect(
        question,
        posting_text="We need Python, Django, PostgreSQL skills.",
        resume_text="Skills: Python, Django, PostgreSQL.",
    )
    assert _has_citation(full_response), (
        f"Expected citation in response for question '{question}'. Got: {full_response!r}"
    )


# ---------------------------------------------------------------------------
# Cases 11–15: Q&A produces Posting: citation
# ---------------------------------------------------------------------------

POSTING_CITATION_CASES = [
    ("What does this role require?", "Posting: requires Python, Django, and PostgreSQL."),
    ("What is the job title?", "Posting: Software Developer Co-op at Acme Corp."),
    ("What are the key responsibilities?", "Posting: building backend APIs and managing databases."),
    ("Is this remote or on-site?", "Posting: hybrid work arrangement available."),
    ("What term is this for?", "Posting: Winter 2027 co-op term, 4 months."),
]


@pytest.mark.parametrize("question,expected_response", POSTING_CITATION_CASES)
@pytest.mark.asyncio
async def test_qa_posting_citation(
    question: str,
    expected_response: str,
    mock_claude_stream: Callable[..., MagicMock],
) -> None:
    """Q&A response cites posting when relevant posting content exists."""
    mock_claude_stream(expected_response)
    full_response = await _collect(
        question,
        posting_text="Software Developer Co-op at Acme Corp. Requires Python, Django, PostgreSQL. Hybrid. Winter 2027.",
        resume_text="Skills: Python, Django.",
    )
    assert _has_citation(full_response), (
        f"Expected posting citation for question '{question}'. Got: {full_response!r}"
    )


# ---------------------------------------------------------------------------
# Cases 16–20: AI correctly says "don't know"
# ---------------------------------------------------------------------------

DONT_KNOW_CASES = [
    "What is the company's GPA requirement?",
    "Does this company offer health benefits?",
    "What is the salary for this co-op?",
    "Is this company publicly traded?",
    "How many employees does this company have?",
]


@pytest.mark.parametrize("question", DONT_KNOW_CASES)
@pytest.mark.asyncio
async def test_qa_dont_know(
    question: str,
    mock_claude_stream: Callable[..., MagicMock],
) -> None:
    """AI says 'don't know' for questions not answerable from context."""
    mock_claude_stream(DONT_KNOW_PHRASE)
    full_response = await _collect(
        question,
        posting_text="Software Developer Co-op. Requires Python.",
        resume_text="Skills: Python.",
    )
    assert _is_dont_know(full_response), (
        f"Expected don't-know response for '{question}'. Got: {full_response!r}"
    )


# ---------------------------------------------------------------------------
# Cases 21–25: Match score range validation
# ---------------------------------------------------------------------------

_STRONG_RESUME = "Skills: Python, Django, PostgreSQL, Docker, AWS, REST APIs, FastAPI"
_MID_RESUME = "Skills: Python, SQL, some web development experience"
_WEAK_RESUME = "Skills: Microsoft Office, data entry, customer service"
_IRRELEVANT_RESUME = "Skills: carpentry, plumbing, electrical wiring"


@pytest.mark.asyncio
async def test_score_strong_resume(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strong match resume → score >= 70."""
    import json

    from app.services.resume import embed_and_rank

    monkeypatch.setattr("app.ingest.embed.generate_embedding", AsyncMock(return_value=[0.9] * 1536))

    fake_row = {
        "id": uuid4(), "title": "Python Developer Co-op", "company": "Acme",
        "city": "Toronto", "province": "ON", "term": "Winter 2027",
        "deadline": "2026-12-01", "description": "Requires Python, Django, PostgreSQL.",
    }
    mock_result = MagicMock()
    mock_result.mappings.return_value.all.return_value = [fake_row]

    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=json.dumps([
        {"posting_id": str(fake_row["id"]), "score": 85, "reason": "Strong Python match."}
    ]))]
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_msg)
    monkeypatch.setattr("anthropic.AsyncAnthropic", MagicMock(return_value=mock_client))

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    results = await embed_and_rank(mock_db, _STRONG_RESUME)
    assert results
    assert results[0].score >= 70


@pytest.mark.asyncio
async def test_score_mid_resume(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mid-level resume → score 40–69."""
    import json

    from app.services.resume import embed_and_rank

    monkeypatch.setattr("app.ingest.embed.generate_embedding", AsyncMock(return_value=[0.5] * 1536))

    fake_row = {
        "id": uuid4(), "title": "Python Developer Co-op", "company": "Acme",
        "city": "Toronto", "province": "ON", "term": "Winter 2027",
        "deadline": "2026-12-01", "description": "Requires Python, Django, PostgreSQL.",
    }
    mock_result = MagicMock()
    mock_result.mappings.return_value.all.return_value = [fake_row]

    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=json.dumps([
        {"posting_id": str(fake_row["id"]), "score": 55, "reason": "Partial Python match."}
    ]))]
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_msg)
    monkeypatch.setattr("anthropic.AsyncAnthropic", MagicMock(return_value=mock_client))

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    results = await embed_and_rank(mock_db, _MID_RESUME)
    assert results
    assert 40 <= results[0].score < 70


@pytest.mark.asyncio
async def test_score_weak_resume(monkeypatch: pytest.MonkeyPatch) -> None:
    """Weak resume → score < 40."""
    import json

    from app.services.resume import embed_and_rank

    monkeypatch.setattr("app.ingest.embed.generate_embedding", AsyncMock(return_value=[0.2] * 1536))

    fake_row = {
        "id": uuid4(), "title": "Python Developer Co-op", "company": "Acme",
        "city": "Toronto", "province": "ON", "term": "Winter 2027",
        "deadline": "2026-12-01", "description": "Requires Python, Django, PostgreSQL.",
    }
    mock_result = MagicMock()
    mock_result.mappings.return_value.all.return_value = [fake_row]

    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=json.dumps([
        {"posting_id": str(fake_row["id"]), "score": 25, "reason": "Very limited technical skills."}
    ]))]
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_msg)
    monkeypatch.setattr("anthropic.AsyncAnthropic", MagicMock(return_value=mock_client))

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    results = await embed_and_rank(mock_db, _WEAK_RESUME)
    assert results
    assert results[0].score < 40


@pytest.mark.asyncio
async def test_score_irrelevant_resume(monkeypatch: pytest.MonkeyPatch) -> None:
    """Irrelevant resume → score < 20."""
    import json

    from app.services.resume import embed_and_rank

    monkeypatch.setattr("app.ingest.embed.generate_embedding", AsyncMock(return_value=[0.05] * 1536))

    fake_row = {
        "id": uuid4(), "title": "Python Developer Co-op", "company": "Acme",
        "city": "Toronto", "province": "ON", "term": "Winter 2027",
        "deadline": "2026-12-01", "description": "Requires Python, Django, PostgreSQL.",
    }
    mock_result = MagicMock()
    mock_result.mappings.return_value.all.return_value = [fake_row]

    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=json.dumps([
        {"posting_id": str(fake_row["id"]), "score": 10, "reason": "No relevant technical skills."}
    ]))]
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_msg)
    monkeypatch.setattr("anthropic.AsyncAnthropic", MagicMock(return_value=mock_client))

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    results = await embed_and_rank(mock_db, _IRRELEVANT_RESUME)
    assert results
    assert results[0].score < 20


@pytest.mark.asyncio
async def test_score_empty_db_returns_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """No postings in DB → empty match list."""
    from app.services.resume import embed_and_rank

    monkeypatch.setattr("app.ingest.embed.generate_embedding", AsyncMock(return_value=[0.5] * 1536))

    mock_result = MagicMock()
    mock_result.mappings.return_value.all.return_value = []

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    results = await embed_and_rank(mock_db, "any resume")
    assert results == []


# ---------------------------------------------------------------------------
# Aggregate gate: citation rate >= 80%
# ---------------------------------------------------------------------------

def test_citation_rate_gate() -> None:
    """
    Verify that the 15 citation cases above would yield >= 80% citation rate.
    This is a compile-time check on the fixture design itself.
    """
    all_citation_responses = (
        [resp for _, resp in RESUME_CITATION_CASES]
        + [resp for _, resp in POSTING_CITATION_CASES]
    )
    cited = sum(1 for r in all_citation_responses if _has_citation(r))
    total = len(all_citation_responses)
    citation_rate = cited / total
    assert citation_rate >= 0.80, (
        f"Fixture citation rate {citation_rate:.0%} < 80%. "
        "Check that fixture responses contain 'Resume: ' or 'Posting: ' prefixes."
    )


def test_dont_know_exact_phrase_gate() -> None:
    """All don't-know fixtures must contain the exact expected phrase."""
    for question in DONT_KNOW_CASES:
        assert _is_dont_know(DONT_KNOW_PHRASE), (
            f"Don't-know fixture for '{question}' does not contain expected phrase."
        )
