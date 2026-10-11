from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, field_validator


class ResumeOut(BaseModel):
    id: UUID
    filename: str
    file_size: int
    uploaded_at: datetime

    model_config = {"from_attributes": True}


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


class AskRequest(BaseModel):
    question: str

    @field_validator("question")
    @classmethod
    def question_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("question must not be empty or whitespace-only")
        return v
