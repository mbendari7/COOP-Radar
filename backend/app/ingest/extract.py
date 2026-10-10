"""
Skill and field extraction from raw posting text.

Two-stage process:
  1. Regex/keyword match against the skills taxonomy (fast, no API call)
  2. If confidence < 0.6: LLM fallback via Claude Haiku to extract structured fields
"""

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class ExtractedFields:
    city: str | None = None
    work_mode: str | None = None
    term: str | None = None
    duration_months: int | None = None
    skills: list[str] = field(default_factory=list)
    confidence_map: dict[str, float] = field(default_factory=dict)


async def extract_fields(db: AsyncSession, text: str) -> ExtractedFields:
    """
    Extract structured fields from raw posting text.

    Step 1: regex/keyword match against the skills taxonomy
    Step 2: if confidence < 0.6, call Claude Haiku for a structured extraction
    """
    from app.models.skill import Skill

    # Load taxonomy from DB
    stmt = select(Skill.name, Skill.aliases)
    rows = (await db.execute(stmt)).all()
    taxonomy: list[tuple[str, list[str]]] = [(row[0], row[1]) for row in rows]

    # --- Stage 1: regex match ---
    matched_skills: list[str] = []
    text_lower = text.lower()

    for name, aliases in taxonomy:
        candidates = [name] + (aliases or [])
        for candidate in candidates:
            pattern = r"\b" + re.escape(candidate.lower()) + r"\b"
            if re.search(pattern, text_lower):
                matched_skills.append(name)
                break  # don't count the same skill twice

    # Simple heuristic confidence: ratio of fields we can extract via regex
    simple_fields_found = 0
    total_simple_fields = 4  # work_mode, city, term, skills

    work_mode: str | None = None
    for mode in ("remote", "hybrid", "onsite"):
        if mode in text_lower:
            work_mode = mode
            simple_fields_found += 1
            break

    if matched_skills:
        simple_fields_found += 1

    # Very rough term detection
    term: str | None = None
    for season in ("summer", "fall", "winter", "spring"):
        m = re.search(rf"\b{season}\s+(\d{{4}})\b", text_lower)
        if m:
            term = f"{season.capitalize()} {m.group(1)}"
            simple_fields_found += 1
            break

    confidence = simple_fields_found / total_simple_fields

    if confidence < 0.6 and taxonomy:
        # --- Stage 2: LLM fallback ---
        llm_result = await _llm_extract(text, [name for name, _ in taxonomy])
        if llm_result:
            if llm_result.get("work_mode"):
                work_mode = llm_result["work_mode"]
            if llm_result.get("term"):
                term = llm_result["term"]
            if llm_result.get("skills"):
                matched_skills = llm_result["skills"]

    return ExtractedFields(
        work_mode=work_mode,
        term=term,
        skills=matched_skills,
        confidence_map={
            "work_mode": 1.0 if work_mode else 0.0,
            "term": 1.0 if term else 0.0,
            "skills": min(1.0, len(matched_skills) / 3.0),
        },
    )


async def _llm_extract(text: str, taxonomy: list[str]) -> dict[str, Any] | None:
    """Call Claude Haiku to extract structured fields when regex confidence is low."""
    import anthropic

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return None

    client = anthropic.AsyncAnthropic(api_key=api_key)
    taxonomy_sample = ", ".join(taxonomy[:50])  # keep prompt short

    prompt = (
        f"Extract structured fields from this job posting as JSON.\n"
        f"Return only valid JSON with keys: work_mode (onsite/hybrid/remote or null), "
        f"term (e.g. 'Summer 2027' or null), duration_months (int or null), "
        f"skills (list of strings from this taxonomy: {taxonomy_sample}).\n\n"
        f"Job posting:\n{text[:2000]}"
    )

    try:
        message = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        content = message.content[0].text if message.content else ""
        # Extract JSON from the response
        json_match = re.search(r"\{[^}]+\}", content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except Exception:  # noqa: BLE001
        pass

    return None
