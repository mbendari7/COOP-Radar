"""
Resume router — upload, view, delete, match results, and streaming Q&A.

Route order:
  POST   /api/resume                      upload + match
  GET    /api/resume                      metadata
  DELETE /api/resume                      delete
  GET    /api/resume/matches              stored match results
  PUT    /api/resume/preferences          save what you're looking for + re-match
  POST   /api/resume/matches/{posting_id}/ask  SSE stream Q&A
"""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import AICredentials, ai_credentials
from app.db import get_db
from app.deps import get_current_user
from app.models.resume import Resume
from app.models.user import User
from app.schemas.insights import ResumeInsights
from app.schemas.resume import (
    AskRequest,
    JobPreferences,
    MatchesResponse,
    ResumeOut,
    UploadResponse,
)
from app.services.insights import generate_ai_insights, get_insights
from app.services.resume import (
    delete_resume,
    get_matches,
    get_resume,
    rematch_resume,
    update_preferences,
    upload_resume,
)
from app.services.usage import consume_ai_quota
from app.store import Store, get_store

router = APIRouter(prefix="/resume", tags=["resume"])


@router.post("", response_model=UploadResponse, status_code=status.HTTP_200_OK)
async def upload_resume_endpoint(
    file: UploadFile = File(...),
    preferences: str | None = Form(default=None, max_length=2000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    store: Store = Depends(get_store),
    creds: AICredentials | None = Depends(ai_credentials("rank", optional=True)),
) -> UploadResponse:
    """
    Upload a resume (PDF/DOCX, ≤5 MB), extract text, run match pipeline,
    store results, and return ranked matches. With the visitor's AI key (X-AI-* headers) the
    AI ranks and explains matches; without any key, matches are ranked by skill overlap for
    free. Only the site owner's fallback key counts toward the daily AI limit.
    `preferences` (optional) is a JobPreferences JSON object: what the student is looking for.
    """
    prefs = _parse_preferences(preferences)
    if creds is not None and creds.source == "server":
        await consume_ai_quota(store, current_user.id)
    file_bytes = await file.read()
    filename = file.filename or "resume"
    return await upload_resume(db, current_user.id, filename, file_bytes, creds, prefs)


def _parse_preferences(raw: str | None) -> JobPreferences | None:
    if not raw:
        return None
    try:
        return JobPreferences.model_validate_json(raw)
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"detail": "Those job preferences aren't valid.", "code": "INVALID_PREFERENCES"},
        ) from exc


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
    store: Store = Depends(get_store),
    creds: AICredentials = Depends(ai_credentials("chat")),
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

    # Only the site owner's key is limited; visitors' own keys are theirs to spend
    if creds.source == "server":
        await consume_ai_quota(store, current_user.id)

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
        stream_answer(creds, posting_text, resume.extracted_text, body.question, body.mode),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _require_resume(db: AsyncSession, user: User) -> Resume:
    resume = await get_resume(db, user.id)
    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": "Upload a resume first.", "code": "RESUME_NOT_FOUND"},
        )
    return resume


@router.get("/insights", response_model=ResumeInsights)
async def resume_insights(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResumeInsights:
    """Skills found + in-demand skills you're missing (free), plus the cached AI review if any."""
    return await get_insights(db, await _require_resume(db, current_user))


@router.post("/insights", response_model=ResumeInsights)
async def generate_resume_insights(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    store: Store = Depends(get_store),
    creds: AICredentials = Depends(ai_credentials("chat")),
) -> ResumeInsights:
    """Run the AI resume review on the visitor's key (strengths, tips, roles) and cache it."""
    resume = await _require_resume(db, current_user)
    if creds.source == "server":
        await consume_ai_quota(store, current_user.id)
    return await generate_ai_insights(db, resume, creds)


@router.put("/preferences", response_model=UploadResponse)
async def update_preferences_endpoint(
    body: JobPreferences,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    creds: AICredentials | None = Depends(ai_credentials("rank", optional=True)),
) -> UploadResponse:
    """
    Save what the student is looking for (job types, location, work mode, level, keywords)
    and re-match the stored resume against it. Uses the visitor's own AI key if they set one;
    otherwise the free ranking, so changing filters never spends the site owner's AI quota.
    """
    resume = await _require_resume(db, current_user)
    if creds is not None and creds.source == "server":
        creds = None
    return await update_preferences(db, resume, body, creds)


@router.post("/rematch", response_model=UploadResponse)
async def rematch_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    store: Store = Depends(get_store),
    creds: AICredentials = Depends(ai_credentials("rank")),
) -> UploadResponse:
    """Re-rank the stored resume against today's postings with the visitor's AI."""
    resume = await _require_resume(db, current_user)
    if creds.source == "server":
        await consume_ai_quota(store, current_user.id)
    return await rematch_resume(db, resume, creds)
