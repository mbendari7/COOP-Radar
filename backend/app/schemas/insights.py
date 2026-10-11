"""Schemas for resume insights."""

from pydantic import BaseModel


class DemandSkill(BaseModel):
    """A skill employers ask for, and how many open postings ask for it."""

    skill: str
    postings: int


class AIInsights(BaseModel):
    """The AI's resume review (generated with the visitor's own key, cached on the resume)."""

    summary: str = ""
    strengths: list[str] = []
    improvements: list[str] = []
    tailoring_tips: list[str] = []
    roles_to_search: list[str] = []
    keywords_to_add: list[str] = []


class ResumeInsights(BaseModel):
    """Free insights (always present) plus the AI review (None until requested)."""

    skills_found: list[str]
    in_demand_missing: list[DemandSkill]
    ai: AIInsights | None = None
