"""
Job types like "Software & web" and "Data & AI" for the job filters and resume matching.

Imported jobs do not come with a category so we work one out from the title with a
Postgres regex that ignores case. The patterns are fixed and never come from users, and
a title can fit more than one type, like "Data Engineer" being software and data.
In Postgres regex \\m means start of word and \\M means end of word.
"""

import re
from collections.abc import Sequence
from typing import Any, Literal

from sqlalchemy import or_

from app.models.posting import Posting

CategoryKey = Literal[
    "software", "data", "design", "product", "hardware", "it_security", "business",
    "sales_marketing", "customer", "health", "public", "trades", "hospitality",
]

# key maps to the label people see and the title pattern
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
        "Engineering & hardware",
        r"\m(hardware|electrical|electronics?|embedded|firmware|mechanical|mechatronics"
        r"|robotics|manufacturing|civil|chemical|industrial|industriali[sz]ation|asic|fpga"
        r"|ing[eé]nierie|micrologiciel|mat[eé]riel|maintenance|structural|geotechnical"
        r"|environmental engineer\w*|process engineer\w*|project engineer\w*|field engineer\w*"
        r"|engineer in training|eit|construction|estimat\w+|drafting|cad|surveying|mining"
        r"|metallurg\w*|petroleum|reservoir|pipeline|energy|power systems?|utilities|aerospace"
        r"|avionics|quality engineer\w*|reliability engineer\w*|engineering (co-?op|intern\w*"
        r"|student))\M",
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
        r"|wealth|advisor|consultant|implementation|controls|revenue|op[eé]rations|paralegal"
        r"|law clerk|legal assistant|bookkeep\w*|payroll|purchasing|buyer)\M",
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
        r"\m(customer|client|support|success|experience associate|agent|retail|store"
        r"|sales associate"
        r"|teller|banking advisor|service representative|front desk|reception\w*)\M",
    ),
    "health": (
        "Health & science",
        r"\m(nurs\w+|clinical|clinic|patient|health|healthcare|medical|pharmac\w+|lab|laboratory"
        r"|research assistant|biolog\w*|chemist\w*|biochem\w*|microbiolog\w*|scientist"
        r"|regulatory affairs"
        r"|quality control|qc|qa associate|biotech\w*|kinesiolog\w*|physiotherap\w*|dietitian"
        r"|therap\w+|epidemiolog\w*|public health|veterinar\w*|environmental|sant[eé]"
        r"|infirmi\w+|dental|dentist\w*|hygienist|paramedic\w*|personal support worker|psw"
        r"|care aide|health care aide|caregiver|phlebotom\w*|x-ray|radiolog\w*|sonograph\w*"
        r"|medical imaging|optician|audiolog\w*|massage therapist|pharmacist)\M",
    ),
    "public": (
        "Government, education & nonprofit",
        r"\m(policy|government|public service|municipal|city of|federal|provincial|teach\w*"
        r"|tutor|education\w*|instructor|librar\w+|museum|curat\w+|archiv\w+|social work\w*"
        r"|community|youth|counsell?or|nonprofit|non-profit|charity|program assistant"
        r"|student affairs|academic|research associate|urban planning|planner|elections?"
        r"|educators?|early childhood|child ?care|daycare|educational assistant|recreation"
        r"|social service worker|case worker|outreach)\M",
    ),
    "trades": (
        "Trades & technicians",
        r"\m(technician|technologist|electrician|millwright|mechanic|welder|plumb\w+|carpent\w+"
        r"|apprentice|operator|machinist|hvac|tradesperson|trades|labou?rer|installer"
        r"|lineman|power line|instrumentation|warehouse|driver|logistics associate"
        r"|technicien\w*)\M",
    ),
    "hospitality": (
        "Hospitality, food & tourism",
        r"\m(hospitality|hotel|resort|tourism|travel|cook|cooks|chef|sous-chef|culinary|kitchen"
        r"|baker|pastry|food service|food and beverage|restaurant|catering|banquet|bartender"
        r"|barista|housekeep\w*|room attendant|night auditor|guest services|concierge"
        r"|event planner|events? coordinator|event staff|cuisinier|h[oô]tellerie)\M",
    ),
}


def category_clause(key: str) -> Any:
    """SQL check that the job title fits this job type."""
    return Posting.title.op("~*")(CATEGORIES[key][1])


def title_fits(key: str, title: str) -> bool:
    """Same check as category_clause but in Python, where Postgres \\m and \\M become \\b."""
    pattern = CATEGORIES[key][1].replace(r"\m", r"\b").replace(r"\M", r"\b")
    return re.search(pattern, title, re.IGNORECASE) is not None


def any_category(keys: Sequence[str]) -> Any:
    """SQL check that the title fits at least one of the picked job types."""
    return or_(*(category_clause(k) for k in keys))
