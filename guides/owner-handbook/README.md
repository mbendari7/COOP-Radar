# Owner's handbook

For the person who runs CoopRadar: how to keep the live site healthy on free plans, how to make the common
changes, and what to check before you push. Short steps, links to the deep docs when you need more.

> Using the site: [Using CoopRadar](../using-coopradar/README.md) · Explaining the build:
> [How it works](../how-it-works/README.md) · Every module: [Project guide](../../docs/PROJECT_GUIDE.md) ·
> Hosting in detail: [Deploy](../../docs/DEPLOY.md)

- [1. What runs where](#1-what-runs-where)
- [2. A quick weekly check](#2-a-quick-weekly-check)
- [3. Make yourself admin](#3-make-yourself-admin)
- [4. Living with free plans](#4-living-with-free-plans)
- [5. Common changes](#5-common-changes)
- [6. Before you commit and push](#6-before-you-commit-and-push)
- [7. When something breaks](#7-when-something-breaks)
- [8. Refresh the README screenshots](#8-refresh-the-readme-screenshots)

---

## 1. What runs where

| Piece | Where | What it does | Where to look when it misbehaves |
|---|---|---|---|
| Website + API | **Render** web service `coopradar` ([coopradar-u7in.onrender.com](https://coopradar-u7in.onrender.com)) | Serves the pages and `/api`, imports jobs in the background every 6 hours while awake | Render dashboard: **Logs**, **Events** (deploys) |
| Database | **Neon** Postgres (free) | Jobs, users, resumes, sessions | Neon dashboard: **Monitoring**, **Usage**, **SQL Editor** |
| Fast front | **Vercel** project | Serves the pages from a CDN, caches the first page of jobs, forwards `/api` to Render | Vercel dashboard: **Deployments**, **Logs** |
| Keep awake | GitHub Actions *Keep the site awake* (`refresh-jobs.yml`) | Pings the site every 10 minutes from 7 am to 1 am Eastern | GitHub repo: **Actions** tab |
| Checks | GitHub Actions *CI* (`ci.yml`) | Every check on every push, then Playwright against a real copy of the site | GitHub repo: **Actions** tab, the badge at the top of the README |

A push to `main` redeploys Render and Vercel by themselves. Nothing else needs doing.

---

## 2. A quick weekly check

Five minutes, once a week:

1. **Open the site in a private window.** Jobs show at once, clicking one shows its details, and *Match my
   resume* gives matches for a real resume.
2. **Admin page** (`/admin/sources`, once you are admin). Sources marked *Paused itself* failed 3 times in a row.
   Open its history to see why. A company that moved to another hiring system is normal; remove it or fix its board
   name (see [Add or fix an employer](#add-or-fix-an-employer)), then click **Turn back on**.
3. **Neon usage.** Storage under 0.5 GB, and compute hours and data transfer comfortably under the monthly limits.
   See [Living with free plans](#4-living-with-free-plans) if not.
4. **GitHub Actions.** *CI* is green on the last push, and *Keep the site awake* runs are green through the day.
5. **Render events.** The last deploy says *Live*.

---

## 3. Make yourself admin

The Admin page shows every import source, its history, and buttons to run one now or turn it on or off.

1. On the live site, click **Sign in** and make a normal account (or keep a temporary one with **Keep my
   account**).
2. In Neon, open **SQL Editor** and run, with your email:
   ```sql
   UPDATE users SET is_admin = TRUE WHERE email = 'you@example.com';
   ```
3. Refresh the site. **Admin** appears in the top bar.

On your own computer, do the same in any Postgres client connected to the local database, or with
`psql "$DATABASE_URL"` on another host.

---

## 4. Living with free plans

| Limit | What happens | What to do |
|---|---|---|
| Render sleeps after about 15 idle minutes | First visit takes up to a minute to wake it; the importer only runs while awake | The keep awake workflow covers 7 am to 1 am Eastern. With the Vercel front visitors see jobs at once anyway. For a demo at night, open the site a minute early |
| Render: 750 free hours a month | The site stops until next month | The workflow uses about 560. Don't widen its hours in `refresh-jobs.yml` |
| Neon: 0.5 GB storage | Imports start failing | Keep `INGEST_US_JOBS=students` (never `all`). Closed jobs are deleted after 30 days on their own |
| Neon: monthly compute hours and 5 GB data transfer | The database stops answering until next month | On Render, **Environment**, set `INGEST_INTERVAL_HOURS=12` so imports run half as often. Job lists already skip descriptions to save transfer |
| Render free memory (512 MB) | The server restarts in the middle of an import | Don't raise the 3 imports at a time in `app/jobs.py`. Big boards already fetch descriptions only for jobs they keep |

The always on fix for all of these is Render's paid instance (a few dollars a month) and Neon's paid plan.

---

## 5. Common changes

Each of these is a small change and a test. The [Project guide](../../docs/PROJECT_GUIDE.md#10-recipes-common-changes-step-by-step)
has the longer recipes.

### Add or fix an employer
1. Find the careers page. The board name is the last part of its URL: `boards.greenhouse.io/`**`shopify`**,
   `jobs.lever.co/`**`wealthsimple`**, `jobs.ashbyhq.com/`**`cohere`**. For Workday,
   `td.wd3.myworkdayjobs.com/TD_Bank_Careers` becomes the board `td.wd3/TD_Bank_Careers`.
2. Add a line to `JOB_BOARDS` in `backend/seed/job_boards.py`: `("Company name", "greenhouse", "board")`, or
   `("TD", "workday", "td.wd3/TD_Bank_Careers")`.
3. Push. On start the seed sees the file changed and adds the source; the importer picks it up within the hour.

### Find many more employers at once
`backend/seed/discover_boards.py` searches Common Crawl's free URL index for career boards and keeps the ones with
jobs in Canada or US student roles, adding them to `discovered_boards.json`.
```bash
cd backend && python -m seed.discover_boards            # 10 to 20 minutes
cd backend && python -m seed.discover_boards --lists    # only boards linked from the GitHub student lists
```
It uses a lot of memory and network. Run it on a computer with memory to spare, with other programs closed, and
review the change to the JSON file before you commit it.

### Add a Job Bank search for a program
Add words to `DEFAULT_QUERIES` in `backend/app/ingest/jobbank.py` (each one is a Job Bank search, `|` between
them). Try the search on [jobbank.gc.ca](https://www.jobbank.gc.ca) first to check it brings real jobs.

### Add a job type or a program
- Job types and their title patterns: `backend/app/services/categories.py`
- Programs of study and how they are read from resumes and job descriptions: `backend/app/services/education.py`

Add a test with a real title or sentence in `backend/tests/` next to the existing ones.

### Change how matches are scored
`backend/app/services/resume.py`: the `_W_*` weights and `fit_notes()`. Tests pin the numbers, so update those too
and say why in the commit.

### Change what the pages look like
Colours and fonts in `frontend/tailwind.config.ts`, shared buttons and fields in `frontend/src/index.css`, and the
reasons in [`DESIGN.md`](../../DESIGN.md). Keep the voice from `PRODUCT.md`: short sentences, plain words, no dashes.

### Change the database
Change the model in `backend/app/models/`, then run the `/db-migration` skill in Claude Code. It writes the
migration, checks it goes up and down, and runs `alembic check`.

### Turn on owner AI keys (optional, costs money)
On Render, **Environment**: `ANTHROPIC_API_KEY` lets visitors without a key use AI on your account (capped by
`AI_DAILY_LIMIT` per person per day). `OPENAI_API_KEY` turns on smart search and similar jobs. Set a monthly spending
limit in the provider's console first.

---

## 6. Before you commit and push

Run the checks that CI runs. On your own computer, the easy way is:

```bash
# Frontend
cd frontend && npm run lint && npm run typecheck && npm test && npm run build

# Backend (needs a throwaway Postgres with pgvector in DATABASE_URL)
cd backend && ruff check . && mypy app && pytest -q -m "not perf" && alembic check
```

Then start the site and click through what you changed (`python start.py`). If you changed the pages, run the
browser tests too: `cd frontend && npm run test:e2e`.

House rules (also in [`CLAUDE.md`](../../CLAUDE.md)):
- Small commits with a conventional message: `feat:`, `fix:`, `test:`, `docs:`, `chore:`.
- No AI co-author lines in commits or pull requests.
- Every bug fix gets a test that would have caught it.
- Secrets only in environment variables, never in a file you commit. Keep `.env.example` current.
- Note what the AI did in `docs/agentic-workflow.md` (`/log-agentic-work` in Claude Code).

If CI fails after a push, open the failed job in the **Actions** tab; the last red step says which check and why.

---

## 7. When something breaks

| What you see | Likely cause | Fix |
|---|---|---|
| The jobs page says the jobs didn't load | Render is still waking, or `vercel.json` lost the `/api/:path*` ending | Wait a minute and retry. Then open `https://<vercel-site>/api/postings?page_size=10`: it must be JSON. If it is a web page, fix the `destination` in `vercel.json` |
| Jobs look days old | The site slept and the importer didn't run | Check *Keep the site awake* runs and that the `SITE_URL` variable is set. Click **Run now** on a source in Admin to test |
| Render deploy failed | A build step broke | Render **Events**, open the deploy, read the last lines of the log. Usually a package or a type error CI also caught |
| Render keeps restarting | Out of memory, or the database is unreachable | Render **Logs**. If it says the database refused, check Neon's usage page and that `DATABASE_URL` is right |
| Neon says a limit was reached | Too much import work for the free plan | Set `INGEST_INTERVAL_HOURS=12`. It resets at the start of the month |
| Many sources *Paused itself* at once | A network problem on Render, or a hiring system changed its API | Look at one run's error in Admin. If every source of one type fails, the adapter in `backend/app/ingest/` needs a fix and a new recorded test response |
| Nobody can sign in on Vercel | Requests aren't going through the `/api` rewrite | Same `vercel.json` check as above |
| Want to start the data over | | Neon: make a new branch or database, put its URL in `DATABASE_URL` on Render, redeploy. Jobs re-import by themselves; accounts don't carry over |

More symptoms and fixes: [Project guide troubleshooting](../../docs/PROJECT_GUIDE.md#13-troubleshooting).

---

## 8. Refresh the README screenshots

The README pictures live in `docs/images/` (`jobs.png`, `matches.png`, `fit.png`, `tracker.png`, `phone.png`).
To take new ones:

1. Start the site without kicking off a full import:
   `BACKGROUND_JOBS=false python start.py --no-browser --port 8123`
   (your local database needs jobs from an earlier run).
2. Laptop shots at 1440 by 900: the jobs page with the first job picked; *Match my resume* after uploading a sample
   resume, scrolled to the matches; a matched job's page scrolled to *Make your resume fit this job*; the tracker
   board from **Try the demo**.
3. A phone shot at 390 by 844.
4. Save them over the old files with the same names and check the README on GitHub after you push.

Playwright (already installed for the browser tests) or the browser's own device toolbar both work for this.
