# Quickstart: One Command Run and Free Hosting

## 1. One command

```bash
python start.py
```

First run: makes `backend/.venv`, installs packages, builds the site, starts Postgres in `~/.coopradar`, migrates,
seeds and opens http://localhost:8000. About a minute later the importer starts. Watch the terminal.

Check:

1. Stop it with Ctrl+C. The terminal says the database stopped
2. Run it again. It should be up in about 12 seconds
3. Close the terminal window hard, then run it again. It waits for Postgres to repair itself and carries on
4. `python start.py --dev` serves http://localhost:5173 and reloads when you edit a file

## 2. Hosted mode on your own machine

```bash
python start.py --hosted
```

The port opens before the seed finishes. Restart it: the seed says it skipped itself because nothing changed.

## 3. Instant first page

1. Open the jobs page once so the browser saves a snapshot
2. In the browser dev tools, throttle or block `/api/postings` for 8 seconds
3. Reload. Jobs and the first job's details show in about a second, and after 4 seconds a note says the server is
   waking up

Check the snapshot headers:

```bash
curl -sI http://localhost:8000/api/postings/snapshot | grep -i cache-control
```

## 4. Deploy for free

Follow `docs/DEPLOY.md`. In short:

1. Make a free Neon project and copy its connection string
2. On Render, New Blueprint from this repo, paste the string as `DATABASE_URL`
3. Optional: import the repo on Vercel and set the Render address in `vercel.json`
4. In GitHub, add a repository variable `SITE_URL` with the live address so `refresh-jobs.yml` runs

## Tests for this feature

```bash
cd backend
pytest -q tests/api/test_store_and_jobs.py tests/api/test_hosting.py
pytest -q -m perf -s
```
