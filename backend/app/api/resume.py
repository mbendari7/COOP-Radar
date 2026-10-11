"""
Resume router — upload, view, delete, match results, and streaming Q&A.

Route order:
  POST   /api/resume                      upload + match
  GET    /api/resume                      metadata
  DELETE /api/resume                      delete
  GET    /api/resume/matches              stored match results
  POST   /api/resume/matches/{posting_id}/ask  SSE stream Q&A
"""

from uuid import UUID

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import get_current_user
from app.models.user import User
from app.redis import get_redis
from app.schemas.resume import AskRequest, MatchesResponse, ResumeOut, UploadResponse
from app.services.resume import delete_resume, get_matches, get_resume, upload_resume
from app.services.usage import consume_ai_quota

router = APIRouter(prefix="/resume", tags=["resume"])


@router.post("", response_model=UploadResponse, status_code=status.HTTP_200_OK)
async def upload_resume_endpoint(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> UploadResponse:
    """
    Upload a resume (PDF/DOCX, ≤5 MB), extract text, run match pipeline,
    store results, and return ranked matches. Counts toward the daily AI limit.
    """
    await consume_ai_quota(redis, current_user.id)
    file_bytes = await file.read()
    filename = file.filename or "resume"
    return await upload_resume(db, current_user.id, filename, file_bytes)


@router.get("", response_model=ResumeOut, status_code=status.HTTP_200_OK)
async def get_resume_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResumeOut:
    """Return stored resume metadata for the authenticated user."""
    resume = await get_resume(db, current_user.id)
    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": "No resume on file.", "code": "RESUME_NOT_FOUND"},
        )
    return ResumeOut.model_validate(resume)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resume_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Permanently delete the resume and all match results."""
    await delete_resume(db, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/matches", response_model=MatchesResponse, status_code=status.HTTP_200_OK)
async def get_matches_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MatchesResponse:
    """Return stored ranked match results. Empty list if no resume on file."""
    return await get_matches(db, current_user.id)


@router.post("/matches/{posting_id}/ask", status_code=status.HTTP_200_OK)
async def ask_about_posting(
    posting_id: UUID,
    body: AskRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> StreamingResponse:
    """
    Stream a cited Q&A response about a matched posting.
    Response is text/event-stream with delta chunks ending in [DONE].
    """
    from app.agent.resume_qa import stream_answer
    from app.models.match_result import MatchResult
    from app.models.posting import Posting

    # Verify the user has a resume
    resume = await get_resume(db, current_user.id)
    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": "No resume on file.", "code": "RESUME_NOT_FOUND"},
        )

    # Verify posting is in the user's match results
    match_row = (
        await db.execute(
            select(MatchResult).where(
                MatchResult.resume_id == resume.id,
                MatchResult.posting_id == posting_id,
            )
        )
    ).scalar_one_or_none()
    if match_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": "Posting not in your match results.", "code": "MATCH_NOT_FOUND"},
        )

    # Only count questions that will actually reach the model
    await consume_ai_quota(redis, current_user.id)

    # Fetch posting description
    posting = (
        await db.execute(select(Posting).where(Posting.id == posting_id))
    ).scalar_one_or_none()
    posting_text = (
        f"{posting.title} at {posting.company}\n\n{posting.description or ''}"
        if posting
        else match_row.reason
    )

    return StreamingResponse(
        stream_answer(posting_text, resume.extracted_text, body.question),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
