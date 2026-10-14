"""What GET /api/resume/align/{posting_id} sends back. See app/services/align.py."""

from uuid import UUID

from pydantic import BaseModel


class AlignCheck(BaseModel):
    """One yes or no check, like "Your program is one it asks for"."""

    ok: bool
    text: str


class ResumeAlignment(BaseModel):
    """How to make the saved resume fit one job. Free and with no AI."""

    posting_id: UUID
    title: str
    company: str
    # The job's skills split into ones the resume shows and ones it does not
    matched_skills: list[str] = []
    missing_skills: list[str] = []
    # The words the job repeats most, split the same way
    keywords_found: list[str] = []
    keywords_missing: list[str] = []
    checks: list[AlignCheck] = []
    # The edits to make, most useful first
    tips: list[str] = []
