"""
Job types ("Software & web", "Data & AI", ...) used by the job filters and resume matching.

Imported postings don't come with a category, so one is inferred from the job title with a
case-insensitive Postgres regex. The patterns are constants (never user input) and a title
can belong to more than one type ("Data Engineer" is both software and data).
Postgres regex: \\m = start of word, \\M = end of word.
"""

import re
from collections.abc import Sequence
from typing import Any, Literal

from sqlalchemy import or_

from app.models.posting import Posting

CategoryKey = Literal[
    "software", "data", "design", "product", "hardware", "it_security", "business",
    "sales_marketing", "customer",
]

# key -> (label shown in the UI, title pattern)
CATEGORIES: dict[str, tuple[str, str]] = {
    "software": (
        "Software & web",
        r"\m(software|developers?|d[eé]veloppeur\w*|programmers?|full[- ]?stack|front[- ]?end"
        r"|back[- ]?end|web|mobile|ios|android|devops|sre|site reliability|platform"
        r"|infrastructure|cloud|qa|quality assurance|tests?|testing|logiciels?|sdks?|sdet"
        r"|engineering manager|integration|product engineer|solutions engineer|architect\w*"
        r"|technical staff|tech(nical)? lead|reliability|systems engineer|privacy engineer)\M",
    ),
    "data": (
        "Data & AI",
        r"\m(data|analytics|analytical|machine learning|ml|ai|scientist|science"
        r"|computer vision|inference|business intelligence|bi|donn[eé]es|research|research engineer"
        r"|modell?ing|post-training|evals?)\M",
    ),
    "design": (
        "Design & UX",
        r"\m(design|designer|ux|ui|user experience|creative|art director|concepteur\w*"
        r"|user researcher|experience researcher)\M",
    ),
    "product": (
        "Product & project",
        r"\m(product manager|product owner|product management|program manager|project manager"
        r"|project coordinator|scrum master|chef de produit|chief of staff|director,? (of )?product"
        r"|gestionnaire de (produits|programme)|programs?)\M",
    ),
    "hardware": (
        "Hardware & engineering",
        r"\m(hardware|electrical|electronics?|embedded|firmware|mechanical|mechatronics"
        r"|robotics|manufacturing|civil|chemical|industrial|industriali[sz]ation|asic|fpga"
        r"|ing[eé]nierie|micrologiciel|mat[eé]riel|maintenance)\M",
    ),
    "it_security": (
        "IT & security",
        r"\m(security|cyber\w*|it|help ?desk|technical support|network|systems administrator"
        r"|sysadmin|fraud)\M",
    ),
    "business": (
        "Business & finance",
        r"\m(finance|financial|financier|accounting|accountant|business|operations|analyst"
        r"|analyste|investment|credit|risk|compliance|audit|tax|treasury|strategy"
        r"|strat[eé]gie|hr|rh|human resources|recruit\w*|talent|people|legal|counsel|juridiques?"
        r"|corporate development|executive assistant|facilities|supply chain|regulatory|grc"
        r"|wealth|advisor|consultant|implementation|controls|revenue|op[eé]rations)\M",
    ),
    "sales_marketing": (
        "Sales & marketing",
        r"\m(sales|account executive|account manager|business development|bdr|sdr|marketing"
        r"|growth|demand generation|content|copywriter|communications|brand|partnerships?"
        r"|social media|seo|partner\w*|account specialist|account development|retention|ventes"
        r"|commercial|comptes|paid media|public relations|relations publiques|enablement"
        r"|proposal)\M",
    ),
    "customer": (
        "Customer & support",
        r"\m(customer|client|support|success|experience associate|agent)\M",
    ),
}


def category_clause(key: str) -> Any:
    """SQL condition: the posting's title fits this job type."""
    return Posting.title.op("~*")(CATEGORIES[key][1])


def title_fits(key: str, title: str) -> bool:
    """The same check as category_clause, in Python (Postgres \\m and \\M become \\b)."""
    pattern = CATEGORIES[key][1].replace(r"\m", r"\b").replace(r"\M", r"\b")
    return re.search(pattern, title, re.IGNORECASE) is not None


def any_category(keys: Sequence[str]) -> Any:
    """SQL condition: the title fits at least one of the chosen job types."""
    return or_(*(category_clause(k) for k in keys))
