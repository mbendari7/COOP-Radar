"""
Resume routes for upload, view, delete, matches and the streamed Q and A.

The routes
  POST   /api/resume                           upload and match
  GET    /api/resume                           details about the file
  DELETE /api/resume                           delete it
  GET    /api/resume/matches                   saved match results
  GET    /api/resume/align/{posting_id}        how to make the resume fit one job, free
  PUT    /api/resume/preferences               save what you want and match again
  POST   /api/resume/matches/{posting_id}/ask  streamed answers about one job
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
from app.schemas.align import ResumeAlignment
from app.schemas.insights import ResumeInsights
from app.schemas.resume import (
    AskRequest,
    JobPreferences,
    MatchesResponse,
    ResumeOut,
    UploadResponse,
)
from app.services.align import align_resume
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
    Upload a resume as PDF or DOCX up to 5 MB, read the text, match it and save
    and return the ranked matches. With the visitor's own AI key the AI ranks and
    explains the matches. With no key at all we rank by skill overlap for free.
    Only the owner's backup key counts toward the daily AI limit.
    `preferences` is optional JSON for what the student is looking for.
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
    """Details about the saved resume for the signed in person."""
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
    """Delete the resume and every match for good."""
    await delete_resume(db, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/matches", response_model=MatchesResponse, status_code=status.HTTP_200_OK)
async def get_matches_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MatchesResponse:
    """Saved ranked matches. An empty list if there is no resume yet."""
    return await get_matches(db, current_user.id)


@router.get(
    "/align/{posting_id}", response_model=ResumeAlignment, status_code=status.HTTP_200_OK
)
async def align_endpoint(
    posting_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResumeAlignment:
    """
    How to make the saved resume fit one job. Skills and words it has or lacks, plain checks
    and the edits to make. No AI, so it is free and instant. 404 with no resume or job.
    """
    return await align_resume(db, current_user.id, posting_id)


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
    Stream an answer with sources about one matched job.
    It is a text/event-stream of small pieces that ends with [DONE].
    """
    from app.agent.resume_qa import stream_answer
    from app.models.match_result import MatchResult
    from app.models.posting import Posting

    # Make sure they have a resume
    resume = await get_resume(db, current_user.id)
    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": "No resume on file.", "code": "RESUME_NOT_FOUND"},
        )

    # Make sure this job is one of their matches
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

    # Only the owner's key has a limit. Visitors can spend their own key however they like
    if creds.source == "server":
        await consume_ai_quota(store, current_user.id)

    # Get the job description
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
    """Skills we found and popular skills you are missing for free, plus the saved AI review."""
    return await get_insights(db, await _require_resume(db, current_user))


@router.post("/insights", response_model=ResumeInsights)
async def generate_resume_insights(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    store: Store = Depends(get_store),
    creds: AICredentials = Depends(ai_credentials("chat")),
) -> ResumeInsights:
    """Run the AI resume review on the visitor's key and save it."""
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
    Save what the student wants like job type, place, work mode, level and keywords
    and match the saved resume again. Uses their own AI key if they set one
    and the free ranking if not, so changing filters never spends the owner's AI quota.
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
    """Rank the saved resume against today's jobs again with the visitor's AI."""
    resume = await _require_resume(db, current_user)
    if creds.source == "server":
        await consume_ai_quota(store, current_user.id)
    return await rematch_resume(db, resume, creds)
