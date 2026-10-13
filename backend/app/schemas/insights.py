"""Shapes for resume insights."""

from pydantic import BaseModel


class DemandSkill(BaseModel):
    """A skill employers ask for and how many open jobs ask for it."""

    skill: str
    postings: int


class AIInsights(BaseModel):
    """The AI resume review, made with the visitor's own key and saved on the resume."""

    summary: str = ""
    strengths: list[str] = []
    improvements: list[str] = []
    tailoring_tips: list[str] = []
    roles_to_search: list[str] = []
    keywords_to_add: list[str] = []


class ResumeInsights(BaseModel):
    """Free insights that are always there plus the AI review, which is None until asked for."""

    skills_found: list[str]
    in_demand_missing: list[DemandSkill]
    ai: AIInsights | None = None
