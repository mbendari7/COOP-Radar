"""Reading the co-op term and its length from job text (app/ingest/terms.py). Real wording from live boards."""

from datetime import date

import pytest

from app.ingest.terms import duration_in_text, length_bucket, season_of, term_in_text, whole_months

TODAY = date(2026, 10, 13)


@pytest.mark.parametrize(
    ("title", "text", "expected"),
    [
        ("Co-op Student (Fall 2027)", "", "Fall 2027"),
        ("2027 Summer Analyst Program", "", "Summer 2027"),
        ("Software Intern - Summer '27", "", "Summer 2027"),
        ("Stagiaire été 2027", "", "Summer 2027"),
        ("Co-op S27", "", "Summer 2027"),
        ("DevOps Engineer - New Grad (January 2027)", "", "Winter 2027"),
        ("Spring 2027 Intern", "", "Spring 2027"),
        # A season next to a role word with no year means the next one
        ("Summer Intern, Finance", "", "Summer 2027"),
        ("Fall Co-op, Assurance", "", "Fall 2027"),
        ("Data Analyst", "Work Term: Winter", "Winter 2027"),
        # From the description
        ("Data Analyst Co-op", "This is a 4 month term starting May 2027.", "Summer 2027"),
        ("Engineering Co-op", "Work term: January to August 2027", "Winter 2027"),
        # The title wins over a description that lists every term
        ("Fall 2027 Co-op", "We hire for Winter 2027, Summer 2027 and Fall 2027.", "Fall 2027"),
        # Nothing about a term, and Spring the Java framework is not a season
        ("Software Developer Coop", "Build services with Spring Boot.", None),
        ("Senior Accountant", "Apply by January 2027.", None),
    ],
)
def test_term_in_text(title: str, text: str, expected: str | None) -> None:
    assert term_in_text(title, text, TODAY) == expected


def test_years_far_away_are_ignored() -> None:
    assert term_in_text("Summer 2019 Intern", "", TODAY) is None


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("This is a 4-month co-op term.", 4),
        ("an eight month internship", 8),
        ("We offer an 8 to 12 month internship.", 8),
        ("12 week summer internship", 3),
        ("16-month internship (May 2027 - Aug 2028)", 16),
        ("This is a one-year contract position.", 12),
        ("Work term: January to August 2027", 8),
        # The real length, never rounded to a co-op length (regression: 6 showed as 8)
        ("6 month co-op placement", 6),
        ("a 10-week summer internship", 2),
        # Months that are not about the job's length
        ("Requires 3 months of experience with Excel.", None),
        ("Graduated within the last 12 months of the start date.", None),
        ("A great team.", None),
    ],
)
def test_duration_in_text(text: str, expected: int | None) -> None:
    assert duration_in_text("", text) == expected


def test_duration_in_title() -> None:
    assert duration_in_text("Finance Intern (12 months)") == 12


@pytest.mark.parametrize(
    ("months", "expected"), [(2.8, 3), (6, 6), (16, 16), (1, None), (30, None)]
)
def test_whole_months(months: float, expected: int | None) -> None:
    assert whole_months(months) == expected


@pytest.mark.parametrize(
    ("months", "bucket"),
    [(3, 4), (4, 4), (6, 8), (8, 8), (12, 12), (16, 16), (20, 16), (None, None)],
)
def test_length_bucket(months: int | None, bucket: int | None) -> None:
    assert length_bucket(months) == bucket


def test_season_of() -> None:
    assert season_of("Summer 2027") == "summer"
    assert season_of("Fall") == "fall"
    assert season_of("Open") is None
    assert season_of("") is None
