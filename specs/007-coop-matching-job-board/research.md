# Research: Co-op Matching and a Job Board Layout

**Feature**: 007-coop-matching-job-board
**Date**: 2026-10-12 to 2026-10-25 (written up 2026-11-17)

## 1. Reading programs and grad years

**Decision**: Rules, not AI. Programs come only from sentences with a degree cue ("degree in", "pursuing a",
"Bachelor of", "enrolled in"). Grad years come from the 90 characters after "graduating" or "class of", whole words
only, with work term phrases cut out first.

**Why**: It has to run on 30,000 jobs on every import for free. Rules are fast and testable.

**Bugs this caught**: "Employee Stock Purchase Program" read as a program. "graduat" inside "undergraduate" saved
2027 from "Undergraduate students for the Summer 2027 term" as a grad year. "Expected co-op term: Summer 2027" on a
resume read as the grad year. Each has a test now.

## 2. Reading the work term and length

**Decision**: `ingest/terms.py` handles "Summer 2027", "Fall '27", "S27", "(January 2027)" in a title, "May to
August", "Work Term: Winter", and lengths like "4 month co-op", "12 week internship", "one year contract". It runs
on import and again on every re import.

**Why**: Imported jobs had all been given a made up 4 months. Migration 0011 made `duration_months` nullable so
unknown stays unknown, and 0013 kept real lengths (6 stays 6).

## 3. Strict or lenient

**Decision**: Lenient. Program and grad year raise or lower a job, they never hide it. Other grad years take 10
points off and add a note.

**Why**: The first version hid jobs for other grad years and students saw too few matches. Most jobs do not say,
and some that say one year take others.

## 4. The score

**Decision**: In SQL, capped at 100: skills 65, student title 15, program 10, grad year 5, term or season 5, length
5, typed keywords plus 20, other grad years minus 10. Senior titles count skills at half.

**Why**: The first weights bunched scores at 100. These spread them out. `fit_notes()` turns the same parts into
the "why it fits" lines so the reason and the score always agree.

## 5. Jobs that do not say their term

**Decision**: `include_unstated`, on by default in the site, keeps them in after the ones that do. A season only
matches terms not yet under way.

**Why**: Most employers never write the term, so picking Winter used to hide almost everything.

## 6. Job types

**Decision**: 13 job types as title patterns in `services/categories.py`, tuned against the live titles, run as
Postgres `~*`. Each program lists the job types that suit it.

## 7. Layout

**Decision**: A job board: one search row, a filter sidebar always in view on laptops, a list beside a details
panel from 1280 px, `?job=` in the address, no popups (the filter drawer and sign in popup were removed in
2026-10-25 after a tester said it felt cluttered).

**Design**: Picked with the Impeccable skill and written into `DESIGN.md` and `PRODUCT.md`. Plain sentence case
labels, no em dashes or emoji in UI text.

## 8. Not added

LinkedIn, Indeed, Glassdoor and Google Jobs. Their terms forbid automated collection (see feature 008).
