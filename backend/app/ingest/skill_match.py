"""
Find skills from our list in free text like job descriptions and resumes.

Plain whole word matching works for most skills, but a few skill names are also everyday
words and need a closer look
  C and R  must be a capital letter on its own, so "C++" or "C-suite" or "R&D" do not count
  Go       has to be capitalised and not used as a verb, like "Go to market" or starting a sentence
  Spring   means the Java framework and not the season, so not "Spring 2027" or "spring term"
"""

import re

_EDGE_BEFORE = r"(?<![\w+#./-])"
_EDGE_AFTER = r"(?![\w+#])"

_SINGLE_LETTER = re.compile(r"(?<![\w+#./&'’-])([CR])(?![\w+#&'’]|\s*\+\+|-\w)")
_GO = re.compile(
    r"(?<![\w+#./-])Go(?![\w+#'’-])(?!\s+(?:to|ahead|beyond|further|live|above|for)\b)"
)
_SPRING_SEASON = re.compile(
    r"\bspring\s*(?:'?\d{2,4}|term|semester|break|session|intake|co-?op|intern|and|or|/)",
    re.IGNORECASE,
)


def _go_mentioned(text: str) -> bool:
    for m in _GO.finditer(text):
        before = text[: m.start()].rstrip(" \t")
        # "Go" at the start of a sentence or line is nearly always the verb
        if before and before[-1] not in ".!?:\n•-*":
            return True
    return False


def _spring_mentioned(text: str, lowered: str) -> bool:
    if "java" not in lowered or "Spring" not in text:
        return False
    framework_uses = len(re.findall(r"\bSpring\b", text))
    season_uses = len(_SPRING_SEASON.findall(text))
    return framework_uses > season_uses


def mentions(skill: str, text: str, lowered: str | None = None) -> bool:
    """True if `skill`, a name or alias, shows up in `text` as a whole word."""
    lowered = lowered if lowered is not None else text.lower()
    if skill in ("C", "R"):
        return any(m.group(1) == skill for m in _SINGLE_LETTER.finditer(text))
    if skill == "Go":
        return _go_mentioned(text)
    if skill == "Spring":
        return _spring_mentioned(text, lowered)
    pattern = _EDGE_BEFORE + re.escape(skill.lower()) + _EDGE_AFTER
    return re.search(pattern, lowered) is not None


def match_skills(taxonomy: list[tuple[str, list[str]]], text: str) -> list[str]:
    """Names of the skills from our list that show up in `text` by name or any alias."""
    lowered = text.lower()
    return [
        name
        for name, aliases in taxonomy
        if any(mentions(c, text, lowered) for c in [name, *(aliases or [])])
    ]
