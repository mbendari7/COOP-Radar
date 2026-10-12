"""
Temporary accounts — no sign-up needed.

- Demo account ("Try the demo"): pre-filled with sample tracker history and matches.
- Guest account ("Upload your resume" without an account): empty, ready for the visitor's own
  resume. A guest can keep everything by adding an email + password (claim_account).

Original notes on demo accounts — one click, no sign-up, for people trying the hosted site.

Every visitor gets their *own* throwaway account (so visitors never see or overwrite each
other's changes), pre-filled with:
  - six saved postings spread across tracker statuses, with notes and dates
  - a sample resume and up to 20 matches scored by skill overlap (no AI cost)

Temporary accounts are deleted 7 days after creation unless claimed; cleanup runs whenever a
new one is created. Creation is rate-limited per IP address.
"""

import secrets
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application_event import ApplicationEvent
from app.models.match_result import MatchResult
from app.models.posting import Posting
from app.models.resume import Resume
from app.models.saved_posting import ApplicationStatus, SavedPosting
from app.models.user import User
from app.services.auth import _create_session, _ph
from app.store import Store

DEMO_EMAIL_DOMAIN = "demo.coopradar"
DEMO_TTL = timedelta(days=7)  # temporary accounts are deleted after this
_RATE_LIMIT = 10          # demo accounts per IP per hour
_RATE_WINDOW = 60 * 60

DEMO_SKILLS = ["Python", "SQL", "PostgreSQL", "React", "TypeScript", "Docker", "AWS", "Linux"]

DEMO_RESUME = """Alex Rivera — Computer Science (Co-op), 3rd year
Skills: Python, SQL, PostgreSQL, React, TypeScript, Docker, AWS, Linux, Git
Experience
- Software Developer Co-op, Campus IT (Summer 2026): built a FastAPI + PostgreSQL service for
  course-room bookings; containerised it with Docker and deployed to AWS.
- Teaching Assistant, Intro to Programming (Fall 2025): ran Python labs for 60 students.
Projects
- Co-op job tracker: React + TypeScript dashboard with a Python REST API.
- Data pipeline that loads transit data into PostgreSQL and serves charts.
"""

# (status, note, days until the event date or None) for the six demo saves, in order
_TRACKER_PLAN: list[tuple[ApplicationStatus | None, str | None, int | None]] = [
    (ApplicationStatus.offer, "Offer received — reply by Friday", 3),
    (ApplicationStatus.interview, "Technical interview with the platform team", 5),
    (ApplicationStatus.applied, "Applied through the company site", None),
    (ApplicationStatus.applying, "Tailoring resume bullets", None),
    (ApplicationStatus.rejected, "Position filled internally", None),
    (None, None, None),  # saved, no status yet
]


def _client_ip(forwarded_for: str | None, peer: str | None) -> str:
    """First address in X-Forwarded-For (set by the hosting proxy), else the socket peer."""
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return peer or "unknown"


async def _check_rate_limit(store: Store, ip: str) -> None:
    key = f"demo_create:{ip}"
    count = await store.incr(key)
    if count == 1:
        await store.expire(key, _RATE_WINDOW)
    if count > _RATE_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "detail": "Too many demo accounts from this network. Try again in an hour.",
                "code": "RATE_LIMITED",
            },
        )


async def cleanup_expired_demo_users(db: AsyncSession) -> int:
    """Delete demo users older than DEMO_TTL (their data cascades). Returns rows deleted."""
    cutoff = datetime.now(UTC) - DEMO_TTL
    result = await db.execute(
        delete(User).where(User.is_demo.is_(True), User.created_at < cutoff)
    )
    return int(getattr(result, "rowcount", 0) or 0)


def skill_overlap_match(posting_skills: list[str], resume_skills: list[str]) -> tuple[int, str]:
    """Score = share of the posting's skills the resume covers. No AI call involved."""
    have = {s.lower() for s in resume_skills}
    matched = [s for s in posting_skills if s.lower() in have]
    missing = [s for s in posting_skills if s.lower() not in have]
    score = round(100 * len(matched) / len(posting_skills)) if posting_skills else 0
    reason = f"Demo match: you have {', '.join(matched) or 'none of the listed skills'}"
    reason += f"; missing {', '.join(missing)}." if missing else "; no missing skills."
    return score, reason


async def _fill_demo_data(db: AsyncSession, user_id: UUID) -> None:
    open_postings = (
        await db.execute(
            select(Posting)
            .where(Posting.closed_at.is_(None), Posting.deadline >= func.current_date())
            .order_by(Posting.deadline, Posting.id)
        )
    ).scalars().all()

    # Tracker: six postings spread across statuses, with history
    now = datetime.now(UTC)
    for posting, (app_status, note, days) in zip(open_postings[:6], _TRACKER_PLAN, strict=False):
        saved = SavedPosting(
            user_id=user_id,
            posting_id=posting.id,
            status=app_status,
            last_status_at=now if app_status else None,
        )
        db.add(saved)
        await db.flush()
        if app_status is not None:
            db.add(
                ApplicationEvent(
                    saved_posting_id=saved.id,
                    status=app_status,
                    notes=note,
                    event_date=date.today() + timedelta(days=days) if days is not None else None,
                )
            )

    # Resume + matches (skill overlap, so the demo costs nothing and works without API keys)
    resume = Resume(
        user_id=user_id,
        filename="alex-rivera-resume.pdf",
        file_size=len(DEMO_RESUME.encode()),
        extracted_text=DEMO_RESUME,
    )
    db.add(resume)
    await db.flush()

    scored = [(p, *skill_overlap_match(p.skills or [], DEMO_SKILLS)) for p in open_postings]
    scored = [row for row in scored if row[1] > 0]
    scored.sort(key=lambda row: row[1], reverse=True)
    for posting, score, reason in scored[:20]:
        db.add(MatchResult(resume_id=resume.id, posting_id=posting.id, score=score, reason=reason))


async def create_demo_user(
    db: AsyncSession,
    store: Store,
    forwarded_for: str | None,
    peer: str | None,
    prefill: bool = True,
) -> tuple[User, str]:
    """Create a fresh temporary account (pre-filled demo, or an empty guest) and log into it."""
    await _check_rate_limit(store, _client_ip(forwarded_for, peer))
    await cleanup_expired_demo_users(db)

    user = User(
        email=f"demo-{secrets.token_hex(4)}@{DEMO_EMAIL_DOMAIN}",
        # Random password nobody knows — demo accounts are reachable only via this endpoint
        hashed_password=_ph.hash(secrets.token_urlsafe(32)),
        is_demo=True,
    )
    db.add(user)
    await db.flush()
    if prefill:
        await _fill_demo_data(db, user.id)
    await db.commit()
    await db.refresh(user)

    token = await _create_session(store, user.id)
    return user, token


async def claim_account(db: AsyncSession, user: User, email: str, password: str) -> User:
    """Turn a temporary (demo/guest) account into a normal one, keeping all its data."""
    if not user.is_demo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"detail": "This account is already saved.", "code": "ALREADY_CLAIMED"},
        )
    normalised = email.lower().strip()
    taken = (await db.execute(select(User.id).where(User.email == normalised))).first()
    if taken:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"detail": "An account with this email already exists", "code": "EMAIL_TAKEN"},
        )
    user.email = normalised
    user.hashed_password = _ph.hash(password)
    user.is_demo = False
    await db.commit()
    await db.refresh(user)
    return user
