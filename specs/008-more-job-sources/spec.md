# Feature Specification: Jobs From Every Field, From Public Sources

**Feature Branch**: `008-more-job-sources`

**Created**: 2026-10-11 (spec written 2026-11-17 from the finished code)

**Status**: Built

**Input**: User description: "Feature 003 only had a couple of feeds and some sample jobs. Bring in real jobs
from as many employers as possible, in every field that has co-ops, not only tech: nursing, trades, early
childhood education, business, hospitality. Use only public job board APIs and feeds, and make sure each job
lands in the right city and country."

<!--
  Written after the code. The work happened from 2026-10-11 to 2026-11-15 in commits e003529, 534ddcf,
  181098f, 0a5bad6, c3164f2, 7c6ddd5, 4e378cc and 1c021e3. See docs/agentic-workflow.md for the session notes.
-->

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Real jobs from the employers students want (Priority: P1)

A student opens the jobs page and sees thousands of real, open jobs from the banks, insurers, tech companies,
hospitals, utilities, retailers and universities they have heard of, each linking to the employer's own apply page.

**Why this priority**: Without real jobs the site is a demo. This is what makes it worth coming back to.

**Independent Test**: On a fresh local site, wait for the importer. The Admin page shows sources finishing with
jobs added and the jobs page shows thousands of open jobs with real apply links.

**Acceptance Scenarios**:

1. **Given** the list of employer career boards, **When** the importer runs, **Then** each board's open jobs in
   Canada (and US student roles) are added or updated
2. **Given** a job that left its board, **When** the next import runs, **Then** it is marked closed
3. **Given** the same job run twice, **When** the importer runs again, **Then** nothing is added twice
4. **Given** one board is down, **When** the importer runs, **Then** every other board still imports and that one
   pauses itself after 3 failures in a row

---

### User Story 2 - Jobs for every program that has co-ops (Priority: P2)

A practical nursing student, an early childhood education student and an electrician apprentice all find jobs
for their program, not only software roles.

**Why this priority**: Most co-op students are not in tech, and tech career boards barely cover them.

**Independent Test**: Filter by the Health job type, then by Trades, then by Hospitality. Each has jobs, including
Government of Canada Job Bank student and apprentice jobs.

**Acceptance Scenarios**:

1. **Given** Job Bank's public feeds, **When** the importer runs, **Then** student jobs, apprentice jobs and jobs
   for about 30 program searches are added
2. **Given** a Job Bank student job whose title does not say student, **When** it is saved, **Then** its title says
   "(student)" so the students only filter finds it
3. **Given** Job Bank feeds only show the last two days, **When** a job ages out of the feed, **Then** it stays open
   for 21 days instead of closing at once

---

### User Story 3 - Student lists and job sites with public APIs (Priority: P3)

Students who follow the big internship lists on GitHub find those roles on CoopRadar too, with their terms, plus
internships from The Muse, remote jobs open to Canada from Himalayas, and Workable's public job search.

**Why this priority**: Fills the gaps between employer boards. Big but lower quality than employers' own boards.

**Independent Test**: Admin shows the Simplify, GitHub list, The Muse, Himalayas and Workable sources with jobs
added.

**Acceptance Scenarios**:

1. **Given** a public list with terms, **When** it is imported, **Then** each role keeps its term, and roles for
   terms already over are dropped
2. **Given** a list entry nobody touched in 180 days, **When** it is imported, **Then** it is skipped
3. **Given** a job API with a rate limit, **When** it says slow down, **Then** what was read so far is kept

---

### User Story 4 - Jobs land in the right place (Priority: P4)

A student filtering by Ontario never sees a Gap store in Coral Ridge, Florida, or a Walmart in Ontario, Ohio.
A student filtering by Canada sees all of Walmart's 4,500 Canadian jobs, not 223.

**Why this priority**: Wrong locations make every filter untrustworthy.

**Independent Test**: Search Walmart with Canada picked. The count is in the thousands, and no listed job has a US
state.

**Acceptance Scenarios**:

1. **Given** a board that gives a country, **When** the job is read, **Then** that country wins over place names
2. **Given** "(CAN) ON FERGUS 01130 WM SUPERCENTER", **When** the place is read, **Then** it is Fergus, ON
3. **Given** a board with more Canadian jobs than its search will list at once, **When** it is imported, **Then**
   Canada is listed on its own, and each province on its own when needed

---

### Edge Cases

- A board that is 30 MB with descriptions included
- A careers page that moved from one hiring system to another
- "Vancouver, WA" and "London, ON"
- "Hybrid - New York" as a location
- A list repo whose name includes next summer's year
- A source that only gives a season ("Winter") with no year
- A job site whose terms forbid automated collection
- 1,700 sources on a free server that sleeps

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Jobs MUST only come from public job board APIs and feeds that allow it in their robots.txt and terms
- **FR-002**: The importer MUST read each employer's own careers board for the hiring systems most employers use
- **FR-003**: The importer MUST keep every job in Canada, and US jobs per the owner's setting (by default student
  and early career roles only)
- **FR-004**: The importer MUST read the city, province or state and country of each job and trust the country the
  board gives
- **FR-005**: The importer MUST bring in Government of Canada Job Bank student, apprentice and program jobs, waiting
  as long between calls as Job Bank asks
- **FR-006**: The importer MUST read the public student internship and new grad lists, keeping each role's term
- **FR-007**: Re running an import MUST update existing jobs and never add the same job twice
- **FR-008**: Jobs that leave their source MUST be closed, except sources with a rolling window, where they stay open
  for that long
- **FR-009**: Most boards publish no deadline, so the importer MUST set an estimated apply by date and mark it as a
  guess
- **FR-010**: The owner MUST be able to add an employer by adding one line, and to find new boards with a script
- **FR-011**: The importer MUST NOT collect from LinkedIn, Indeed, Glassdoor or Google Jobs
- **FR-012**: A source that fails 3 times in a row MUST pause itself, and the owner MUST be able to turn it back on

### Key Entities *(include if feature involves data)*

- **Source**: one career board or feed, with its hiring system, settings and health
- **Discovered board**: a board found by the discovery script and checked to have jobs in Canada or US student roles
- **Rolling window**: how long a job stays open after its feed stops showing it

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: About 1,700 sources seeded (185 hand picked employers, about 1,500 discovered boards, and the feeds)
- **SC-002**: About 30,000 open jobs on the live site (30,840 checked on 2026-11-15)
- **SC-003**: Only 31 of 1,671 seeded employers had no jobs, each with 1 to 6 on their own board (checked
  2026-11-15)
- **SC-004**: Walmart shows its Canadian jobs in the thousands, not 223
- **SC-005**: No import pass is stopped by one broken source

## Assumptions

- Employers' career boards are public on purpose so that job sites can list their openings
- Most employers outside tech use Workday
- The owner reruns the discovery script now and then. `start.py` does not
- A paid Adzuna plan is optional and off by default
