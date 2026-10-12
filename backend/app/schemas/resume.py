from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.posting import WorkMode
from app.services.categories import CategoryKey
from app.services.education import Degree, ProgramKey


class ResumeOut(BaseModel):
    id: UUID
    filename: str
    file_size: int
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class JobPreferences(BaseModel):
    """
    What the student is looking for, set before or after uploading. Matching only considers
    open postings that fit these; keywords (e.g. "data analyst") rank fitting postings higher.
    """

    categories: list[CategoryKey] = Field(default=[], max_length=9)
    keywords: str = Field(default="", max_length=100)
    province: str = Field(default="", max_length=2)
    city: str = Field(default="", max_length=100)
    work_modes: list[WorkMode] = Field(default=[], max_length=3)
    # entry: students + entry-level (no senior titles) · students: co-op/intern only · all
    level: Literal["entry", "students", "all"] = "entry"
    # About the student. Blank = read from the resume (see detect_education)
    program: ProgramKey | Literal[""] = ""
    degree: Degree = ""
    grad_year: int | None = Field(default=None, ge=2000, le=2100)
    # Co-op term they want, e.g. "Summer 2027" (jobs for that term rank higher)
    term: str = Field(default="", max_length=20)
    # Countries to include; most students want Canada, some also do a US co-op term
    countries: list[Literal["CA", "US"]] = Field(default=["CA"], max_length=2)


class DetectedEducation(BaseModel):
    """What was read from the resume's education section (blank when not found)."""

    program: ProgramKey | Literal[""] = ""
    program_label: str = ""
    degree: Degree = ""
    grad_year: int | None = None


class MatchResultOut(BaseModel):
    posting_id: UUID
    title: str
    company: str
    city: str
    province: str
    term: str
    deadline: str
    score: int
    reason: str
    work_mode: str = ""
    # The posting's listed skills, split into ones the resume shows and ones it doesn't
    matched_skills: list[str] = []
    missing_skills: list[str] = []
    country: str = "CA"
    # Why this job fits the student, from its description: program, graduation year, term, role
    fit_notes: list[str] = []

    @field_validator("score")
    @classmethod
    def score_range(cls, v: int) -> int:
        if not 0 <= v <= 100:
            raise ValueError("score must be between 0 and 100")
        return v

    @field_validator("reason")
    @classmethod
    def reason_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("reason must not be empty")
        return v[:500]


class UploadResponse(BaseModel):
    resume: ResumeOut
    matches: list[MatchResultOut]
    preferences: JobPreferences | None = None
    education: DetectedEducation | None = None


class MatchesResponse(BaseModel):
    items: list[MatchResultOut]
    resume: ResumeOut | None
    preferences: JobPreferences | None = None
    education: DetectedEducation | None = None


class AskRequest(BaseModel):
    """
    mode "question": answer `question` with citations (question required)
    mode "tailor":   how to tailor this resume for the posting (question optional)
    mode "cover_letter": a short cover-letter opening for the posting (question optional)
    """

    question: str = Field(default="", max_length=2000)
    mode: Literal["question", "tailor", "cover_letter"] = "question"

    @model_validator(mode="after")
    def question_required_for_questions(self) -> "AskRequest":
        if self.mode == "question" and not self.question.strip():
            raise ValueError("question must not be empty or whitespace-only")
        return self
