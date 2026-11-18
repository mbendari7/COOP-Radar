# Feature Specification: Co-op Matching and a Job Board Layout

**Feature Branch**: `007-coop-matching-job-board`

**Created**: 2026-10-12 (spec written 2026-11-17 from the finished code)

**Status**: Built

**Input**: User description: "Matching only looks at skills, but a co-op student cares about their program,
their graduation year and which work term a job is for. Read those from the resume and from each job, rank by
them, say why a job fits, and make the jobs page feel like a real job board with every filter a student needs."

<!--
  Written after the code. The work happened from 2026-10-12 to 2026-10-25 in commits 534ddcf, 4c3a8d1,
  7e807f7, 0a5bad6 and 7c6ddd5. See docs/agentic-workflow.md for the session notes.
-->

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Jobs ranked for my program, grad year and term (Priority: P1)

A third year mechanical engineering student graduating in 2028 drops in their resume. The site reads "Bachelor of
Engineering, Mechanical, expected 2028" from it, fills in program, degree and grad year, and asks what they are
looking for: Summer 2027, 4 or 8 months, Ontario. Their matches put mechanical and manufacturing co-ops for that
term first, and each one says why it fits, like "For mechanical engineering students", "Summer 2027 term" and "You
have SolidWorks and MATLAB".

**Why this priority**: A great skill match for the wrong program or the wrong term is useless to a co-op student.

**Independent Test**: Upload a resume that names a program and a grad year. The detected values show on the page,
the top matches suit the program, and each has fit notes.

**Acceptance Scenarios**:

1. **Given** a resume that names a program, degree and graduation year, **When** it is uploaded, **Then** those are
   filled in and the student can change them
2. **Given** a wanted term and length, **When** matches are ranked, **Then** jobs for that term and length rank
   higher
3. **Given** a job that names other graduation years, **When** matches are ranked, **Then** it still shows, lower,
   with a "check before you apply" note
4. **Given** "Undergraduate students for the Summer 2027 term" in a job, **When** it is read, **Then** 2027 is a work
   term, not a grad year

---

### User Story 2 - Filter jobs like on a real job board (Priority: P2)

A student browsing without a resume searches "data" and filters by work term (Winter, Summer, Fall), length, level
(students only, entry level, all), province and city, work mode, job type, program, grad year, date posted and
company. Every choice shows how many jobs it has. The list sits beside a details panel, and the whole state is in
the address so they can send it to a friend.

**Why this priority**: Most visitors browse first. Good filters are how they find the five jobs that matter.

**Independent Test**: On the jobs page pick Summer, Ontario, Software and Students only. The count and every list
change, the address has every choice, and reloading keeps them.

**Acceptance Scenarios**:

1. **Given** the jobs page, **When** a student picks any mix of filters, **Then** only jobs that fit all of them show
   and each choice shows its count
2. **Given** many jobs do not say their term, **When** a term is picked, **Then** jobs that do not say stay in after
   the ones that do, unless the student turns that off
3. **Given** a laptop screen, **When** a job is clicked, **Then** its details show beside the list without leaving
   the page
4. **Given** a phone, **When** the student taps Filters, **Then** the same filters open in place above the results,
   with no popup

---

### User Story 3 - Make my resume fit one job (Priority: P3)

The student opens a job they like and clicks Make your resume fit. With no AI key they see a short list: checks
(is your grad year on it, does it say French if the job asks), edits in order, and the job's words split into ones
the resume already has and ones worth adding if true.

**Why this priority**: Helps after a match is found. Useful, but the match has to come first.

**Independent Test**: Open a job with a resume uploaded and click Make your resume fit. The checks and word lists
appear with no AI key.

**Acceptance Scenarios**:

1. **Given** a resume and a job, **When** the student opens Make your resume fit, **Then** they see checks, edits
   and words found or worth adding, for free
2. **Given** no resume, **When** they open it, **Then** it asks them to upload one first

---

### User Story 4 - See what is new since last time (Priority: P4)

A student comes back a week later. A bar says "18 new since your last visit" and a Newly added sort shows them
first. They can also copy an RSS link for their search to get new jobs in a reader.

**Why this priority**: Brings people back. Not needed for a first visit.

**Independent Test**: Visit, wait for an import to add jobs, visit again. The new count shows and Newly added puts
them first.

**Acceptance Scenarios**:

1. **Given** a returning browser, **When** new jobs were added since its last visit, **Then** a count shows with a
   way to see just those
2. **Given** any search, **When** the student copies the feed link, **Then** a feed reader shows the newest jobs for
   that search

---

### Edge Cases

- "Employee Stock Purchase Program" is not a degree program
- "Hybrid - New York" has no city called Hybrid
- "graduat" inside "undergraduate" is not a graduation year, and "graduate students" is a level of study
- "Expected co-op term: Summer 2027" on a resume is a work term, not the grad year
- Lengths like 6 months must stay 6, not be rounded
- A term already under way should not show as starting soonest
- Job titles in French
- Scores bunching up at 100 so the order means nothing

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The site MUST read program, degree and graduation year from a resume when it can, and let the student
  change them
- **FR-002**: The site MUST read the programs of study and graduation years a job asks for, only from sentences
  that talk about a degree or graduating
- **FR-003**: The site MUST read the work term (season and year) and length from each job's title and text
- **FR-004**: Students MUST be able to say what they are looking for: job types, keywords, province or city, work
  modes, level, program, degree, grad year, term, lengths and countries
- **FR-005**: Matching MUST rank by skills first, then student title, program, grad year, term, length and
  keywords, and MUST NOT hide jobs just because program or grad year do not match
- **FR-006**: Each match MUST have plain "why it fits" notes
- **FR-007**: The jobs list MUST filter by work term, length, level, province, city, country, work mode, job type,
  program, grad year, date posted, company and skills, with counts for each choice
- **FR-008**: Jobs that do not say their term or length MUST stay in by default when those filters are used, after
  the ones that do
- **FR-009**: The jobs list MUST sort by newest posted, deadline, company, title, term start, length and newly added
- **FR-010**: Every filter, sort and the selected job MUST live in the page address
- **FR-011**: The site MUST give a free, no AI way to see how to make a resume fit one job
- **FR-012**: The site MUST show how many jobs are new since this browser's last visit and offer an RSS feed for any
  search
- **FR-013**: The site MUST have no popups. Sign in is its own page and returns to where the student was

### Key Entities *(include if feature involves data)*

- **Job preferences**: what the student is looking for, saved with their resume
- **Program**: a field of study with the job types that suit it (for example mechanical engineering suits hardware
  and trades)
- **Job type**: a group of titles (software, data, design, product, hardware, IT and security, business, sales and
  marketing, customer, health, public, trades, hospitality)
- **Work term**: a season and year, with a start date worked out from it

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a resume that names a program, at least 8 of the top 10 matches suit that program
- **SC-002**: The jobs list with every filter on still answers under 300 ms at p95 on 10,000 jobs (measured 47 ms)
- **SC-003**: Turning on "also show jobs that don't say their term" took Winter co-ops for computer engineering
  from 155 to 297 (measured 2026-10-17)
- **SC-004**: Up to 60 matches come back per resume, spread across the score range instead of bunched at 100

## Assumptions

- Most employers never write the term or a deadline, so the site has to be lenient
- Students mostly want Canada. Some also do a US term
- Program names differ by school, so programs are broad groups
- The look follows `DESIGN.md` (written during this work with the Impeccable design skill)
