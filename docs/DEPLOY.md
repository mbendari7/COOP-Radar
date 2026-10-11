# Deploy CoopRadar as a Website

This guide puts CoopRadar on the internet so anyone, including an employer, can use it from a link. No installing,
no Docker, no commands on their side.

**How it works:** the root `Dockerfile` builds the whole website into **one container**. That container serves the
React site and the API on the same address. When it starts, it automatically:
1. creates or updates the database tables
2. loads the sample postings (skipping any that already exist)
3. starts the background worker (job feeds + AI search vectors)
4. creates AI search vectors for postings that don't have one yet (if an OpenAI key is set)

It needs two companions: a **PostgreSQL** database (with the `pgvector` extension) and **Redis**. Both options below
set those up for you.

---

## What visitors get

- A **"Try the demo"** button. Each visitor gets a *private* demo account filled with sample applications and
  resume matches. Demo accounts are deleted after 24 hours, and each network can create 10 per hour.
- Normal sign-up for anyone who wants to keep their own data.
- **Bring your own AI key**: each visitor adds their own Claude, ChatGPT, or Gemini key on the **AI key** page
  (with step-by-step instructions). Their key stays in their browser, so **you pay nothing for AI** and need no
  AI keys on the server.
- Optional: set `ANTHROPIC_API_KEY` to let visitors *without* a key use AI on your account. That's capped by
  `AI_DAILY_LIMIT` (default 20 actions per person per day). Demo matches never use AI.

> **HTTPS matters here**: visitors' keys travel from their browser to your server. Always serve the public site
> over HTTPS (option A3, or any host in options B/C, which provide it automatically).

---

## Option A: Your own server (VPS) with Docker (recommended)

Works on any Linux server with Docker, e.g. a small cloud VM (DigitalOcean, Hetzner, AWS Lightsail, Oracle Cloud).
**About 1 GB of RAM** is enough.

### A1. Prepare the server (one time)
```bash
# On a fresh Ubuntu server: install Docker
curl -fsSL https://get.docker.com | sh

# Get the code
git clone https://github.com/mbendari7/COOP-Radar.git
cd COOP-Radar
cp .env.example .env
nano .env        # set POSTGRES_PASSWORD (a long random one); AI keys are optional
```

### A2. Start it
```bash
docker compose -f docker-compose.prod.yml up -d --build
```
Wait about a minute, then open `http://<your-server-ip>:8080`.

> Browsers only send login cookies over **HTTPS**, or to `localhost`. Visiting by plain IP over http lets you browse
> but not log in. Either add a domain + HTTPS (A3), or for a quick test only set `COOKIE_SECURE=false` in `.env` and
> restart.

### A3. Add your domain + free HTTPS
1. At your domain registrar, create an **A record** pointing your domain (e.g. `coopradar.yourname.dev`) to the
   server's IP address. Wait until it resolves (a few minutes to an hour).
2. Add `DOMAIN=coopradar.yourname.dev` to `.env`.
3. Start with the `https` profile:
   ```bash
   docker compose -f docker-compose.prod.yml --profile https up -d --build
   ```
   Caddy gets a free Let's Encrypt certificate automatically. Your site is now at `https://coopradar.yourname.dev`.
   Make sure the server's firewall allows ports **80** and **443**.

### A4. Update to the latest code
```bash
git pull
docker compose -f docker-compose.prod.yml --profile https up -d --build
```
Your data lives in Docker volumes and survives updates. **Never** run `down -v` on the server: `-v` deletes the
database.

### A5. Useful server commands
| Task | Command |
|---|---|
| See logs | `docker compose -f docker-compose.prod.yml logs -f app` |
| Status | `docker compose -f docker-compose.prod.yml ps` |
| Restart after editing `.env` | `docker compose -f docker-compose.prod.yml --profile https up -d` |
| Make your account an admin | `docker compose -f docker-compose.prod.yml exec db psql -U coopradar -d coopradar -c "UPDATE users SET is_admin = TRUE WHERE email = 'you@example.com';"` |
| Back up the database | `docker compose -f docker-compose.prod.yml exec db pg_dump -U coopradar coopradar > backup.sql` |

---

## Option B: Render (click-through, no server to manage)

`render.yaml` in the repo is a **Blueprint**: Render reads it and creates the website, a Postgres database, and a
Redis-compatible store in one go, then redeploys on every push to `main`.

1. Sign up at https://render.com with your GitHub account.
2. **New → Blueprint**, then pick the `COOP-Radar` repository.
3. Render shows the three resources it will create. Review the plans and prices on that screen; the file asks
   for free plans where available. Free web services sleep after inactivity, and free databases expire after a
   trial period, so pick paid plans for an always-on portfolio site.
4. When asked for `ANTHROPIC_API_KEY` and `OPENAI_API_KEY`, leave them blank: visitors bring their own keys.
5. Click **Apply**. The first build takes several minutes. Your site is at `https://coopradar-xxxx.onrender.com`
   (you can add your own domain under the service's **Settings → Custom Domains**).

> If Render reports that the `vector` or `fuzzystrmatch` extension isn't available on your database plan, choose a
> plan that supports extensions, or use Option A.

---

## Option C: Any other host that runs Docker images

Railway, Fly.io, Google Cloud Run, Azure Container Apps, and similar hosts all work the same way:
1. Deploy the repo's root **`Dockerfile`** as a web service (port from `PORT`, default 8000; health check
   `/api/health`).
2. Add a **PostgreSQL 16** database with the `vector` and `fuzzystrmatch` extensions available, and a **Redis**.
3. Set the environment variables below. The host's database URL works as-is (`postgres://…` is converted
   automatically).

---

## Environment variables

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `DATABASE_URL` | ✅ | — | Postgres connection URL |
| `REDIS_URL` | ✅ | — | Redis connection URL |
| `ANTHROPIC_API_KEY` | | empty | *Optional:* shared Claude key for visitors without their own (daily-limited) |
| `OPENAI_API_KEY` | | empty | *Optional:* turns on smart search + similar postings |
| `DEMO_ENABLED` | | `true` | Show the "Try the demo" button |
| `AI_DAILY_LIMIT` | | `20` | AI actions per user per day (`0` = unlimited) |
| `SEED_ON_START` | | `true` | Load the sample postings on start |
| `RUN_WORKER` | | `true` | Run the background worker inside the container |
| `COOKIE_SECURE` | | `true` | Keep `true` whenever the site uses HTTPS |
| `AGENT_MODEL` / `FAST_MODEL` | | `claude-opus-5-5` / `claude-haiku-5-5` | Claude models |
| `PORT` | | `8000` | Port inside the container (hosts usually set this) |

---

## Before you share the link

- [ ] Open the site in a private/incognito window and click **Try the demo**. You should land on a filled tracker.
- [ ] Check **Matches** shows demo matches, and a posting's detail page loads.
- [ ] Click **AI key**, add your own key (Gemini's free tier is fine), upload a resume on **Matches**, and ask a question.
- [ ] Put the link at the top of the README (replace the placeholder in the "Live demo" line).
- [ ] Set a monthly spending limit in the Anthropic and OpenAI consoles as a second safety net.
