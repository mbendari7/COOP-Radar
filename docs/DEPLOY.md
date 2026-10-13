# Deploy CoopRadar as a Website

This guide puts CoopRadar on the internet so anyone can use it from a link: classmates, a co-op office, an employer
reviewing your portfolio. No Docker anywhere: the host installs Python and Node.js packages, builds the site, and
runs one command.

> The short, step-by-step free setup (Render + Neon + GitHub Actions, optional Vercel) is in the
> [README](../README.md#host-it-for-free). This page has the details and other hosts.

**What gets deployed:** one web service plus one PostgreSQL database. Every host runs the same two commands:

| Step | Command |
|---|---|
| Build | `pip install -e backend && npm ci --prefix frontend && npm run build --prefix frontend` |
| Start | `python start.py --hosted` |

`start.py --hosted` then:
1. applies database migrations (`alembic upgrade head`)
2. seeds the skills list and the **~120 employer career boards** (safe to repeat)
3. starts the web server on `$PORT`, serving the React site and the API from one address
4. inside that server, a background scheduler imports real jobs from the boards right away, then every 6 hours

It needs **PostgreSQL 16 with the `pgvector` extension available** (Neon, Supabase, Render, Railway and most
managed Postgres hosts have it). Redis is **optional**: without `REDIS_URL`, login sessions and rate limits are
kept in a small Postgres table. The database is about 50 MB with ~2,800 open jobs.

---

## Option A: Render + Neon, free (recommended)

`render.yaml` is a **Blueprint**: Render reads it and creates the website (native Python runtime, which includes
Node.js for the build), then redeploys on every push to `main`. The database is on **Neon**, whose free plan doesn't
expire (Render's free Postgres is deleted 30 days after it's created).

1. **Neon**: sign up at https://neon.tech, create a project, click **Connect**, turn *Connection pooling* off and
   copy the connection string (`postgresql://...neon.tech/neondb?sslmode=require&channel_binding=require`). The app
   converts it for asyncpg itself (`sslmode` becomes `ssl`, `channel_binding` is dropped).
2. **Render**: sign up at https://render.com with **GitHub**, then **New → Blueprint** and pick the repo.
3. Paste the Neon string into `DATABASE_URL`. Leave `ANTHROPIC_API_KEY` and `OPENAI_API_KEY` **blank**: visitors
   bring their own AI key. Click **Apply**.
4. The first build takes about 5 to 10 minutes. Your site is at `https://coopradar-xxxx.onrender.com`. Add your own
   domain under **Settings → Custom Domains** if you like.
5. Within a few minutes of going live, about 2,800 jobs are imported. Refresh **Find jobs** to see them.
6. **Keep jobs fresh**: in GitHub, **Settings → Secrets and variables → Actions → Variables**, add `SITE_URL` with
   your Render address. `.github/workflows/refresh-jobs.yml` then wakes the site every 6 hours and keeps it up for
   about 20 minutes so every board is re-imported. It's free for public repositories.

**Free plan caveats** (check the providers' pricing pages, since these change):
- The free Render web service **sleeps after about 15 minutes idle**. The first visit after that takes about a
  minute. Logins survive the sleep because sessions are stored in the database.
- Neon's free plan has 0.5 GB of storage and a monthly compute allowance; its database also sleeps after 5 idle
  minutes and wakes in about a second. CoopRadar uses a small fraction of both.
- For a pitch or interview, open the site a minute early, or upgrade the Render service to a paid instance
  (always on).

Already deployed with Render's own database? Create the Neon project, change `DATABASE_URL` in the Render
dashboard (**Environment**), and redeploy; the site migrates and re-imports jobs by itself. Accounts and saved jobs
from the old database aren't copied (use `pg_dump` / `psql` if you need them).

---

## Option A2: Vercel in front of Render

Vercel is great at serving websites, but its servers only run for a moment per request, while CoopRadar's API keeps
running: it imports jobs every 6 hours and needs a Postgres database. So the split is:

- **Render** runs the API, with the database on Neon (Option A).
- **Vercel** serves the React pages from its CDN and forwards `/api/*` to Render (`vercel.json`). The browser only
  ever sees the Vercel address, so login cookies stay first-party and no CORS setup is needed.

Steps:
1. Deploy Option A and note the Render address (for example `https://coopradar.onrender.com`).
2. If it differs, edit the `destination` in `vercel.json` to your Render address. Keep `/api/:path*` on the end,
   like `https://your-site.onrender.com/api/:path*`. Without it every request goes to the Render home page and the
   jobs page says the jobs didn't load. `backend/tests/api/test_hosting.py` checks this.
3. On https://vercel.com: **Add New, Project**, import the repo, keep the defaults (`vercel.json` sets the build
   command `npm run build --prefix frontend` and output `frontend/dist`), and deploy.
4. Open `https://<project>.vercel.app/api/health`. It should say `{"status":"ok"}`. Then open
   `https://<project>.vercel.app/api/postings?page_size=10`. It should be JSON with `items`, not a web page.

Notes: `vercel.json` turns off Vercel caching for `/api` because answers are per visitor. The Render free plan
still sleeps after about 15 minutes, so the first request after a quiet spell waits for it to wake. Running the
whole thing on Vercel alone would mean replacing the in-process importer with Vercel Cron jobs (which have short
time limits per run, while a full import takes several minutes); that's possible but not set up here.

---

## Option B: Any other host that runs Python

Railway, Fly.io, Koyeb, Heroku, Azure App Service, Google App Engine and similar hosts all work the same way:
1. Create a web service from this repo.
2. Set the **build command** and **start command** from the table at the top. Set the Python version to 3.12 and
   make sure Node.js 20+ is available at build time (most hosts detect `frontend/package.json` or let you add it).
3. Add a **PostgreSQL** database and put its connection URL in `DATABASE_URL`. Host-style URLs (`postgres://…`,
   `?sslmode=require`) are converted automatically.
4. Health check path: `/api/health`.

---

## Option C: Your own server (VPS)

Any Linux server with about 1 GB of RAM works (DigitalOcean, Hetzner, AWS Lightsail, Oracle Cloud).

```bash
sudo apt install -y python3.12 python3.12-venv nodejs npm postgresql postgresql-16-pgvector caddy
sudo -u postgres createuser coopradar --pwprompt && sudo -u postgres createdb -O coopradar coopradar
git clone https://github.com/mbendari7/COOP-Radar.git && cd COOP-Radar
echo "DATABASE_URL=postgresql://coopradar:YOUR_PASSWORD@localhost:5432/coopradar" > .env
python3.12 -m venv .venv && . .venv/bin/activate
pip install -e backend && npm ci --prefix frontend && npm run build --prefix frontend
PORT=8000 python start.py --hosted        # site on http://<server-ip>:8000
```

To keep it running after you log out, create a systemd service whose `ExecStart` is
`/path/to/COOP-Radar/.venv/bin/python /path/to/COOP-Radar/start.py --hosted` with `WorkingDirectory` set to the
repo and `Environment=PORT=8000`.

**Add a domain and free HTTPS** (needed for logins: browsers only send Secure cookies over HTTPS): point an
**A record** at the server, then run `sudo caddy reverse-proxy --from coopradar.yourname.dev --to localhost:8000`
(or put the same in `/etc/caddy/Caddyfile`). Caddy gets a Let's Encrypt certificate automatically.

| Task | Command |
|---|---|
| Update to the latest code | `git pull && pip install -e backend && npm ci --prefix frontend && npm run build --prefix frontend`, then restart the service |
| Make yourself admin | `psql "$DATABASE_URL" -c "UPDATE users SET is_admin = TRUE WHERE email = 'you@example.com';"` |
| Back up the database | `pg_dump "$DATABASE_URL" > backup.sql` |

---

## Environment variables

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `DATABASE_URL` | ✅ on a host | local database (`start.py` on your computer) | Postgres connection URL |
| `REDIS_URL` | | empty | *Optional:* keep sessions and rate limits in Redis instead of Postgres |
| `DEMO_ENABLED` | | `true` | "Try the demo" plus uploading without an account (temporary accounts, 7 days) |
| `AI_DAILY_LIMIT` | | `20` | AI actions per user per day on *your* key (visitors' own keys are never limited) |
| `ANTHROPIC_API_KEY` | | empty | *Optional:* shared Claude key for visitors without one (daily-limited) |
| `OPENAI_API_KEY` | | empty | *Optional:* turns on smart (semantic) search and similar postings |
| `SEED_ON_START` | | `true` | Run the seed on every start (idempotent) |
| `SEED_JOB_BOARDS` / `SEED_SAMPLE_POSTINGS` / `SEED_DEV_SOURCES` | | `true` / `false` / `false` | What the seed loads: real boards, made-up postings, Admin-page fixtures |
| `INGEST_INTERVAL_HOURS` | | `6` | How often each career board is re-imported |
| `INGEST_LOCATION_FILTER` | | Canada | Regex on job location. Empty means Canada; `.*` means everywhere. |
| `INGEST_US_JOBS` | | `students` | US jobs: `students` (co-op / intern / new grad titles), `all`, or `none` |
| `BACKGROUND_JOBS` | | `true` | Run the importer inside the web server |
| `COOKIE_SECURE` | | `true` | Keep `true` on HTTPS |
| `PORT` | | `8000` | Port to listen on (hosts set this) |

**Adding or removing employers:** edit `backend/seed/job_boards.py` (company,
`greenhouse`/`lever`/`ashby`/`smartrecruiters`, board name from the careers URL) and redeploy. Admins can also pause sources on the **Admin** page.

---

## Before you share the link

1. Open the site in a **private window**. **Find jobs** lists real postings; clicking one shows its details beside
   the list.
2. Go to **Match my resume** and drop in a resume. Its program and graduation year are read, and 20 matches with
   "why it fits" notes appear with no key.
3. Click **AI key** and add a free Gemini key. Then click **Review my resume** (Resume feedback tab) and, on a match, **Tailor my resume**.
4. Click **Keep my account**, add an email and password, sign out, and sign back in. Your resume should still be there.
5. Click **Try the demo** in another private window. You should see a filled tracker and resume page.
6. Add the link to the top of the README ("Live site" line) and to your pitch slides.
7. If you set your own AI keys, also set a monthly spending limit in those providers' consoles.
