# [PROJECT_NAME] Constitution
<!-- CoopRadar's filled in version is .specify/memory/constitution.md. Start there instead of here. -->

## Core Principles

### [PRINCIPLE_1_NAME]
<!-- CoopRadar: I. Correctness First -->
[PRINCIPLE_1_DESCRIPTION]
<!-- CoopRadar: every endpoint has a schema and tests, every bug fix has a regression test, tests never touch the network -->

### [PRINCIPLE_2_NAME]
<!-- CoopRadar: II. Data Stays in the Database -->
[PRINCIPLE_2_DESCRIPTION]
<!-- CoopRadar: filter, sort and page in SQL, whitelisted columns, no user input in SQL text, do not load columns the page does not show -->

### [PRINCIPLE_3_NAME]
<!-- CoopRadar: III. Fast on Free Hosting -->
[PRINCIPLE_3_DESCRIPTION]
<!-- CoopRadar: 300 ms p95 on 10,000 postings, an index for every new sort or filter, the first page shows jobs while the server wakes up -->

### [PRINCIPLE_4_NAME]
<!-- CoopRadar: IV. Matching Works Without AI and V. Honest AI -->
[PRINCIPLE_4_DESCRIPTION]
<!-- CoopRadar: free SQL matching is the base, AI only adds; the AI cites, says when it does not know, and resume and posting text is tagged data -->

### [PRINCIPLE_5_NAME]
<!-- CoopRadar: VI. Visitors Own Their Keys and Their Data, VII. Respectful Job Collection, VIII. Accessible and Easy to Read, IX. Small Honest Changes, X. Keep It Simple -->
[PRINCIPLE_5_DESCRIPTION]
<!-- CoopRadar: keys never stored, resumes deletable, public sources only with robots.txt and terms respected, 375 px and keyboard friendly, conventional commits with no AI attribution, one process and one database -->

## [SECTION_2_NAME]
<!-- CoopRadar: Quality Gates -->

[SECTION_2_CONTENT]
<!-- CoopRadar: ruff, mypy strict, pytest, perf budget, migrations round trip, alembic check, eslint, tsc, vitest, build, hosted smoke test, Playwright -->

## [SECTION_3_NAME]
<!-- CoopRadar: Development Workflow -->

[SECTION_3_CONTENT]
<!-- CoopRadar: branch, the Spec Kit loop from specify to converge, the project skills, checks, pull request -->

## Governance
<!-- CoopRadar: the constitution wins over other practices, CLAUDE.md must agree with it, changes go through a PR with a version bump -->

[GOVERNANCE_RULES]
<!-- CoopRadar: MAJOR for a removed or changed principle, MINOR for a new one, PATCH for wording; every review checks new work against it -->

**Version**: [CONSTITUTION_VERSION] | **Ratified**: [RATIFICATION_DATE] | **Last Amended**: [LAST_AMENDED_DATE]
<!-- CoopRadar: Version 2.0.0 | Ratified 2026-10-09 | Last Amended 2026-11-17 -->
