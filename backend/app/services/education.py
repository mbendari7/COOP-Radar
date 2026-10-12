"""
Programs of study and graduation years, read from job descriptions and resumes. Pure regex, no AI.

Postings: `fields_in_posting` finds the programs a job asks for ("Bachelor's in Computer Science,
Engineering or a related field" -> cs, engineering) and `grad_years_in_posting` the graduation
years it wants ("graduating between December 2026 and June 2027" -> 2026, 2027). Both are stored
on the posting at import time so matching and filtering can use them in SQL.

Resumes: `detect_education` reads the student's program, degree and graduation year from the
education lines, so matching works even when the student hasn't filled those in.
"""

import re
from dataclasses import dataclass
from datetime import date
from typing import Literal

# Field-of-study tags stored on postings: tag -> pattern (searched only in degree sentences)
FIELD_PATTERNS: dict[str, str] = {
    "cs": r"computer science|computing|software engineering|computer engineering|informatics"
          r"|\bcs\b|génie logiciel|informatique",
    "engineering": r"\bengineering\b|\bgénie\b|\bb\.?\s?eng\b|\bmeng\b",
    "electrical": r"electrical|electronics?|ece\b",
    "mechanical": r"mechanical|mechatronics?|aerospace|robotics",
    "data_math": r"data science|statistics|mathematics|\bmath\b|actuarial|quantitative"
                 r"|operations research",
    "business": r"business|commerce|\bmba\b|management|administration",
    "finance": r"finance|accounting|economics|\bcpa\b",
    "marketing": r"marketing|communications|journalism|public relations",
    "design": r"\bdesign\b|human[- ]computer interaction|\bhci\b|fine arts|media arts|visual arts",
    "it": r"information technology|information systems|\bmis\b|cyber ?security|networking",
    "science": r"physics|chemistry|biology|life sciences|biochemistry|geology|earth sciences?"
               r"|environmental science|mining|metallurgy",
}
FIELD_LABELS: dict[str, str] = {
    "cs": "Computer Science / Software", "engineering": "Engineering",
    "electrical": "Electrical / Electronics", "mechanical": "Mechanical / Mechatronics",
    "data_math": "Math, Stats or Data Science", "business": "Business / Commerce",
    "finance": "Finance, Accounting or Economics", "marketing": "Marketing / Communications",
    "design": "Design", "it": "IT / Information Systems", "science": "Science",
}

# A sentence counts as a degree requirement when it mentions one of these
_DEGREE_CUE = re.compile(
    r"(?i)\b(degrees?|major(ing)?|bachelor\w*|master\w*|b\.?\s?sc|b\.?\s?a\.?sc|b\.?\s?eng"
    r"|undergrad\w*|diploma|ph\.?\s?d|field of study|disciplines?|studying|pursuing an?"
    r"|enrolled in|programs? in)\b"
)
_SENTENCES = re.compile(r"[^.\n•;]+")

ProgramKey = Literal[
    "computer_science", "software_engineering", "computer_engineering", "electrical_engineering",
    "mechanical_engineering", "other_engineering", "data_science", "mathematics",
    "information_technology", "business", "finance_accounting", "marketing", "design", "science",
]


@dataclass(frozen=True)
class Program:
    label: str
    resume_pattern: str        # how the program is written on a resume
    fields: tuple[str, ...]    # posting field tags that welcome this program
    categories: tuple[str, ...]  # job types (app/services/categories.py) it leads to


# Order matters for resume detection: specific programs before general ones
PROGRAMS: dict[str, Program] = {
    "software_engineering": Program(
        "Software Engineering", r"software engineering|génie logiciel",
        ("cs", "engineering"), ("software", "data", "it_security")),
    "computer_engineering": Program(
        "Computer Engineering", r"computer engineering|génie informatique",
        ("cs", "engineering", "electrical"), ("software", "hardware", "data")),
    "electrical_engineering": Program(
        "Electrical Engineering", r"electrical (and computer )?engineering|electronics engineering",
        ("electrical", "engineering"), ("hardware", "software")),
    "mechanical_engineering": Program(
        "Mechanical / Mechatronics Engineering",
        r"(mechanical|mechatronics?|aerospace|robotics) engineering",
        ("mechanical", "engineering"), ("hardware",)),
    "data_science": Program(
        "Data Science / Statistics", r"data science|statistics|data analytics",
        ("data_math", "cs"), ("data", "software")),
    "computer_science": Program(
        "Computer Science", r"computer science|computing science|\bcomputing\b|informatique",
        ("cs", "data_math"), ("software", "data", "it_security")),
    "information_technology": Program(
        "Information Technology", r"information technology|information systems|cyber ?security",
        ("it", "cs"), ("it_security", "software")),
    "mathematics": Program(
        "Mathematics", r"mathematics|\bmath\b|actuarial", ("data_math",), ("data", "business")),
    "finance_accounting": Program(
        "Finance / Accounting / Economics", r"finance|accounting|economics",
        ("finance", "business", "data_math"), ("business",)),
    "business": Program(
        "Business / Commerce", r"business|commerce|\bbba\b|\bbcomm?\b|management",
        ("business", "finance", "marketing"), ("business", "product", "sales_marketing")),
    "marketing": Program(
        "Marketing / Communications", r"marketing|communications|journalism",
        ("marketing", "business"), ("sales_marketing", "customer")),
    "design": Program(
        "Design / Media", r"\bdesign\b|fine arts|media arts|interaction design|\bhci\b",
        ("design",), ("design", "product")),
    "other_engineering": Program(
        "Other Engineering (civil, chemical, industrial...)",
        r"(civil|chemical|industrial|systems|environmental|mining|materials|nuclear"
        r"|engineering physics) engineering|\bengineering\b",
        ("engineering", "science"), ("hardware",)),
    "science": Program(
        "Science (physics, chemistry, biology...)",
        r"physics|chemistry|biology|biochemistry|life sciences|geology|earth sciences",
        ("science", "data_math"), ("data", "hardware")),
}

Degree = Literal["", "diploma", "bachelors", "masters", "phd"]
DEGREE_LABELS: dict[str, str] = {
    "diploma": "College diploma", "bachelors": "Bachelor's", "masters": "Master's", "phd": "PhD",
}
_DEGREE_PATTERNS: list[tuple[str, str]] = [
    ("phd", r"\bph\.?\s?d\b|doctor(ate|al)"),
    ("masters", r"\bmaster'?s?\b|\bm\.?\s?sc\b|\bm\.?\s?eng\b|\bmba\b|\bm\.?a\.?sc\b"),
    ("bachelors", r"\bbachelor'?s?\b|\bb\.?\s?sc\b|\bb\.?\s?a\.?\s?sc\b|\bb\.?\s?eng\b|\bbcomm?\b"
                  r"|\bbba\b|\bbmath\b|\bb\.?a\.?\b|honou?rs|undergraduate"),
    ("diploma", r"\bdiploma\b|\bcollege\b|polytechnic|advanced certificate"),
]
_SCHOOL_CUE = re.compile(
    r"(?i)(universit|college|polytechni|institute of technology|école|ecole|\bschool\b|candidate"
    r"|expected|graduat|\bclass of\b|\bmajor\b|\bminor\b|bachelor|master|b\.?\s?sc|b\.?\s?eng"
    r"|\bbcomm?\b|\bbba\b|\bbmath\b|honou?rs|diploma|\bgpa\b|co-?op program)"
)
_YEAR = r"(20[1-4]\d)"


def _sentences_with_degree(text: str) -> list[str]:
    return [s for s in _SENTENCES.findall(text or "") if _DEGREE_CUE.search(s)]


def fields_in_posting(text: str) -> list[str]:
    """Field tags a posting asks for, e.g. ["cs", "engineering"]. Only degree sentences count."""
    sentences = _sentences_with_degree(text)
    found = [
        tag for tag, pattern in FIELD_PATTERNS.items()
        if any(re.search(pattern, s, re.IGNORECASE) for s in sentences)
    ]
    return found


_GRAD_CUE = re.compile(
    r"(?i)(graduat\w*|class of|grad date|convocat\w*|completion of (your|their) degree)"
)


def grad_years_in_posting(text: str, today: date | None = None) -> list[int]:
    """
    Graduation years a posting asks for, from the text right after a graduation phrase:
    "graduating between December 2026 and June 2027" -> [2026, 2027]. Years far in the past or
    future are ignored. Empty = the posting doesn't say.
    """
    this_year = (today or date.today()).year
    years: set[int] = set()
    for cue in _GRAD_CUE.finditer(text or ""):
        window = text[cue.end(): cue.end() + 90]
        window = re.split(r"[.\n;]", window, maxsplit=1)[0]
        for y in re.findall(_YEAR, window):
            if this_year - 1 <= int(y) <= this_year + 6:
                years.add(int(y))
    return sorted(years)


@dataclass
class Education:
    program: str = ""       # a PROGRAMS key, or "" when not found
    degree: str = ""        # a DEGREE_LABELS key, or ""
    grad_year: int | None = None


def _education_lines(text: str) -> list[str]:
    """Resume lines that look like they're about school, plus the two lines after each."""
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    picked: set[int] = set()
    for i, line in enumerate(lines):
        if _SCHOOL_CUE.search(line):
            picked.update(j for j in (i, i + 1, i + 2) if j < len(lines))
    return [lines[i] for i in sorted(picked)]


def detect_education(text: str, today: date | None = None) -> Education:
    """Best guess at the student's program, degree and graduation year from their resume."""
    this_year = (today or date.today()).year
    lines = _education_lines(text)
    joined = "\n".join(lines)
    result = Education()

    for key, program in PROGRAMS.items():
        if re.search(program.resume_pattern, joined, re.IGNORECASE):
            result.program = key
            break
    for key, pattern in _DEGREE_PATTERNS:
        if re.search(pattern, joined, re.IGNORECASE):
            result.degree = key
            break

    # 1. "Expected graduation: April 2028", "Class of 2027", "Graduating 2027"
    explicit = re.search(
        r"(?i)(expected|anticipated|graduat\w*|class of|convocation)\D{0,40}?" + _YEAR, joined
    )
    if explicit:
        result.grad_year = int(explicit.group(2))
        return result
    # 2. "Sept 2023 - Apr 2028" / "2024 – Present": the end of a date range in the education lines
    ends = [
        int(m.group(2))
        for m in re.finditer(_YEAR + r"\s*[-–—to]+\s*(?:[A-Za-z.]+\s*)?" + _YEAR, joined)
    ]
    future = [y for y in ends if y >= this_year - 1]
    if future:
        result.grad_year = max(future)
        return result
    # 3. The latest plausible year mentioned near school
    years = [int(y) for y in re.findall(_YEAR, joined) if this_year <= int(y) <= this_year + 6]
    if years:
        result.grad_year = max(years)
    return result
