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
    What the student is looking for, set before or after uploading. Matching only looks at
    open jobs that fit these. Keywords like "data analyst" push fitting jobs higher.
    """

    categories: list[CategoryKey] = Field(default=[], max_length=9)
    keywords: str = Field(default="", max_length=100)
    province: str = Field(default="", max_length=2)
    city: str = Field(default="", max_length=100)
    work_modes: list[WorkMode] = Field(default=[], max_length=3)
    # entry is students plus entry level with no senior titles. students is co-op and intern only
    level: Literal["entry", "students", "all"] = "entry"
    # About the student. Leave blank and we read it from the resume (see detect_education)
    program: ProgramKey | Literal[""] = ""
    degree: Degree = ""
    grad_year: int | None = Field(default=None, ge=2000, le=2100)
    # The co-op term they want like "Summer 2027". Jobs for that term rank higher
    term: str = Field(default="", max_length=20)
    # Countries to include. Most students want Canada and some also do a US term
    countries: list[Literal["CA", "US"]] = Field(default=["CA"], max_length=2)


class DetectedEducation(BaseModel):
    """What we read from the education part of the resume. Blank when we could not find it."""

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
    # The job's skills split into ones the resume shows and ones it does not
    matched_skills: list[str] = []
    missing_skills: list[str] = []
    country: str = "CA"
    # Why this job fits the student based on its description. Program, grad year, term and role
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
    mode "question"      answers `question` with sources and needs a question
    mode "tailor"        says how to tailor this resume for the job
    mode "cover_letter"  writes a short cover letter opening for the job
    """

    question: str = Field(default="", max_length=2000)
    mode: Literal["question", "tailor", "cover_letter"] = "question"

    @model_validator(mode="after")
    def question_required_for_questions(self) -> "AskRequest":
        if self.mode == "question" and not self.question.strip():
            raise ValueError("question must not be empty or whitespace-only")
        return self
