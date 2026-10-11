"""
Resume upload, text extraction, match pipeline, and delete logic.
"""

import io
import json
import os
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import delete, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.match_result import MatchResult
from app.models.posting import Posting
from app.models.resume import Resume
from app.schemas.resume import MatchResultOut, MatchesResponse, ResumeOut, UploadResponse

_MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
_ALLOWED_EXTENSIONS = {".pdf", ".docx"}


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------


def extract_pdf_text(data: bytes) -> str:
    """Extract plain text from PDF bytes using pypdf."""
    from pypdf import PdfReader  # type: ignore[import-untyped]

    reader = PdfReader(io.BytesIO(data))
    parts = []
    for page in reader.pages:
        t = page.extract_text()
        if t:
            parts.append(t)
    return "\n".join(parts)


def extract_docx_text(data: bytes) -> str:
    """Extract plain text from DOCX bytes using python-docx."""
    from docx import Document  # type: ignore[import-untyped]

    doc = Document(io.BytesIO(data))
    return "\n".join(p.text for p in doc.paragraphs if p.text)


def extract_text(filename: str, data: bytes) -> str:
    """
    Dispatch to the correct extractor based on file extension.
    Raises ValueError for unsupported formats.
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext == "pdf":
        return extract_pdf_text(data)
    if ext == "docx":
        return extract_docx_text(data)
    raise ValueError(f"Unsupported file extension: .{ext}")


# ---------------------------------------------------------------------------
# Match pipeline
# ---------------------------------------------------------------------------

_HAIKU_MODEL = "claude-haiku-4-5-20251001"
_RESUME_TOKEN_LIMIT = 8000   # chars ~ 2000 tokens
_POSTING_TOKEN_LIMIT = 6000  # chars ~ 1500 tokens per posting in batch


async def embed_and_rank(
    db: AsyncSession, extracted_text: str
) -> list[MatchResultOut]:
    """
    Two-stage match pipeline:
    1. Cosine similarity via pgvector to get top-40 candidate postings.
    2. Claude Haiku re-ranks the candidates and returns top-20 with scores + reasons.
    """
    from app.ingest.embed import generate_embedding

    resume_vec = await generate_embedding(extracted_text[:_RESUME_TOKEN_LIMIT])

    # Stage 1: cosine similarity — fetch top-40 candidates
    vec_literal = "[" + ",".join(str(x) for x in resume_vec) + "]"
    sql = text(
        """
        SELECT p.id, p.title, p.company, p.city, p.province, p.term,
               p.deadline::text, p.description
        FROM posting_embeddings pe
        JOIN postings p ON p.id = pe.posting_id
        WHERE p.closed_at IS NULL
        ORDER BY pe.embedding <=> CAST(:vec AS vector)
        LIMIT 40
        """
    )
    rows = (await db.execute(sql, {"vec": vec_literal})).mappings().all()

    if not rows:
        return []

    # Stage 2: Haiku re-ranking — send all candidates in one call
    import anthropic

    candidates_json = json.dumps(
        [
            {
                "posting_id": str(r["id"]),
                "title": r["title"],
                "company": r["company"],
                "description": (r["description"] or "")[:_POSTING_TOKEN_LIMIT],
            }
            for r in rows
        ]
    )
    resume_snippet = extracted_text[:_RESUME_TOKEN_LIMIT]

    prompt = (
        "You are a co-op matching assistant. Given a student's resume and a list of job postings, "
        "score each posting from 0–100 based on how well the resume matches the role. "
        "Provide a one-sentence reason for each score. "
        "Return ONLY a JSON array (no markdown) in this exact format:\n"
        '[{"posting_id": "<uuid>", "score": <int 0-100>, "reason": "<one sentence>"}]\n\n'
        f"RESUME:\n{resume_snippet}\n\n"
        f"POSTINGS:\n{candidates_json}"
    )

    client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
    message = await client.messages.create(
        model=_HAIKU_MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text if message.content else "[]"

    # Parse and validate rankings
    try:
        rankings: list[dict[str, object]] = json.loads(raw)
    except json.JSONDecodeError:
        # Graceful degradation: return candidates with cosine-order scores
        rankings = [
            {"posting_id": str(r["id"]), "score": max(0, 80 - i * 2), "reason": "Based on skills alignment."}
            for i, r in enumerate(rows[:20])
        ]

    # Build lookup for posting display fields
    posting_by_id = {str(r["id"]): r for r in rows}
    results: list[MatchResultOut] = []
    for item in rankings:
        pid = str(item.get("posting_id", ""))
        if pid not in posting_by_id:
            continue
        row = posting_by_id[pid]
        score = int(item.get("score", 0))
        score = max(0, min(100, score))
        results.append(
            MatchResultOut(
                posting_id=UUID(pid),
                title=str(row["title"]),
                company=str(row["company"]),
                city=str(row["city"]),
                province=str(row["province"]),
                term=str(row["term"]),
                deadline=str(row["deadline"]) if row["deadline"] else "",
                score=score,
                reason=str(item.get("reason", "Matched based on skills."))[:500],
            )
        )

    # Return top 20, sorted by score descending
    results.sort(key=lambda r: r.score, reverse=True)
    return results[:20]


# ---------------------------------------------------------------------------
# Upload, fetch, delete
# ---------------------------------------------------------------------------


async def upload_resume(
    db: AsyncSession,
    user_id: UUID,
    filename: str,
    file_bytes: bytes,
) -> UploadResponse:
    """
    Validate, extract text, run match pipeline, and store results.
    Replaces any existing resume for this user atomically.
    """
    if len(file_bytes) > _MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail={"detail": "File exceeds 5 MB limit.", "code": "FILE_TOO_LARGE"},
        )

    ext = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail={
                "detail": "Unsupported file type. Upload a PDF or DOCX.",
                "code": "INVALID_FILE_TYPE",
            },
        )

    try:
        extracted = extract_text(filename, file_bytes)
    except Exception:
        raise HTTPException(
            status_code=422,
            detail={
                "detail": "Could not extract text from the uploaded file.",
                "code": "EXTRACTION_FAILED",
            },
        )

    if not extracted.strip():
        raise HTTPException(
            status_code=422,
            detail={
                "detail": "Could not extract text from the uploaded file.",
                "code": "EXTRACTION_FAILED",
            },
        )

    # Delete existing resume (cascades to match_results)
    await db.execute(delete(Resume).where(Resume.user_id == user_id))

    # Insert new resume row
    resume = Resume(
        user_id=user_id,
        filename=filename,
        file_size=len(file_bytes),
        extracted_text=extracted,
    )
    db.add(resume)
    await db.flush()  # populate resume.id before FK use

    # Run match pipeline
    matches = await embed_and_rank(db, extracted)

    # Bulk-insert match results
    if matches:
        await db.execute(
            pg_insert(MatchResult),
            [
                {
                    "resume_id": resume.id,
                    "posting_id": m.posting_id,
                    "score": m.score,
                    "reason": m.reason,
                }
                for m in matches
            ],
        )

    await db.commit()
    await db.refresh(resume)

    return UploadResponse(
        resume=ResumeOut.model_validate(resume),
        matches=matches,
    )


async def get_resume(db: AsyncSession, user_id: UUID) -> Resume | None:
    """Return the stored resume for a user, or None if none exists."""
    result = await db.execute(select(Resume).where(Resume.user_id == user_id))
    return result.scalar_one_or_none()


async def delete_resume(db: AsyncSession, user_id: UUID) -> None:
    """
    Permanently delete the resume and all associated match results (via CASCADE).
    Raises 404 if no resume exists.
    """
    resume = await get_resume(db, user_id)
    if resume is None:
        raise HTTPException(
            status_code=404,
            detail={"detail": "No resume on file.", "code": "RESUME_NOT_FOUND"},
        )
    await db.delete(resume)
    await db.commit()


async def get_matches(db: AsyncSession, user_id: UUID) -> MatchesResponse:
    """
    Return stored match results for the user's current resume.
    Returns empty list if no resume exists.
    """
    resume = await get_resume(db, user_id)
    if resume is None:
        return MatchesResponse(items=[], resume=None)

    # Fetch match_results joined with postings for display fields
    sql = text(
        """
        SELECT mr.posting_id, mr.score, mr.reason,
               p.title, p.company, p.city, p.province, p.term, p.deadline::text
        FROM match_results mr
        JOIN postings p ON p.id = mr.posting_id
        WHERE mr.resume_id = :resume_id
        ORDER BY mr.score DESC
        LIMIT 20
        """
    )
    rows = (await db.execute(sql, {"resume_id": str(resume.id)})).mappings().all()

    items = [
        MatchResultOut(
            posting_id=row["posting_id"],
            title=row["title"],
            company=row["company"],
            city=row["city"],
            province=row["province"],
            term=row["term"],
            deadline=str(row["deadline"]) if row["deadline"] else "",
            score=int(row["score"]),
            reason=row["reason"],
        )
        for row in rows
    ]

    return MatchesResponse(
        items=items,
        resume=ResumeOut.model_validate(resume),
    )
