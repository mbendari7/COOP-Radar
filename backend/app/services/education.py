"""
Programs and grad years read from job descriptions and resumes. Just regex, no AI.

Jobs. `fields_in_posting` finds the programs a job asks for, so "Bachelor's in Computer
Science, Engineering or a related field" gives cs and engineering. `grad_years_in_posting`
finds the grad years it wants, so "graduating between December 2026 and June 2027" gives
2026 and 2027. Both get saved on the job when we import it so SQL can match and filter on them.

Resumes. `detect_education` reads the student's program, degree and grad year from the
education lines, so matching works even if the student never filled those in.
"""

import re
from dataclasses import dataclass
from datetime import date
from typing import Literal

# Program tags saved on jobs, tag to pattern. We only search sentences about degrees
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
    "health": r"nursing|health sciences?|kinesiology|pharmacy|public health|biomedical|nutrition"
              r"|medicine|medical|physiotherapy|dental|paramedic",
    "social": r"psychology|sociology|political science|criminology|social work|anthropology"
              r"|\bhistory\b|philosophy|humanities|liberal arts|social sciences?"
              r"|international (development|relations)|public (administration|policy)|\blaw\b",
    "environment": r"environmental (studies|science|management)|geography|urban planning"
                   r"|\bplanning\b|\bgis\b|sustainability",
    "education": r"\beducation\b|teaching|early childhood",
    "trades": r"technician|technologist|engineering technology|skilled trades|apprentice\w*",
}
FIELD_LABELS: dict[str, str] = {
    "cs": "Computer Science / Software", "engineering": "Engineering",
    "electrical": "Electrical / Electronics", "mechanical": "Mechanical / Mechatronics",
    "data_math": "Math, Stats or Data Science", "business": "Business / Commerce",
    "finance": "Finance, Accounting or Economics", "marketing": "Marketing / Communications",
    "design": "Design", "it": "IT / Information Systems", "science": "Science",
    "health": "Health Sciences / Nursing", "social": "Social Sciences / Humanities",
    "environment": "Environment / Geography", "education": "Education",
    "trades": "Technology / Skilled Trades",
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
    "health_sciences", "social_sciences", "environment", "education", "engineering_technology",
]


@dataclass(frozen=True)
class Program:
    label: str
    resume_pattern: str        # how the program shows up on a resume
    fields: tuple[str, ...]    # job program tags that welcome this program
    categories: tuple[str, ...]  # job types it leads to (app/services/categories.py)


# Order matters when reading resumes. Specific programs go before general ones
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
    "engineering_technology": Program(
        "Engineering Technology / Skilled Trades (college)",
        r"engineering technolog\w*|technician|technologist|skilled trades|apprentice\w*",
        ("trades", "engineering"), ("trades", "hardware")),
    "other_engineering": Program(
        "Other Engineering (civil, chemical, industrial...)",
        r"(civil|chemical|industrial|systems|environmental|mining|materials|nuclear"
        r"|engineering physics) engineering|\bengineering\b",
        ("engineering", "science"), ("hardware",)),
    "health_sciences": Program(
        "Health Sciences / Nursing / Kinesiology",
        r"nursing|health sciences?|kinesiology|pharmacy|public health|biomedical|nutrition"
        r"|physiotherapy|paramedic|medical laboratory",
        ("health", "science"), ("health",)),
    "science": Program(
        "Science (physics, chemistry, biology...)",
        r"physics|chemistry|biology|biochemistry|life sciences|geology|earth sciences",
        ("science", "data_math", "health"), ("health", "data", "hardware")),
    "environment": Program(
        "Environment / Geography / Planning",
        r"environmental (studies|science|management)|geography|urban planning|\bgis\b"
        r"|sustainability",
        ("environment", "science"), ("health", "public", "hardware")),
    "education": Program(
        "Education", r"\beducation\b|teaching|early childhood", ("education", "social"),
        ("public",)),
    "social_sciences": Program(
        "Arts / Social Sciences / Humanities",
        r"psychology|sociology|political science|criminology|social work|anthropology"
        r"|\bhistory\b|philosophy|humanities|liberal arts|social sciences?|english literature"
        r"|international (development|relations)|bachelor of arts|\bb\.?a\.?\b",
        ("social",), ("public", "business", "customer")),
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
# Between "Expected" and a year on a resume, these mean the year is about work, not graduation
_NOT_GRADUATION = re.compile(r"(?i)co-?op|intern|work|term|availab|start|placement|position")
# A resume line about the co-op they want, like "Seeking an 8 month co-op from May 2027"
_WORK_TERM_LINE = re.compile(
    r"(?im)^.*\b(seeking|looking for|available|availability|work terms?|co-?op terms?)\b.*$"
)
_SEASON_WORD = r"(?:winter|spring|summer|fall|autumn|hiver|été|ete|printemps|automne)"
# The work term, not graduation: "for the Summer 2027 term", "starting May 2027", "2027 co-op".
# Cut out of the text before we read grad years from it
_TERM_PHRASE = re.compile(
    r"(?i)(?:\b(?:for|during|in)\s+(?:the|a|an|our)?\s*)?\b" + _SEASON_WORD
    + r"\s*(?:/\s*" + _SEASON_WORD + r"\s*)?'?(?:20)?\d{2}\s+"
    r"(?:work\s+)?(?:terms?|internships?|intern\b|co-?ops?|sessions?|semesters?|placements?"
    r"|cohorts?)"
    r"|\b(?:start\w*|begin\w*|commenc\w*|available|availability)\b[^.;\n]{0,30}?\b20\d{2}\b"
    r"|\b20\d{2}\s+(?:work\s+)?(?:terms?|internships?|co-?ops?|placements?)\b"
)


def _sentences_with_degree(text: str) -> list[str]:
    return [s for s in _SENTENCES.findall(text or "") if _DEGREE_CUE.search(s)]


def fields_in_posting(text: str) -> list[str]:
    """Program tags a job asks for, like ["cs", "engineering"]. Only degree sentences count."""
    sentences = _sentences_with_degree(text)
    found = [
        tag for tag, pattern in FIELD_PATTERNS.items()
        if any(re.search(pattern, s, re.IGNORECASE) for s in sentences)
    ]
    return found


# Whole words only, so "undergraduate" and "postgraduate" are never a graduation phrase
_GRAD_CUE = re.compile(
    r"(?i)\b(graduat\w*|class of|grad date|convocat\w*|completion of (your|their) degree)"
)
# "Graduate students" or "graduate degree" is the level of study, not a grad year
_GRAD_LEVEL = re.compile(
    r"(?i)^\s*(students?|degrees?|programs?|studies|school|level|positions?|roles?"
    r"|opportunit\w*|(or|and) undergrad\w*)\b"
)


def grad_years_in_posting(text: str, today: date | None = None) -> list[int]:
    """
    Grad years a job asks for, read from the text right after a graduation phrase.
    "graduating between December 2026 and June 2027" gives [2026, 2027]. Years way in the past
    or future are ignored. Empty means the job does not say.
    The work term is something else. "Undergraduate students for the Summer 2027 term" asks
    for no grad year, it is a Summer 2027 job (app/ingest/terms.py reads that).
    """
    this_year = (today or date.today()).year
    years: set[int] = set()
    for cue in _GRAD_CUE.finditer(text or ""):
        window = text[cue.end(): cue.end() + 90]
        if cue.group(1).lower() == "graduate" and _GRAD_LEVEL.match(window):
            continue
        window = re.split(r"[.\n;]", window, maxsplit=1)[0]
        window = _TERM_PHRASE.sub(" ", window)
        for y in re.findall(_YEAR, window):
            if this_year - 1 <= int(y) <= this_year + 6:
                years.add(int(y))
    return sorted(years)


@dataclass
class Education:
    program: str = ""       # a PROGRAMS key or "" when not found
    degree: str = ""        # a DEGREE_LABELS key or ""
    grad_year: int | None = None


def _education_lines(text: str) -> list[str]:
    """Resume lines that look like they are about school plus the two lines after each."""
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    picked: set[int] = set()
    for i, line in enumerate(lines):
        if _SCHOOL_CUE.search(line):
            picked.update(j for j in (i, i + 1, i + 2) if j < len(lines))
    return [lines[i] for i in sorted(picked)]


def detect_education(text: str, today: date | None = None) -> Education:
    """Our best guess at the student's program, degree and grad year from their resume."""
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

    # 1. Things like "Expected graduation: April 2028" or "Class of 2027" or "Graduating 2027".
    # Not "Expected co-op term: Summer 2027" or "Undergraduate, available May 2027", which say
    # when they can work, not when they finish
    for m in re.finditer(
        r"(?i)\b(expected|anticipated|graduat\w*|class of|convocation)\b(\D{0,40}?)" + _YEAR,
        joined,
    ):
        if not _NOT_GRADUATION.search(m.group(2)):
            result.grad_year = int(m.group(3))
            return result
    # Lines about the co-op they want, like "Seeking a Summer 2027 co-op", never count below
    joined = _TERM_PHRASE.sub(" ", _WORK_TERM_LINE.sub(" ", joined))
    # 2. The end of a date range near school like "Sept 2023 to Apr 2028" or "2024 to Present".
    # A range inside one year is a work term, not a degree
    ends = [
        int(m.group(2))
        for m in re.finditer(_YEAR + r"\s*[-–—to]+\s*(?:[A-Za-z.]+\s*)?" + _YEAR, joined)
        if int(m.group(2)) > int(m.group(1))
    ]
    future = [y for y in ends if y >= this_year - 1]
    if future:
        result.grad_year = max(future)
        return result
    # 3. The latest year that makes sense near the school lines
    years = [int(y) for y in re.findall(_YEAR, joined) if this_year <= int(y) <= this_year + 6]
    if years:
        result.grad_year = max(years)
    return result
