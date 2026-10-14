"""
Make your resume fit one job. Free, plain rules, no AI.

We compare the saved resume with one job and give back
  skills    the job's skills the resume shows and the ones it does not
  keywords  the words the job repeats most, found or missing on the resume
  checks    plain yes or no checks, like program, grad year, term, language and numbers
  tips      the edits to make, most useful first

Recruiters and applicant tracking systems look for the job's own words, so most tips are
about saying what you already did in the job's words. We never tell anyone to claim a skill
they do not have, and every tip says "if you have it" where it matters.
"""

import re
from collections import Counter
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.posting import Posting
from app.schemas.align import AlignCheck, ResumeAlignment
from app.services.education import FIELD_LABELS, PROGRAMS, detect_education
from app.services.resume import get_resume, skills_in_text

_WORD = re.compile(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ+#&/.-]*[A-Za-zÀ-ÿ+#]")
_STOP = {
    "a", "about", "above", "across", "after", "again", "against", "all", "also", "am", "an",
    "and", "any", "are", "as", "at", "be", "because", "been", "before", "being", "below",
    "between", "both", "but", "by", "can", "could", "did", "do", "does", "doing", "down",
    "during", "each", "either", "etc", "every", "few", "for", "from", "further", "had", "has",
    "have", "having", "he", "her", "here", "hers", "him", "his", "how", "i", "if", "in", "into",
    "is", "it", "its", "itself", "just", "may", "me", "might", "more", "most", "must", "my",
    "no", "nor", "not", "now", "of", "off", "on", "once", "only", "or", "other", "our", "ours",
    "out", "over", "own", "per", "please", "same", "shall", "she", "should", "so", "some",
    "such", "than", "that", "the", "their", "them", "then", "there", "these", "they", "this",
    "those", "through", "to", "too", "under", "until", "up", "upon", "us", "very", "via", "was",
    "we", "were", "what", "when", "where", "which", "while", "who", "whom", "why", "will",
    "with", "within", "would", "you", "your", "yours", "ability", "able", "account", "activities",
    "additional", "apply", "applicants", "applications", "applying", "based",
    "benefits", "best", "build", "building", "candidate", "candidates", "career", "careers",
    "company", "core", "create", "culture", "day", "days", "degree", "description", "diverse",
    "diversity", "duties", "employee", "employees", "employer", "employment", "environment",
    "equal", "excellent", "experience", "experiences", "fast", "first", "focus",
    "following", "full", "help", "high", "highly", "hire", "hiring", "ideal", "include",
    "includes", "including", "inclusive", "individual", "individuals", "information", "job",
    "jobs", "join", "key", "know", "knowledge", "learn", "learning", "least", "level", "life",
    "like", "looking", "make", "making", "many", "member", "members", "new", "number", "offer",
    "offers", "one", "opportunities", "opportunity", "part", "people", "perform", "plus",
    "position", "positions", "preferred", "provide", "provides", "qualifications", "qualified",
    "related", "required", "requirements", "responsibilities", "responsible", "role", "roles",
    "skill", "skills", "strong", "student", "students", "success", "successful", "support",
    "team", "teams", "time", "title", "two", "use", "used", "using", "value", "values", "want",
    "way", "ways", "well", "work", "working", "works", "world", "year", "years", "canada",
    "canadian", "toronto", "ontario", "montreal", "vancouver", "calgary", "ottawa", "remote",
    "hybrid", "onsite", "office", "intern", "interns", "internship", "co-op", "coop", "term",
    "terms", "month", "months", "summer", "winter", "fall", "spring", "disability",
    "accommodation", "accommodations", "status", "gender", "race", "religion", "orientation",
    # Pay, perks and benefits text that every posting repeats
    "pay", "salary", "compensation", "bonus", "equity", "stock", "range", "base", "total",
    "insurance", "health", "dental", "vision", "wellness", "vacation", "perk", "perks",
    "flexible", "protection", "drive", "driven", "performance", "eligible", "eligibility",
    "annual", "hour", "hourly", "region", "location", "locations", "country",
    # Seniority and shape words that say nothing about the work itself
    "senior", "junior", "lead", "principal", "staff", "manager", "associate", "stack",
    "grad", "graduate", "entry",
}
# Results with numbers like "30%", "$5k" or "120 accounts". Years and phone numbers do not count
_NUMBERS = re.compile(
    r"\d+(?:[.,]\d+)?\s*(?:%|percent|\+|k\b|x\b)|\$\s?\d|\b\d{1,3}(?:,\d{3})*\s+[a-z]{3,}"
)
_FRENCH_ASKED = re.compile(r"(?i)\b(bilingual|french|français|francais)\b")
_FRENCH_ON_RESUME = re.compile(r"(?i)\b(french|français|francais|bilingual)\b")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_MAX_KEYWORDS = 12


def _normal(word: str) -> str:
    w = word.lower().strip(".-/")
    if len(w) > 4 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) > 4 and w.endswith("s") and not w.endswith("ss"):
        return w[:-1]
    return w


def job_keywords(title: str, description: str, company: str = "") -> list[str]:
    """
    The words and two word phrases a job leans on most, best first. Title words count extra
    since they say what the job is. Common filler and place names are left out.
    """
    skip = _STOP | {_normal(w) for w in _WORD.findall(company)}
    counts: Counter[str] = Counter()
    shown: dict[str, str] = {}

    def add(words: list[str], weight: int) -> None:
        normals = [_normal(w) for w in words]
        for raw, norm in zip(words, normals, strict=True):
            if len(norm) >= 3 and norm not in skip and not norm.isdigit():
                counts[norm] += weight
                shown.setdefault(norm, raw if not raw.isupper() or len(raw) <= 5 else raw.lower())
        for i in range(len(normals) - 1):
            a, b = normals[i], normals[i + 1]
            if len(a) >= 3 and len(b) >= 3 and a not in skip and b not in skip:
                key = f"{a} {b}"
                counts[key] += weight
                shown.setdefault(key, f"{words[i]} {words[i + 1]}".lower())

    add(_WORD.findall(title), 3)
    for line in description.splitlines():
        add(_WORD.findall(line), 1)

    # A phrase that shows up twice is a stronger signal than either of its words alone
    picked: list[str] = []
    for key, n in counts.most_common():
        if n < 2:
            break
        if " " not in key and any(key in p.split(" ") for p in picked):
            continue
        picked.append(key)
        if len(picked) >= _MAX_KEYWORDS:
            break
    return [shown[k] for k in picked]


def _on_resume(keyword: str, resume_normals: set[str], resume_lower: str) -> bool:
    parts = keyword.lower().split(" ")
    if len(parts) > 1:
        return keyword.lower() in resume_lower or all(_normal(p) in resume_normals for p in parts)
    return _normal(keyword) in resume_normals


def align(posting: Posting, resume_text: str) -> ResumeAlignment:
    """Every check and tip for this resume and this job. Pure Python so it is easy to test."""
    description = posting.description or ""
    resume_lower = resume_text.lower()
    resume_normals = {_normal(w) for w in _WORD.findall(resume_text)}

    skills = list(posting.skills or [])
    have = skills_in_text(skills, resume_text)
    missing = [s for s in skills if s not in have]

    keywords = job_keywords(posting.title, description, posting.company)
    found = [k for k in keywords if _on_resume(k, resume_normals, resume_lower)]
    absent = [k for k in keywords if k not in found]

    education = detect_education(resume_text)
    checks: list[AlignCheck] = []
    tips: list[str] = []

    if skills:
        checks.append(AlignCheck(
            ok=len(have) * 2 >= len(skills),
            text=f"Your resume shows {len(have)} of the {len(skills)} skills this job lists",
        ))
    if missing:
        tips.append(
            "If you have used " + _join(missing[:5]) + ", name them in a skills line and in the "
            "bullet where you used them. Course projects count."
        )

    fields = list(posting.fields_of_study or [])
    if fields:
        labels = [FIELD_LABELS.get(f, f) for f in fields]
        program_fields = set(PROGRAMS[education.program].fields) if education.program else set()
        fits = bool(program_fields & set(fields))
        checks.append(AlignCheck(
            ok=fits,
            text=("Your program is one it asks for" if fits
                  else f"It asks for {_join(labels[:3])}"),
        ))
        if not fits:
            tips.append(
                f"It asks for {_join(labels[:3])}. If you took courses in these, list them under "
                "your education as relevant courses. Many employers still read every application."
            )

    years = list(posting.grad_years or [])
    if years:
        if education.grad_year:
            ok = education.grad_year in years
            checks.append(AlignCheck(
                ok=ok,
                text=(f"Your graduation year {education.grad_year} is one it asks for" if ok
                      else f"It asks for {' or '.join(map(str, years))} grads and you finish in "
                           f"{education.grad_year}"),
            ))
        else:
            checks.append(AlignCheck(ok=False, text="We could not find your graduation year"))
            tips.append(
                "Add your expected graduation date to your education line, like "
                f"\"Expected graduation: April {years[0]}\". This job asks for it."
            )

    term = posting.term if posting.term and posting.term != "Open" else ""
    if term:
        season = term.split(" ", 1)[0].lower()
        stated = season in resume_lower or term.lower() in resume_lower
        checks.append(AlignCheck(
            ok=stated,
            text=("Your resume says you are free for this term" if stated
                  else f"Your resume does not say you are free for {term}"),
        ))
        if not stated:
            length = f"{posting.duration_months} month " if posting.duration_months else ""
            tips.append(
                f"Add one line near the top: \"Available for a {length}{term} co-op term\". "
                "Recruiters filter by availability first."
            )

    if _FRENCH_ASKED.search(description):
        has_french = bool(_FRENCH_ON_RESUME.search(resume_text))
        checks.append(AlignCheck(
            ok=has_french,
            text="Your resume mentions French" if has_french else "It mentions French or bilingual",
        ))
        if not has_french:
            tips.append(
                "It mentions French or being bilingual. If you speak any French, add a languages "
                "line with your level, like \"French: intermediate\"."
            )

    if absent:
        tips.append(
            "Use the job's own words where they are true for you: " + _join(absent[:6]) + ". "
            "Applicant tracking systems look for these exact words."
        )

    numbers = len(_NUMBERS.findall(resume_text))
    checks.append(AlignCheck(
        ok=numbers >= 3,
        text=("Your bullets show results with numbers" if numbers >= 3
              else "Few of your bullets show results with numbers"),
    ))
    if numbers < 3:
        tips.append(
            "Add a number to your best bullets, like how many people, how much time saved or "
            "how big the project was. \"Cut report time by 30%\" reads stronger than "
            "\"made reports\"."
        )

    title_words = [
        w for w in _WORD.findall(posting.title) if _normal(w) not in _STOP and len(w) > 3
    ]
    if title_words and not any(_normal(w) in resume_normals for w in title_words):
        tips.append(
            "Name this kind of work in the summary line at the top, using the title's own words "
            f"where they are true for you: {_join(title_words[:3], 'and')}."
        )

    if not _EMAIL.search(resume_text):
        tips.append("We could not find an email address. Put your email and phone at the top.")
    if len(resume_text.split()) > 900:
        tips.append("Your resume is long for a co-op application. Aim for one page, two at most.")

    return ResumeAlignment(
        posting_id=posting.id,
        title=posting.title,
        company=posting.company,
        matched_skills=have,
        missing_skills=missing,
        keywords_found=found,
        keywords_missing=absent,
        checks=checks,
        tips=tips,
    )


def _join(items: list[str], last: str = "or") -> str:
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + f" {last} " + items[-1]


async def align_resume(db: AsyncSession, user_id: UUID, posting_id: UUID) -> ResumeAlignment:
    """The alignment for this person's saved resume and one job. 404 when either is missing."""
    resume = await get_resume(db, user_id)
    if resume is None:
        raise HTTPException(
            status_code=404,
            detail={"detail": "Upload a resume first.", "code": "RESUME_NOT_FOUND"},
        )
    posting = await db.get(Posting, posting_id)
    if posting is None:
        raise HTTPException(
            status_code=404,
            detail={"detail": "Posting not found", "code": "POSTING_NOT_FOUND"},
        )
    return align(posting, resume.extracted_text)
