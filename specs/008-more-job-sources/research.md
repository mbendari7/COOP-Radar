# Research: Jobs From Every Field, From Public Sources

**Feature**: 008-more-job-sources
**Date**: 2026-10-11 to 2026-11-15 (written up 2026-11-17)

Every source below was checked for a public API or feed, its robots.txt and its terms before it was added.
`guides/owner-handbook/` and the README sources table keep the current list.

## Sources and why they are allowed

| Source | Type | What it reads | Why it is OK |
|---|---|---|---|
| Greenhouse, Lever, Ashby | `greenhouse`, `lever`, `ashby` | Each employer's public job board API | Built for job sites to list openings |
| SmartRecruiters | `smartrecruiters` | Public postings API | Same |
| Workday | `workday` | The JSON behind `myworkdayjobs.com` pages (`/wday/cxs/<tenant>/<site>/jobs`) | robots.txt allows it. It is what the public page loads |
| Recruitee, BambooHR, Rippling | `recruitee`, `bamboohr`, `rippling` | `<board>.recruitee.com/api/offers/`, `<board>.bamboohr.com/careers/list`, `api.rippling.com/platform/api/ats/v1/board/<board>/jobs` | Public board endpoints |
| Oracle Cloud | `oracle` | `/hcmRestApi/resources/latest/recruitingCEJobRequisitions` | The same public endpoint the career pages use |
| Workable | `workable` | jobs.workable.com public search | robots.txt allows it |
| Simplify and vanshb03 lists | `simplify` | `.github/scripts/listings.json` on GitHub | Public repos made to be shared |
| negarprh list | `github_list` | README table on GitHub | Public repo |
| The Muse | `themuse` | Public jobs API, internship level | Public API, 500 calls an hour |
| Himalayas | `himalayas` | Public jobs API, remote jobs open to Canada | Public API |
| Job Bank | `jobbank` | Government of Canada Atom feeds | Public feeds. robots.txt asks for 5 seconds between calls |
| Adzuna | `adzuna` | Search API | Only with the owner's paid keys |

## Turned down

LinkedIn, Indeed, Glassdoor and Google Jobs. Their terms forbid automated collection and Google Jobs has no public
API. The constitution says public APIs and feeds only, even if it means fewer jobs.

## Finding employers

**Decision**: A hand picked list in `seed/job_boards.py` (185 employers) plus `seed/discover_boards.py`, which the
owner runs now and then. It reads Common Crawl's free URL index for careers pages on each hiring system, asks each
board's own API once, and keeps boards with jobs in Canada or US student roles. `--lists` also takes boards from
the apply links on the GitHub student lists. It adds to `discovered_boards.json` (about 1,500 boards) instead of
replacing it.

**Why**: Nobody can hand pick 1,700 employers. The public lists and Common Crawl were used as leads only. Jobs
always come from the employer's own board.

## Workday's 2,000 limit

**Found 2026-11-15**: Workday never lists more than 2,000 jobs for one search. Walmart has about 19,000, 4,525 in
Canada, and only 223 showed. **Fix**: when the site's own Canada filter counts more Canadian jobs than the list
showed, list Canada on its own, and each province on its own when Canada is over 2,000.

## Country wins

**Found 2026-11-15**: Gap stores named "05139 ON Coral Ridge" and Walmart in Ontario, Ohio were saved as Canadian.
**Fix**: Workday, Lever and SmartRecruiters give a country and it always wins over place names. Store codes like
"(CAN) ON FERGUS 01130 WM SUPERCENTER" read as Fergus, ON.

## Big boards

**Decision**: Greenhouse and SmartRecruiters list jobs without descriptions and fetch descriptions only for kept
jobs, six at a time. Some Greenhouse boards are 30 MB with descriptions.

## Job Bank

**Decision**: The student filter (`fjsf=1`), the apprentice filter (`fjap=1`) and about 30 program searches
(`DEFAULT_QUERIES`: nursing, personal support, early childhood education, teaching, social work, trades, cooking,
engineering technology, labs, accounting, marketing and more), 5 seconds apart, each tried twice. Titles get
"(student)" or "(apprentice)" when they do not say. The feeds only show two days, so the adapter has a
`rolling_window` of 21 days.

## Deadlines

**Decision**: Most boards publish none, so the runner sets an estimated apply by date 45 days out, flags it in
`low_confidence_fields`, and pushes it forward on each run while the job is still listed.

## Keeping the database small

**Decision**: Jobs closed or past their deadline for over 30 days are deleted unless someone saved them. Neon's
free plan is 0.5 GB.
