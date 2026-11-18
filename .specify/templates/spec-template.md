# Feature Specification: [FEATURE NAME]

**Feature Branch**: `[###-feature-name]`

**Created**: [DATE]

**Status**: Draft

**Input**: User description: "$ARGUMENTS"

<!--
  How to fill this in for CoopRadar

  This file is the WHAT and the WHY. Write it so a co-op coordinator or a student could read it.
  No FastAPI, React, Postgres, table names or endpoints here. Those go in plan.md.

  Who uses CoopRadar
  - Visitors: university and college students looking for co-ops, internships and early career jobs in Canada
    (and student roles in the US). Most never make an account. Dropping in a resume makes a temporary one.
  - Students who keep their account to track applications for a whole season.
  - The owner: the person running the live site on free hosting, who uses the Admin page.

  Look at specs/001 to specs/008 for finished examples.
-->

## User Scenarios & Testing *(mandatory)*

<!--
  Put the user stories in order of importance. Each one has to work and be worth something on its own, so if
  only Story 1 ships the feature still helps someone.

  P1 is the one that matters most. Think of each story as something you could build, test, ship and show to a
  student by itself.

  Good CoopRadar stories are about a real moment in a co-op search, for example
  - "A second year nursing student finds placements near Hamilton for the summer term"
  - "A student with no AI key still gets a ranked list of jobs that fit their resume"
  - "The owner sees which career boards failed in the last import"
-->

### User Story 1 - [Brief Title] (Priority: P1)

[Describe this user journey in plain language. Who is it, what are they trying to do, what do they see]

**Why this priority**: [Why this one comes first and what a student gets from it]

**Independent Test**: [How to check it on its own, for example "Open the jobs page, pick Winter 2027 and Ontario,
and only jobs for that term and province show up, with the count updated"]

**Acceptance Scenarios**:

1. **Given** [where things start], **When** [what the user does], **Then** [what they see]
2. **Given** [where things start], **When** [what the user does], **Then** [what they see]

---

### User Story 2 - [Brief Title] (Priority: P2)

[Describe this user journey in plain language]

**Why this priority**: [Why it comes after Story 1]

**Independent Test**: [How to check it on its own]

**Acceptance Scenarios**:

1. **Given** [where things start], **When** [what the user does], **Then** [what they see]

---

### User Story 3 - [Brief Title] (Priority: P3)

[Describe this user journey in plain language]

**Why this priority**: [Why it comes after Story 2]

**Independent Test**: [How to check it on its own]

**Acceptance Scenarios**:

1. **Given** [where things start], **When** [what the user does], **Then** [what they see]

---

[Add more user stories if you need them, each with a priority]

### Edge Cases

<!--
  Replace these with the real edge cases for this feature. Ones that come up again and again in CoopRadar:
  - A job that does not say its term, length, deadline or city
  - A job in Vancouver, WA or London, ON that looks like the wrong country
  - A resume that is a scanned image with no text, or a file over 5 MB
  - No AI key, a wrong AI key, or an AI that runs out of credit halfway
  - The free server is asleep and takes 30 seconds to wake up
  - A career board that is down, slow, or changed its format
  - A phone 375 px wide
-->

- What happens when [boundary condition]?
- How does the site handle [error case]?

## Requirements *(mandatory)*

<!--
  Each requirement is one thing the site MUST do that you can test. Keep them about behaviour, not code.
  If something really is not decided, mark it [NEEDS CLARIFICATION: the question] and /speckit-clarify
  will ask about it. Keep it to 3 or fewer.

  Things that are already decided for every feature (from the constitution), so you do not need to ask:
  - Filtering, sorting and paging happen on the server
  - Matching works without any AI key
  - Visitor AI keys are never stored
  - Jobs only come from public APIs, feeds, uploads or manual entry
  - Pages work on a phone and with a keyboard
-->

### Functional Requirements

- **FR-001**: The site MUST [specific thing, for example "let a student filter jobs by work term"]
- **FR-002**: The site MUST [specific thing, for example "show how many jobs match each filter choice"]
- **FR-003**: Students MUST be able to [key action, for example "save a job and change its status"]
- **FR-004**: The site MUST [data rule, for example "keep a job that left its source for 21 days"]
- **FR-005**: The site MUST [behaviour, for example "explain why a job fits in plain words"]

*Example of marking something that is not decided yet:*

- **FR-006**: Students MUST be able to filter by [NEEDS CLARIFICATION: which terms, only the next three or any year?]

### Key Entities *(include if feature involves data)*

<!--
  The things this feature deals with, in plain words. The CoopRadar ones that already exist:
  Posting (a job), Source (a career board or feed), Import run, Saved posting (tracker card), Status change,
  User (real or temporary), Resume (text only, plus what the student is looking for), Match, Skill.
-->

- **[Entity 1]**: [What it is and what you need to know about it]
- **[Entity 2]**: [What it is and how it relates to other things]

## Success Criteria *(mandatory)*

<!--
  How you will know it worked. Numbers you can measure, no tech words.
  CoopRadar style examples: "A student can narrow 13,000 jobs to the 5 that fit in under 30 seconds",
  "The first page shows jobs within 2 seconds even when the server is asleep",
  "At least 9 out of 10 imported jobs show the right city and country".
-->

### Measurable Outcomes

- **SC-001**: [Measurable result, for example "A student finds a job for their program and term in under a minute"]
- **SC-002**: [Measurable result, for example "Search answers in under 300 ms with 10,000 jobs"]
- **SC-003**: [User result, for example "9 out of 10 testers upload a resume and see matches without help"]
- **SC-004**: [Site result, for example "No import pass is stopped by one broken source"]

## Assumptions

<!--
  The defaults you picked when the description did not say. CoopRadar ones that are usually true:
  - Visitors do not need an account. A temporary one is made when they need one
  - Students are in Canada, or looking for student roles in the US
  - The site runs on free hosting that sleeps, with a free database that has data transfer limits
  - The owner may not have set any AI keys
-->

- [Assumption about who uses it, for example "Most visitors are on a laptop, about a third on phones"]
- [Assumption about what is out of scope, for example "Email alerts are not part of this feature"]
- [Assumption about data, for example "Most career boards do not publish a deadline"]
- [Dependency, for example "Uses the existing resume upload from feature 004"]
