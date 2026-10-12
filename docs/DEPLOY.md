# Deploy CoopRadar as a Website

This guide puts CoopRadar on the internet so anyone can use it from a link: classmates, a co-op office, an employer
reviewing your portfolio. No Docker anywhere: the host installs Python and Node.js packages, builds the site, and
runs one command.

> Just want the short version for non-developers? See the [User Guide](USER_GUIDE.md#put-your-own-copy-online-no-coding).

**What gets deployed:** one web service plus one PostgreSQL database. Every host runs the same two commands:

| Step | Command |
|---|---|
| Build | `pip install -e backend && npm ci --prefix frontend && npm run build --prefix frontend` |
| Start | `python start.py --hosted` |

`start.py --hosted` then:
1. applies database migrations (`alembic upgrade head`)
2. seeds the skills list and the **27 employer career boards** (safe to repeat)
3. starts the web server on `$PORT`, serving the React site and the API from one address
4. inside that server, a background scheduler imports real jobs from the boards right away, then every 6 hours

It needs **PostgreSQL 16 with the `pgvector` extension available** (Render, Neon, Supabase, Railway and most
managed Postgres hosts have it). Redis is **optional**: without `REDIS_URL`, login sessions and rate limits are
kept in a small Postgres table.

---

## Option A: Render, one click (recommended to start)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/mbendari7/COOP-Radar)

`render.yaml` is a **Blueprint**. Render reads it and creates the website (native Python runtime, which includes
Node.js for the build) and a Postgres database, then redeploys on every push to `main`.

1. Sign up at https://render.com with **GitHub**.
2. Click the button above (or **New → Blueprint** and pick the repo).
3. Review the two resources and plans, then click **Apply**.
4. Leave `ANTHROPIC_API_KEY` and `OPENAI_API_KEY` **blank**. Visitors bring their own AI key.
5. The first build takes about 5–10 minutes. Your site is at `https://coopradar-xxxx.onrender.com`. Add your own
   domain under **Settings → Custom Domains** if you like.
6. Within a couple of minutes of going live, roughly 700–800 Canadian jobs are imported. Refresh **Jobs** to see them.

**Free plan caveats** (check Render's pricing page, since these change):
- The free web service **sleeps after about 15 minutes idle**. The first visit after that takes about a minute.
  The importer only runs while the site is awake and catches up when it wakes. Logins survive the sleep because
  sessions are stored in the database.
- The free Postgres database is **time-limited** (about 30 days at the time of writing). Upgrade it before then,
  or point `DATABASE_URL` at a free [Neon](https://neon.tech) or [Supabase](https://supabase.com) database instead.
- For a pitch or interview, upgrade the web service to a paid instance (always on) or open the site a minute early.

---

## Option A2: Vercel in front of Render

Vercel is great at serving websites, but its servers only run for a moment per request, while CoopRadar's API keeps
running: it imports jobs every 6 hours and needs a Postgres database. So the split is:

- **Render** runs the API and database (Option A).
- **Vercel** serves the React pages from its CDN and forwards `/api/*` to Render (`vercel.json`). The browser only
  ever sees the Vercel address, so login cookies stay first-party and no CORS setup is needed.

Steps:
1. Deploy Option A and note the Render address (for example `https://coopradar.onrender.com`).
2. If it differs, edit the `destination` in `vercel.json` to your Render address.
3. On https://vercel.com: **Add New, Project**, import the repo, keep the defaults (`vercel.json` sets the build
   command `npm run build --prefix frontend` and output `frontend/dist`), and deploy.
4. Open `https://<project>.vercel.app/api/health`; it should say `{"status":"ok"}`.

Notes: `vercel.json` turns off Vercel caching for `/api` because answers are per visitor. The Render free plan
still sleeps after about 15 minutes, so the first request after a quiet spell waits for it to wake. Running the
whole thing on Vercel alone would mean swapping the background importer for Vercel Cron and using a hosted Postgres
such as Neon; that's possible but not set up here.

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
| `BACKGROUND_JOBS` | | `true` | Run the importer inside the web server |
| `COOKIE_SECURE` | | `true` | Keep `true` on HTTPS |
| `PORT` | | `8000` | Port to listen on (hosts set this) |

**Adding or removing employers:** edit `backend/seed/job_boards.py` (company, `greenhouse`/`lever`/`ashby`,
board name from the careers URL) and redeploy. Admins can also pause sources on the **Admin** page.

---

## Before you share the link

1. Open the site in a **private window**. The home page shows the hero, and **Jobs** lists real postings with
   **Live** badges.
2. Go to **My resume** and drop in a resume. Skills found, in-demand skills, and 20 matches appear with no key.
3. Click **AI key** and add a free Gemini key. Then click **Get my AI review** and, on a match, **Tailor my resume**.
4. Click **Keep my account**, add an email and password, sign out, and sign back in. Your resume should still be there.
5. Click **Try the demo** in another private window. You should see a filled tracker and resume page.
6. Add the link to the top of the README ("Live site" line) and to your pitch slides.
7. If you set your own AI keys, also set a monthly spending limit in those providers' consoles.
