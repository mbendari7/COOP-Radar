# Getting Started: Run and Use CoopRadar

This is the hands-on guide. It covers how to install what you need, start the app, and use every feature.
Follow it top to bottom the first time (about 15 minutes).

There are two ways to run CoopRadar on your computer:

| Mode | Command | Open | Use it when |
|---|---|---|---|
| **Website mode** | `docker compose -f docker-compose.prod.yml up --build` | http://localhost:8080 | You want to *use* or *show* the app. One container, sets itself up, exactly like the hosted site. |
| **Developer mode** | `docker compose up --build` | http://localhost:5173 | You're *changing the code*. Hot reload, separate containers, API docs at :8000/docs. |

To put it on the internet instead, see **[DEPLOY.md](DEPLOY.md)**.

> Want to understand *how* it works instead? See **[HOW_IT_WORKS.md](HOW_IT_WORKS.md)**.

---

## Part 1: One-time setup

### 1.1 Install Docker Desktop
CoopRadar runs as 5 containers, so Docker is the only thing you must install.

1. Download **Docker Desktop**: https://www.docker.com/products/docker-desktop/
2. Windows: during install keep **"Use WSL 2"** checked. If it asks you to install/update WSL, follow the prompt
   (or run `wsl --install` in an admin PowerShell) and reboot.
3. Open Docker Desktop and wait until it says **Engine running**.
4. Check it works. In PowerShell or a terminal:
   ```powershell
   docker --version
   docker compose version
   ```

### 1.2 Get the code
If you already have the repo in GitHub Desktop, just make sure you're on **`main`** and click **Fetch origin**, then
**Pull**. Otherwise:
```powershell
git clone https://github.com/mbendari7/COOP-Radar.git
cd COOP-Radar
```

### 1.3 Create your `.env` file
`.env` holds your settings and secrets. It is never committed.
```powershell
cp .env.example .env
```
Open `.env` in VS Code and set:

| Setting | What to put | Required? |
|---|---|---|
| `POSTGRES_PASSWORD` | any password (e.g. `coopradar-dev-123`). Also update the same password inside `DATABASE_URL` | yes |
| `ANTHROPIC_API_KEY` | leave empty | no (only if you want visitors without a key to use *your* account) |
| `OPENAI_API_KEY` | leave empty | no (only to turn on smart search and similar postings) |

Leave everything else at its default. **You don't need any AI keys to run CoopRadar.** For the AI features, each
person adds their own key inside the website (see 3.5 and [AI_KEYS.md](AI_KEYS.md)).

---

## Part 2: Start the app

### 2.0 Fastest: website mode (recommended to start)
```powershell
docker compose -f docker-compose.prod.yml up --build
```
When the logs show `Starting web server on port 8000`, open **http://localhost:8080** and click **Try the demo**.
The database tables, sample postings, and background worker all set themselves up, so **skip 2.1–2.4** and go
straight to Part 3. Stop it with `Ctrl+C` (or `docker compose -f docker-compose.prod.yml down`).

The rest of Part 2 is **developer mode**, for when you're changing code.

### 2.1 Start everything (developer mode)
From the repo folder:
```powershell
docker compose up --build
```
The first run downloads images and installs dependencies (a few minutes). It's ready when you see lines like:
```
api-1     | INFO:     Application startup complete.
web-1     |   ➜  Local:   http://localhost:5173/
```
Leave this terminal running; it shows live logs. The `api` container creates/updates the database tables
automatically on start.

### 2.2 Load sample data (first time only)
Open a **second** terminal in the repo folder:
```powershell
docker compose exec api python -m seed
```
You should see `Seeded 55 postings…`, `Seeded 106 skills.`, `Seeded 2 ingest sources.` It's safe to run again.

### 2.3 Optional: turn on smart search (needs `OPENAI_API_KEY` in `.env`)
```powershell
docker compose exec api python -m app.ingest.embed
```
This creates an "embedding" (a meaning-vector) for every posting, which powers smart search and similar postings
(resume matching works without it). It prints `Embedded 55 postings.` Skip this step if you didn't set the key.

### 2.4 Open it
- **The app:** http://localhost:5173
- **The API's interactive docs:** http://localhost:8000/docs

---

## Part 3: Use every feature

### 3.0 Try the demo (no sign-up)
Click **Try the demo** (top-right, or in the blue welcome box). You're instantly logged into a private demo account
with six applications already in the tracker and a sample resume with 20 matches. A yellow banner reminds you it's
a demo, and it's deleted after 24 hours. Everything in 3.1–3.8 works inside the demo too.

### 3.1 Browse and search (no account needed)
1. The home page lists open postings, newest first. Expired ones are hidden; tick **Show expired** to see them.
2. Type in the search box, e.g. `python` or `"data engineer" -senior`. Quotes match a phrase; `-word` excludes.
3. Use the filters: **City, Province, Term**, work-mode chips, duration checkboxes, and **+ Add skill**
   (adding several skills means a posting must have *all* of them). Remote jobs always show in a city filter.
4. Click a column header to sort; change **Rows per page**; page with **Prev/Next**.
5. Notice the URL changes as you go. Copy it and open it in a new tab to get the exact same view.
6. Click a posting for its full description, skills, a link to the original, and **Similar postings**.

### 3.2 Smart (semantic) search
Click **Smart search** next to the search box and try `low-level hardware programming`. It finds postings by
*meaning* (e.g. embedded C/firmware roles) even when those words don't appear.

### 3.3 Create an account
Click **Register**, enter an email and a password of at least 10 characters. You stay logged in for 7 days of
activity. **Sign out** ends the session immediately.

### 3.4 Track your applications
1. Click the bookmark icon on any posting to save it.
2. Open **Saved** in the header.
3. **Table view**: use the status tabs to filter; set a status on each card (Saved → Applying → Applied →
   Interview → Offer / Rejected / Withdrawn). Each change can include a note and a date (e.g. interview day),
   and the card keeps the full history.
4. **Board view**: drag cards between status columns.
5. The top panels show your stats and **Deadlines this week**.
6. **↓ CSV** downloads your whole tracker as a spreadsheet.

### 3.5 Add your AI key, then match your resume
1. Click **AI key** in the top bar. Choose **Gemini** (free tier), **ChatGPT**, or **Claude**, follow the 3 short
   steps to get a key ([AI_KEYS.md](AI_KEYS.md) has more detail), paste it, click **Check key**, then
   **Use this key**. The top bar now shows **✓ AI key**. Your key stays in your browser.
2. Open **Matches** and upload your resume (**PDF or DOCX, max 5 MB**).
3. Wait 10–30 seconds. You get up to 20 postings ranked by fit, each with a **0–100 score** (green ≥ 70,
   yellow 40–69, red < 40) and a one-sentence reason.
4. On any match, click **Ask about this role** and ask, for example:
   - "What skills am I missing for this role?"
   - "Which of my projects are most relevant here?"
   - "Does this role want Python or Java?"

   The answer streams in word by word. Claims start with **Resume:** or **Posting:** to show where they came from.
   If the answer isn't in your resume or the posting, it says *"I don't have enough information to answer that."*
5. Upload again any time to replace your resume. Delete it under **Account → Resume** (this also deletes matches).

### 3.6 Add postings yourself
Open **Add postings**:
- **CSV upload**: try the sample file `backend/tests/fixtures/ingest/sample_postings.csv`. Required columns:
  `title, company, city, term, deadline` (deadline as `YYYY-MM-DD`). Optional: `work_mode, province, skills,
  duration_months, description, source_url`. Bad rows are listed by line number; duplicates are skipped.
  The limit is 3 uploads per hour.
- **Manual form**: fill in title, company, city, term, deadline (and optional details).

### 3.7 Admin: ingestion sources
1. Make your account an admin (use the email you registered with):
   ```powershell
   docker compose exec db psql -U coopradar -d coopradar -c "UPDATE users SET is_admin = TRUE WHERE email = 'you@example.com';"
   ```
   (If you changed `POSTGRES_USER`/`POSTGRES_DB` in `.env`, use those names.)
2. Refresh the app. An **Admin** link appears. It lists the two demo sources.
3. Click **Run now** on *Acme Jobs (Dev Fixture)*, wait a few seconds, and refresh. **History** shows
   `+5 added`. Run it again: 0 added, 5 updated, nothing closed (proof that re-runs are safe).
4. Sources also re-run automatically every 6 hours. A source that fails 3 times in a row is **auto-paused**;
   fix it and click **Re-enable**.

### 3.8 Account settings
**Account** (click your email in the header): change password, manage your resume, or permanently delete your
account and all your data.

---

## Part 4: Day-to-day commands

These are for **developer mode**. In website mode, add `-f docker-compose.prod.yml` after `docker compose`.

| I want to… | Command |
|---|---|
| Start the app | `docker compose up` (add `--build` after pulling code changes) |
| Start in the background | `docker compose up -d` (logs: `docker compose logs -f api`) |
| Stop the app | `Ctrl+C` in the running terminal, or `docker compose down` |
| Wipe all data and start fresh | `docker compose down -v`, then start, seed, and embed again |
| See what's running | `docker compose ps` |
| Open a database shell | `docker compose exec db psql -U coopradar -d coopradar` |
| Run backend tests | `docker compose exec api pytest -q -m "not perf"` |
| Run frontend checks | `cd frontend; npm install; npm run lint; npm run typecheck; npm test` |

Your data lives in a Docker volume, so it survives restarts and only `down -v` deletes it.

---

## Part 5: If something goes wrong

| Problem | Fix |
|---|---|
| "You've used today's 20 AI actions" | The per-user daily AI limit (`AI_DAILY_LIMIT` in `.env`; `0` = unlimited). |
| `docker: command not found` / "cannot connect to the Docker daemon" | Open Docker Desktop and wait for "Engine running". |
| `port is already allocated` (5432, 6379, 8000 or 5173) | Another program uses that port (often a local Postgres). Stop it, or change the left-hand port in `docker-compose.yml`, e.g. `"5433:5432"`. |
| The page loads but shows no postings | Run the seed command (2.2). |
| "Add your own AI key…" | No key is saved in this browser: click **AI key** (3.5). |
| "…rejected the API key" | Copied wrong or deleted. Make a new key and **Check key** again. |
| "…out of credit or over its rate limit" | Add credit at your provider, or wait a minute (free tiers have per-minute limits). |
| **Matches** says "No matches found yet" | There are no open postings yet: run the seed command (2.2). |
| **Run now** says the job queue is unavailable | `docker compose ps`: the `worker` and `redis` containers must be running. |
| Logged in but the app acts logged out | Always use http://localhost:5173 (not `127.0.0.1` or port 8000) so the login cookie is sent. |
| You changed `.env` | Containers read it at start: `docker compose down` then `docker compose up`. |
| Anything else | `docker compose logs api` and `docker compose logs worker` usually show the real error. |
