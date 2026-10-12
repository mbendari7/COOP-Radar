from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.posting import WorkMode
from app.services.categories import CategoryKey


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


class MatchesResponse(BaseModel):
    items: list[MatchResultOut]
    resume: ResumeOut | None
    preferences: JobPreferences | None = None


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
