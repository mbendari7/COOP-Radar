# Deploy CoopRadar as a Website

This guide puts CoopRadar on the internet so anyone can use it from a link: classmates, a co-op office, an employer
reviewing your portfolio. **You don't need Docker on your computer** for option A. The host builds everything for you.

> Just want the short version for non-developers? See the [User Guide](USER_GUIDE.md#put-your-own-copy-online-no-docker-no-coding).

**What gets deployed:** the root `Dockerfile` builds the whole site into **one container**, which serves the React
app and the API on one address. On every start, `backend/scripts/start.sh`:
1. applies database migrations (`alembic upgrade head`)
2. seeds the skills list and the **27 employer career boards** (safe to repeat)
3. starts the background worker. It imports real jobs from those boards right away, then every 6 hours.
4. starts the web server

It needs **PostgreSQL 16 with `pgvector`** and **Redis**. Every option below sets both up.

---

## Option A: Render, one click and no Docker (recommended to start)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/mbendari7/COOP-Radar)

`render.yaml` is a **Blueprint**. Render reads it and creates the website, a Postgres database, and a
Redis-compatible store, then redeploys on every push to `main`.

1. Sign up at https://render.com with **GitHub**.
2. Click the button above (or **New → Blueprint** and pick the repo).
3. Review the three resources and plans, then click **Apply**.
4. Leave `ANTHROPIC_API_KEY` and `OPENAI_API_KEY` **blank**. Visitors bring their own AI key.
5. The first build takes about 5–10 minutes. Your site is at `https://coopradar-xxxx.onrender.com`. Add your own
   domain under **Settings → Custom Domains** if you like.
6. Within a couple of minutes of going live, the worker imports roughly 700–800 Canadian jobs. Refresh **Jobs** to see them.

**Free plan caveats** (check Render's pricing page, since these change):
- The free web service **sleeps after about 15 minutes idle**. The first visit after that takes about a minute.
  The importer only runs while the site is awake and catches up when it wakes.
- The free Postgres database is **time-limited** (about 30 days at the time of writing). Upgrade it before then
  to keep accounts and data.
- For a pitch or interview, upgrade the web service to a paid instance (always on) or open the site a minute early.

The Blueprint sets these for a public site: `SEED_SAMPLE_POSTINGS=false` (real jobs only),
`SEED_DEV_SOURCES=false`, `DEMO_ENABLED=true`, `AI_DAILY_LIMIT=20`.

---

## Option B: Your own server (VPS) with Docker

Any Linux server with Docker and about 1 GB of RAM works, such as DigitalOcean, Hetzner, AWS Lightsail, or Oracle Cloud.

```bash
curl -fsSL https://get.docker.com | sh                    # fresh Ubuntu: install Docker
git clone https://github.com/mbendari7/COOP-Radar.git && cd COOP-Radar
cp .env.example .env && nano .env                         # set POSTGRES_PASSWORD (long, random)
docker compose -f docker-compose.prod.yml up -d --build   # site on http://<server-ip>:8080
```

**Add a domain and free HTTPS** (needed for logins: browsers only send Secure cookies over HTTPS):
1. Point an **A record** for your domain at the server's IP.
2. Add `DOMAIN=coopradar.yourname.dev` to `.env`.
3. `docker compose -f docker-compose.prod.yml --profile https up -d --build`. Caddy gets a Let's Encrypt
   certificate automatically. Open ports 80 and 443.

| Task | Command |
|---|---|
| Update to the latest code | `git pull && docker compose -f docker-compose.prod.yml --profile https up -d --build` |
| Logs | `docker compose -f docker-compose.prod.yml logs -f app` |
| Make yourself admin | `docker compose -f docker-compose.prod.yml exec db psql -U coopradar -d coopradar -c "UPDATE users SET is_admin = TRUE WHERE email = 'you@example.com';"` |
| Back up the database | `docker compose -f docker-compose.prod.yml exec db pg_dump -U coopradar coopradar > backup.sql` |

Never run `down -v` on a server: `-v` deletes the database volume.

---

## Option C: Any host that runs a Dockerfile

Railway, Fly.io, Google Cloud Run, Azure Container Apps, and similar hosts:
1. Deploy the root **`Dockerfile`** as a web service (it listens on `PORT`, default 8000; health check `/api/health`).
2. Add **PostgreSQL 16** with the `vector` extension available, plus **Redis**.
3. Set the variables below. Host-style URLs (`postgres://…`, `?sslmode=require`) are converted automatically.

---

## Environment variables

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `DATABASE_URL` | ✅ | — | Postgres connection URL |
| `REDIS_URL` | ✅ | — | Redis connection URL |
| `DEMO_ENABLED` | | `true` | "Try the demo" plus uploading without an account (temporary accounts, 7 days) |
| `AI_DAILY_LIMIT` | | `20` | AI actions per user per day on *your* key (visitors' own keys are never limited) |
| `ANTHROPIC_API_KEY` | | empty | *Optional:* shared Claude key for visitors without one (daily-limited) |
| `OPENAI_API_KEY` | | empty | *Optional:* turns on smart (semantic) search and similar postings |
| `SEED_ON_START` | | `true` | Run the seed on every start (idempotent) |
| `SEED_JOB_BOARDS` / `SEED_SAMPLE_POSTINGS` / `SEED_DEV_SOURCES` | | `true` | What the seed loads. Public sites: boards on, samples and dev sources off. |
| `INGEST_INTERVAL_HOURS` | | `6` | How often each career board is re-imported |
| `INGEST_LOCATION_FILTER` | | Canada | Regex on job location. Empty means Canada; `.*` means everywhere. |
| `RUN_WORKER` | | `true` | Run the importer inside the web container |
| `COOKIE_SECURE` | | `true` | Keep `true` on HTTPS |
| `PORT` | | `8000` | Port inside the container (hosts set this) |

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
