# Feature Specification: One Command Run and Free Hosting

**Feature Branch**: `006-one-command-free-hosting`

**Created**: 2026-10-11 (spec written 2026-11-17 from the finished code)

**Status**: Built

**Input**: User description: "Running CoopRadar needs Docker, Redis and a separate worker, which most students
and reviewers do not have. Make it one command on any laptop, host it for free, and make the first page show jobs
right away even when the free server is asleep."

<!--
  Written after the code. The work happened between 2026-10-11 and 2026-10-31 in commits df7b144, 4c3a8d1,
  7180239, 4e378cc and c355759. See docs/agentic-workflow.md for the session notes.
-->

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run it with one command (Priority: P1)

A classmate clones the repo on a Windows laptop with Python and Node installed and nothing else. They run one
command. It sets everything up, opens the browser, and real jobs start coming in a minute later. When they close
it and run it again it starts in seconds and their account is still there.

**Why this priority**: If people can not run it, nobody can review it, learn from it or help with it.

**Independent Test**: On a clean machine with Python 3.12 and Node, run `python start.py`. The site opens at
http://localhost:8000 and the Admin page shows imports running.

**Acceptance Scenarios**:

1. **Given** a fresh clone, **When** the visitor runs `python start.py`, **Then** it makes its own Python
   environment, installs packages, builds the site, starts a private database, sets up the tables and serves the
   site on one address
2. **Given** it ran before, **When** it runs again, **Then** it skips the steps that have not changed and is up in
   about 12 seconds
3. **Given** the window was closed hard, **When** it runs again, **Then** it waits for the database to repair
   itself and carries on
4. **Given** a developer, **When** they run `python start.py --dev`, **Then** the site reloads as they edit

---

### User Story 2 - Host it for free (Priority: P2)

The owner wants a public link for their resume and for students to use, without paying. They connect the repo to
Render and a free Neon database, optionally put Vercel in front, and the site keeps importing jobs on its own.

**Why this priority**: A live link is what makes it a real product, but the code has to run first.

**Independent Test**: Follow `docs/DEPLOY.md`. The live site lists jobs and the Admin page shows imports finishing.

**Acceptance Scenarios**:

1. **Given** a Render account and a Neon database, **When** the owner deploys the Blueprint, **Then** the site
   builds and starts with no other setup
2. **Given** the site is live, **When** six hours pass, **Then** each career board is imported again
3. **Given** the free server sleeps when idle, **When** the keep awake workflow is set up, **Then** it is pinged
   every 10 minutes from 7 am to 1 am Eastern so it stays up through the day
4. **Given** Vercel in front, **When** a visitor opens the site, **Then** pages come from Vercel's CDN and `/api`
   is passed through to Render

---

### User Story 3 - Jobs show right away, even when the server is asleep (Priority: P3)

A student opens the live link in the morning. The free server has been asleep and takes 30 seconds or more to wake
up. They see the first page of jobs and the first job's details in about a second anyway, with a small note saying
the rest is on its way.

**Why this priority**: A blank page for 30 seconds makes people leave. This makes free hosting feel fast.

**Independent Test**: Hold back the API by 8 seconds in the browser dev tools and open the jobs page. Jobs and
details show in about a second.

**Acceptance Scenarios**:

1. **Given** the server is asleep, **When** a visitor opens the jobs page, **Then** a saved first page shows at once
   from the CDN or the browser's own copy
2. **Given** the real list takes more than 4 seconds, **When** the visitor waits, **Then** a note says the server is
   waking up
3. **Given** the server wakes, **When** the real list arrives, **Then** it replaces the saved one with no jump

---

### Edge Cases

- Python or Node is missing or too old
- The repo lives in a OneDrive folder that locks database files while syncing
- Two copies of `start.py` run at once
- The free database counts every byte read, so careless queries use up the month
- The free server sleeps halfway through an import of 1,700 boards
- A restart on the host would reload 1,700 boards row by row before opening its port
- The Vercel rewrite loses its `/api/:path*` ending and every API call gets the home page back
- The snapshot must never hold anything specific to one visitor, since the CDN shares it with everyone

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The site MUST run on a laptop with one command and only Python and Node installed. No Docker, no Redis,
  no separate worker
- **FR-002**: The command MUST set up its own database outside any synced folder and stop it cleanly on exit
- **FR-003**: Repeat runs MUST skip installing, building and seeding when nothing they depend on changed
- **FR-004**: Login sessions and rate limit counters MUST work without Redis, and MAY use Redis when it is set
- **FR-005**: Imports and other background work MUST run inside the one server process, a few at a time, and one
  failing job MUST NOT stop the others
- **FR-006**: The site MUST deploy to a free host from the repo with the database address as the only required
  setting
- **FR-007**: On a host, the server MUST open its port before doing slow startup work
- **FR-008**: The importer MUST make progress even if the server sleeps partway, by doing sources that never ran
  and then the oldest first
- **FR-009**: Imported jobs that closed or passed their deadline over 30 days ago MUST be deleted unless someone
  saved them
- **FR-010**: The first page of jobs, the filter choices and the first job's details MUST be available as one reply
  that is the same for everyone and that the CDN may cache. Nothing else may be cached by the CDN
- **FR-011**: The browser MUST keep its last copy of that first page and show it while the real one loads
- **FR-012**: Job lists MUST NOT read job descriptions or other columns the list does not show

### Key Entities *(include if feature involves data)*

- **Key value row**: a session or a counter with an optional expiry time
- **Background job**: a named task like importing one source or making one embedding
- **Snapshot**: the first page as nobody has filtered it, the filter choices and the first job's details
- **Seed fingerprint**: a hash of the seed files and settings so the seed can skip itself

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A clean Windows machine goes from clone to jobs on screen with one command (checked 2026-10-11: 791
  real jobs imported in the background)
- **SC-002**: A restart takes about 12 seconds
- **SC-003**: Hosting costs nothing: Render free, Neon free, Vercel free, GitHub Actions free
- **SC-004**: With the API held back 8 seconds, the jobs and the first job's details show in about a second
  (checked 2026-10-29)
- **SC-005**: The keep awake pings use about 560 of the 750 free Render hours a month

## Assumptions

- Everyone running it has Python 3.12 and Node 20 or newer
- Free plans keep roughly their current limits (Render sleeps after about 15 minutes idle, Neon counts data
  transfer, 0.5 GB storage)
- The owner is fine with the site being slow to answer the very first API call after a long idle
- Vercel is optional. Render alone works
