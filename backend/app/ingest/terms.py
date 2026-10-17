"""
The co-op term and its length, read from a job's title and description. Just regex, no AI.

Term. Gives back "Summer 2027", or "Summer" when the job names a season with no year we can
pin down. Canadian co-op terms follow the school year
  Winter   January to April
  Summer   May to August
  Fall     September to December
Spring stays its own season since it means May to August at some schools and January to May
at most US ones.
A job can say it in many ways, so we look for
  a season and a year           "Summer 2027", "2027 Summer", "Fall '26", "été 2027"
  a start month                 "starting January 2027", "May to August 2027"
  a season next to a role word  "Summer Intern", "Work Term: Fall", "winter co-op"
A season with no year gets the next one after today, so "Summer intern" in October means
next summer.

Length. Gives back the length in whole months as the job states it, 2 to 24, or None when it
does not say. "6 month internship" gives 6 and "12 week internship" gives 3. A month range like
"May to August" counts too. Filters group lengths into the usual co-op ones with LENGTH_BUCKETS.
"""

import re
from datetime import date

SEASONS = ("winter", "spring", "summer", "fall")
_START_MONTH = {"winter": 1, "spring": 3, "summer": 5, "fall": 9}

_SEASON_WORDS = {
    "winter": "winter", "hiver": "winter",
    "summer": "summer", "été": "summer", "ete": "summer",
    "spring": "spring", "printemps": "spring",
    "fall": "fall", "autumn": "fall", "automne": "fall",
}
_SEASON = r"(winter|summer|spring|fall|autumn|hiver|été|ete|printemps|automne)"
_YEAR = r"(20[2-4]\d)"
_SHORT_YEAR = r"'(\d{2})\b"

_MONTHS = {
    "january": 1, "jan": 1, "janvier": 1, "february": 2, "feb": 2, "février": 2,
    "march": 3, "mar": 3, "mars": 3, "april": 4, "apr": 4, "avril": 4, "may": 5, "mai": 5,
    "june": 6, "jun": 6, "juin": 6, "july": 7, "jul": 7, "juillet": 7,
    "august": 8, "aug": 8, "août": 8, "september": 9, "sept": 9, "sep": 9, "septembre": 9,
    "october": 10, "oct": 10, "octobre": 10, "november": 11, "nov": 11, "novembre": 11,
    "december": 12, "dec": 12, "décembre": 12,
}
_MONTH = r"(" + "|".join(sorted(_MONTHS, key=len, reverse=True)) + r")\.?"

# Words that show a season is about the job's term and not something else like "Spring Boot"
_ROLE_CUE = (
    r"(intern\w*|co-?op\w*|stage|stagiaire|students?|terms?|work term|placement|semester"
    r"|session|program|cohort|analyst|associate|position|role|hire|employment|job)"
)

_SEASON_YEAR = re.compile(
    rf"(?i)\b{_SEASON}\s*(?:term|session|semester|/\s*term \d)?\s*[,(]?\s*{_YEAR}\b"
)
_YEAR_SEASON = re.compile(rf"(?i)\b{_YEAR}\s+{_SEASON}\b")
_SEASON_SHORT = re.compile(rf"(?i)\b{_SEASON}\s*{_SHORT_YEAR}")
_SEASON_CODE = re.compile(r"\b([WSF])(2[5-9]|3\d)\b")  # Waterloo style codes like S27 or W28
_START = re.compile(
    rf"(?i)\b(?:start(?:ing|s)?(?: date)?|begin(?:ning|s)?|commenc\w+|available|from)"
    rf"(?:\s+(?:in|on|date|of|:))*\s*:?\s*{_MONTH}\s*(?:\d{{1,2}}(?:st|nd|rd|th)?,?\s*)?{_YEAR}?"
)
_RANGE = re.compile(
    rf"(?i)\b{_MONTH}\s*{_YEAR}?\s*(?:-|–|—|to|through|until|thru)\s*{_MONTH}\s*{_YEAR}?"
)
# A bare month and year. Only trusted in a title like "Co-op Student (January 2027)", since a
# description can name a month for a deadline or an info session
_MONTH_YEAR = re.compile(rf"(?i)\b{_MONTH}\s*,?\s*{_YEAR}\b")
_SEASON_ROLE = re.compile(rf"(?i)\b{_SEASON}\s+{_ROLE_CUE}\b")
_ROLE_SEASON = re.compile(rf"(?i)\b(?:work term|term|session|semester)\s*:?\s*{_SEASON}\b")

_NUMBER_WORDS = {
    "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "fourteen": 14, "sixteen": 16, "eighteen": 18,
}
_NUMBER = r"(\d{1,2}|" + "|".join(_NUMBER_WORDS) + r")"
_MONTHS_LONG = re.compile(
    rf"(?i)\b{_NUMBER}\s*(?:(?:-|to|or|/|–)\s*{_NUMBER}\s*)?[- ]?\s*(?:months?|mois)\b"
)
_WEEKS_LONG = re.compile(rf"(?i)\b{_NUMBER}\s*(?:(?:-|to|–)\s*{_NUMBER}\s*)?[- ]?\s*weeks?\b")
_YEAR_LONG = re.compile(r"(?i)\b(?:one|1)[- ]year\b|\byear[- ]long\b|\bfull[- ]year\b")
# Near a length these show it is the job's own length
_LENGTH_CUE = re.compile(
    r"(?i)(intern\w*|co-?op|stage|term|placement|contract|assignment|position|program"
    r"|duration|length|role|temporary|fixed|student|mois)"
)
# And these show it is about something else, like years of experience or a probation period
_LENGTH_NOT = re.compile(
    r"(?i)(experience|graduat\w*|probation|ago|within|past|last|every|data|old|prior|minimum"
    r"|least|after|before|notice|leave|vesting|salary|benefit|eligible)"
)


def _number(token: str | None) -> int | None:
    if not token:
        return None
    token = token.lower()
    return int(token) if token.isdigit() else _NUMBER_WORDS.get(token)


def _season_of_month(month: int) -> str:
    if month <= 4:
        return "winter"
    return "summer" if month <= 8 else "fall"


def _next_year_for(season: str, today: date) -> int:
    """The year of the next time this season starts, counting one already under way for a month."""
    start = date(today.year, _START_MONTH[season], 1)
    return today.year if (today - start).days < 31 else today.year + 1


def _label(season: str, year: int | None) -> str:
    return f"{season.capitalize()} {year}" if year else season.capitalize()


def _sane_year(year: int, today: date) -> bool:
    return today.year - 1 <= year <= today.year + 3


def term_in_text(title: str, text: str = "", today: date | None = None) -> str | None:
    """
    The term a job is for, like "Summer 2027", or None when it does not say.
    The title wins over the description, since descriptions often list every term a company
    hires for.
    """
    today = today or date.today()
    for part, is_title in ((title or "", True), ((text or "")[:6000], False)):
        found = _term_in(part, today, is_title)
        if found:
            return found
    return None


def _term_in(text: str, today: date, is_title: bool = False) -> str | None:
    if not text:
        return None
    stale = False  # it names a term, but one long gone, so we will not guess another
    for rx, season_group, year_group in ((_SEASON_YEAR, 1, 2), (_YEAR_SEASON, 2, 1)):
        for m in rx.finditer(text):
            year = int(m.group(year_group))
            if _sane_year(year, today):
                return _label(_SEASON_WORDS[m.group(season_group).lower()], year)
            stale = True
    if stale:
        return None
    for m in _SEASON_SHORT.finditer(text):
        year = 2000 + int(m.group(2))
        if _sane_year(year, today):
            return _label(_SEASON_WORDS[m.group(1).lower()], year)
    code = _SEASON_CODE.search(text)
    if code:
        season = {"W": "winter", "S": "summer", "F": "fall"}[code.group(1)]
        year = 2000 + int(code.group(2))
        if _sane_year(year, today):
            return _label(season, year)
    for rx in (_START, _RANGE, *((_MONTH_YEAR,) if is_title else ())):
        month = rx.search(text)
        if month:
            season = _season_of_month(_MONTHS[month.group(1).lower().rstrip(".")])
            stated = int(month.group(2)) if month.group(2) else None
            if stated and not _sane_year(stated, today):
                continue
            return _label(season, stated or _next_year_for(season, today))
    cue = _ROLE_SEASON.search(text) or _SEASON_ROLE.search(text)
    if cue:
        season = _SEASON_WORDS[cue.group(1).lower()]
        return _label(season, _next_year_for(season, today))
    return None


MIN_MONTHS, MAX_MONTHS = 2, 24
# The usual co-op lengths and the real lengths each one covers. The length filter, the counts
# next to it and resume preferences all use these, so a 6 month job shows under "about 8"
LENGTH_BUCKETS: dict[int, tuple[int, int]] = {4: (2, 5), 8: (6, 9), 12: (10, 14), 16: (15, 24)}


def whole_months(months: float) -> int | None:
    """A job length in whole months, or None when it is too short or long to be a work term."""
    rounded = round(months)
    return rounded if MIN_MONTHS <= rounded <= MAX_MONTHS else None


def length_bucket(months: int | None) -> int | None:
    """The usual co-op length a real length falls under. 6 gives 8. None when unknown."""
    if months is None:
        return None
    return next((key for key, (low, high) in LENGTH_BUCKETS.items() if low <= months <= high), None)


def _cued(text: str, start: int, end: int) -> bool:
    before = text[max(0, start - 50): start]
    after = text[end: end + 50]
    if _LENGTH_NOT.search(before[-25:]) or _LENGTH_NOT.search(after[:25]):
        return False
    return bool(_LENGTH_CUE.search(before) or _LENGTH_CUE.search(after))


def duration_in_text(title: str, text: str = "") -> int | None:
    """The length in whole months a job states, like 4 or 6, or None when it does not say."""
    for part in (title or "", (text or "")[:8000]):
        found = _duration_in(part)
        if found:
            return found
    return None


def _duration_in(text: str) -> int | None:
    if not text:
        return None
    for m in _MONTHS_LONG.finditer(text):
        low = _number(m.group(1))
        if low and _cued(text, m.start(), m.end()):
            rounded = whole_months(low)
            if rounded:
                return rounded
    for m in _WEEKS_LONG.finditer(text):
        low = _number(m.group(1))
        if low and 8 <= low <= 52 and _cued(text, m.start(), m.end()):
            rounded = whole_months(low / 4.345)
            if rounded:
                return rounded
    whole = _YEAR_LONG.search(text)
    if whole and _cued(text, whole.start(), whole.end()):
        return 12
    for m in _RANGE.finditer(text):
        start = _MONTHS[m.group(1).lower().rstrip(".")]
        end = _MONTHS[m.group(3).lower().rstrip(".")]
        start_year = int(m.group(2)) if m.group(2) else None
        end_year = int(m.group(4)) if m.group(4) else None
        span = end - start + 1
        if start_year and end_year:
            span += 12 * (end_year - start_year)
        elif span <= 0:
            span += 12
        rounded = whole_months(span)
        if rounded:
            return rounded
    return None


def term_start_date(term: str | None) -> date | None:
    """"Summer 2027" gives May 1 2027, like term_start in the database. None without a year."""
    season = season_of(term)
    year = (term or "")[-4:]
    if not season or not year.isdigit():
        return None
    return date(int(year), _START_MONTH[season], 1)


def season_of(term: str | None) -> str | None:
    """"Summer 2027" gives "summer". None when the term names no season."""
    word = (term or "").split(" ", 1)[0].lower()
    return _SEASON_WORDS.get(word) if word else None
