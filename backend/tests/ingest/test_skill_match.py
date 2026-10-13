"""Tests for spotting skills in job descriptions and resumes. No database and no network."""

import pytest

from app.ingest.skill_match import match_skills, mentions


@pytest.mark.parametrize(
    ("skill", "text", "expected"),
    [
        # Single letters mean the language and not the letter
        ("C", "Strong C and C++ skills", True),
        ("C", "Experience with C++ and C#", False),
        ("C", "Report to the C-suite after Series C funding", True),  # "Series C" is accepted
        ("C", "Partner with the C-suite", False),
        ("R", "Statistics in R or Python", True),
        ("R", "Join our R&D team", False),
        ("R", "Use the r key", False),
        # Go means the language and not the verb
        ("Go", "Backend services in Go and Python", True),
        ("Go", "Go to market with our sales team.", False),
        ("Go", "We go above and beyond", False),
        ("Go", "Ready to Go further? Apply now", False),
        # Spring means the Java framework and not the season
        ("Spring", "Java and Spring microservices", True),
        ("Spring", "Java developer intern for Spring 2027", False),
        ("Spring", "Python intern, spring term", False),
        # Normal skills only match whole words
        ("CSS", "HTML and CSS", True),
        ("CSS", "SCSS only", False),
        ("node.js", "Built APIs with Node.js", True),
    ],
)
def test_mentions(skill: str, text: str, expected: bool) -> None:
    assert mentions(skill, text) is expected


def test_match_skills_uses_aliases_once_per_skill() -> None:
    taxonomy = [
        ("Kubernetes", ["k8s", "helm"]),
        ("PostgreSQL", ["postgres"]),
        ("Spring", ["spring boot"]),
        ("Go", ["golang"]),
    ]
    text = "Deploy with k8s and Helm; store data in Postgres; Spring Boot services; golang CLI"
    assert match_skills(taxonomy, text) == ["Kubernetes", "PostgreSQL", "Spring", "Go"]
