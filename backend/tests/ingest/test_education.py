"""Tests for reading programs and grad years from jobs and resumes."""

from datetime import date

import pytest

from app.services.categories import title_fits
from app.services.education import (
    detect_education,
    fields_in_posting,
    grad_years_in_posting,
)

TODAY = date(2026, 10, 12)


# Jobs

def test_fields_come_from_degree_sentences_only() -> None:
    text = (
        "Our engineering team ships fast and our business is growing.\n"
        "• Currently pursuing a Bachelor's degree in Computer Science, Engineering or a related field\n"
        "• Strong communication skills\n"
        "Join our Employee Stock Purchase Program."
    )
    assert fields_in_posting(text) == ["cs", "engineering"]


def test_fields_for_business_programs() -> None:
    text = "Currently enrolled in a post-secondary program in Business, Finance or Marketing."
    assert fields_in_posting(text) == ["business", "finance", "marketing"]


def test_no_degree_sentence_means_no_fields() -> None:
    assert fields_in_posting("We build data platforms in Python for finance teams.") == []


@pytest.mark.parametrize(
    ("text", "years"),
    [
        ("with the expectation of graduating in December 2027 or spring/summer 2028", [2027, 2028]),
        ("Open to students graduating between Dec 2026 and June 2027.", [2026, 2027]),
        ("Class of 2028 students only", [2028]),
        ("Founded in 2015, we have 300 people. Graduates welcome.", []),
        ("Must be returning to school after the work term.", []),
        ("graduation date in 2045", []),  # too far away to be real
        # The work term is not a grad year (regression: these all gave 2027 before)
        ("Undergraduate students enrolled for the Summer 2027 term.", []),
        ("Open to undergraduate and graduate students for a Fall 2027 co-op.", []),
        ("Graduate students starting May 2027 are welcome.", []),
        ("Students graduating in 2028, for our Summer 2027 internship.", [2028]),
        ("Must be graduating in 2029 and available to start January 2027.", [2029]),
    ],
)
def test_grad_years(text: str, years: list[int]) -> None:
    assert grad_years_in_posting(text, today=TODAY) == years


# Resumes

def test_detects_program_degree_and_expected_graduation() -> None:
    resume = (
        "Alex Student\nalex@example.com\n"
        "Skills: Python, SQL, React\n"
        "EDUCATION\n"
        "University of Waterloo\n"
        "Bachelor of Applied Science, Mechatronics Engineering (Co-op)\n"
        "Expected graduation: April 2029\n"
        "EXPERIENCE\nSoftware Developer Intern, Acme, 2025\n"
    )
    found = detect_education(resume, today=TODAY)
    assert (found.program, found.degree, found.grad_year) == ("mechanical_engineering", "bachelors", 2029)


def test_graduation_from_a_date_range() -> None:
    resume = "Toronto Metropolitan University\nBCom, Business Management\nSept 2024 - Apr 2028\n"
    found = detect_education(resume, today=TODAY)
    assert (found.program, found.degree, found.grad_year) == ("business", "bachelors", 2028)


def test_computer_science_honours() -> None:
    resume = "McGill University, Honours Computer Science, 2023 – 2027\nGPA 3.8"
    found = detect_education(resume, today=TODAY)
    assert (found.program, found.grad_year) == ("computer_science", 2027)


def test_co_op_availability_is_not_the_grad_year() -> None:
    # Regression: the wanted work term was read as the graduation year
    resume = (
        "University of Waterloo, Computer Science (Co-op)\n"
        "Expected co-op term: Summer 2027\n"
        "Seeking an 8 month co-op starting May 2027\n"
        "Sept 2024 - Apr 2029\n"
    )
    found = detect_education(resume, today=TODAY)
    assert found.grad_year == 2029


def test_undergraduate_line_is_not_graduation() -> None:
    resume = "Undergraduate Research Assistant, McGill University, Summer 2026\nBSc Biology, 2024 - 2028"
    assert detect_education(resume, today=TODAY).grad_year == 2028


def test_nothing_found_is_blank() -> None:
    found = detect_education("Jane Doe\nSkills: Python, Django\nBuilt APIs.", today=TODAY)
    assert (found.program, found.degree, found.grad_year) == ("", "", None)


# Programs and job types beyond tech, like the Job Bank jobs bring in

@pytest.mark.parametrize(
    "line,program",
    [
        ("Diploma, Hospitality and Tourism Management, Humber College, 2027", "hospitality"),
        ("Paralegal diploma, Seneca College, expected 2027", "law_justice"),
        ("Practical Nursing diploma, Conestoga College, 2027", "health_sciences"),
        ("Bachelor of Commerce, Business Management, 2028", "business"),
    ],
)
def test_college_programs_are_read_from_the_resume(line: str, program: str) -> None:
    assert detect_education(f"Education\n{line}", today=TODAY).program == program


@pytest.mark.parametrize(
    "title,key,fits",
    [
        ("Cook (student)", "hospitality", True),
        ("Hotel night auditor", "hospitality", True),
        ("SQL Server Developer", "hospitality", False),
        ("Early childhood educator (ECE)", "public", True),
        ("ECE Co-op", "public", False),
        ("Personal support worker - home support", "health", True),
        ("Dental assistant", "health", True),
        ("Paralegal", "business", True),
    ],
)
def test_job_types_cover_job_bank_titles(title: str, key: str, fits: bool) -> None:
    assert title_fits(key, title) is fits
