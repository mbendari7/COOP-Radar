# Research: One Command Run and Free Hosting

**Feature**: 006-one-command-free-hosting
**Date**: 2026-10-11 to 2026-10-31 (written up 2026-11-17)

## 1. A database with no Docker

**Decision**: The `pgserver` pip package. It ships Postgres 16 with pgvector for Windows, macOS and Linux and
starts it from Python.

**Why**: Students already have Python. Installing Postgres by hand differs on every OS, and Docker Desktop is big
and needs admin rights on many school laptops.

**Detail**: Data lives in `~/.coopradar`, not in the repo, because OneDrive locks files while it syncs and
Postgres does not like that. `start.py` waits out crash recovery after a hard kill.

## 2. Sessions without Redis

**Decision**: A `Store` protocol (`hget`, `hset`, `incr`, `expire`, `delete`) with `PostgresStore` on a
`kv_store` table. Redis is used instead when `REDIS_URL` is set.

**Why**: Sessions and rate limit counters are tiny. One more service to run is not worth it at this size.
Expired rows are ignored on read and purged by the scheduler.

## 3. Background jobs without a worker

**Decision**: `app/jobs.py`. `enqueue(name, *args)` runs a registered job as an asyncio task, at most 3 at a time.
A scheduler task in the app lifespan imports due sources every 10 minutes.

**Why**: RQ needed Redis and a second process. Imports are mostly waiting on the network, which asyncio handles
well in one process.

**Learned later (2026-10-17)**: Going through 1,700 boards one at a time on a server that sleeps after about 20
minutes meant most boards never ran. Now it runs 3 at a time, never run first and then oldest first, so each wake
gets further.

## 4. Where to host

**Decision**: Render free web service on the native Python runtime, Neon free Postgres, optional Vercel in front.

**Why**: Render builds straight from the repo with `pip install -e backend && npm ci && npm run build` and starts
`python start.py --hosted`. Neon's free plan has pgvector. Render's own free database expires after 30 days,
so `render.yaml` stopped creating one on 2026-10-12.

**Neon detail**: Neon's URLs come with `channel_binding=require`, which asyncpg does not take, so `DATABASE_URL`
is cleaned up in config.

## 5. Staying awake

**Decision**: `.github/workflows/refresh-jobs.yml` pings the site every 10 minutes from 7 am to 1 am Eastern when
the `SITE_URL` repository variable is set.

**Why**: About 560 of the 750 free hours a month, and imports keep running through the day. Night time sleep is
fine.

**Open**: On 2026-11-15 the workflow was found skipped on every run because `SITE_URL` was never set.

## 6. Instant first page

**Decision**: `GET /api/postings/snapshot` returns the first page, the filter choices and the first job's details
with `Cache-Control: public, s-maxage=300, stale-while-revalidate=604800`. `vercel.json` lets only that path be
cached at the edge. The browser keeps its own copy in localStorage and uses it as placeholder data.

**Why**: The slow part was Render waking up, not the query. A copy at the edge or in the browser shows something
real at once. The normal list can not be cached because it includes `is_saved` for the signed in visitor.

**Turned down**: A paid always on plan. The point is free.

## 7. Faster wake ups

**Decision**: The seed keeps a fingerprint in `kv_store` (`seed:fingerprint`) and skips itself when nothing
changed (`SEED_FORCE=true` to load anyway). Boards load in two `jsonb_to_recordset` statements instead of about
3,400 round trips. `--hosted` opens the port first and seeds next to it. The importer waits
`INGEST_START_DELAY_SECONDS` (60) before its first pass.

## 8. Less data transfer on Neon

**Decision**: `defer(Posting.description)` in list queries, `search_vector` deferred in the model, re imports skip
unchanged descriptions, filter menus cached 2 minutes and the skills list an hour, gzip for replies over 1 KB.
