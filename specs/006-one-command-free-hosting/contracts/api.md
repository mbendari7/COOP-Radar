# API Contracts: One Command Run and Free Hosting

**Feature**: 006-one-command-free-hosting
**Date**: 2026-10-29 (written up 2026-11-17)

## `GET /api/postings/snapshot`

The jobs page as nobody has filtered it yet. The same for every visitor, so it never includes `is_saved` or
anything else tied to a person.

**200**: `PostingsSnapshot`

```json
{
  "postings": {"items": [...], "total": 30840, "page": 1, "page_size": 25},
  "filters": { "...": "the same as GET /api/postings/meta/filters" },
  "first_job": { "...": "PostingDetail for items[0], or null" }
}
```

**Headers**: `Cache-Control: public, s-maxage=300, stale-while-revalidate=604800`

This is the only reply the CDN may cache. `vercel.json` sets that rule for this path alone.

## `GET /api/health`

**200**: `{"status": "ok"}`. It never touches the database, so it answers as soon as the server is up. Render uses
it as the health check and the keep awake workflow pings it.

## Built site serving (`main.py → mount_frontend`)

| Path | Served as | Cache |
|---|---|---|
| `/assets/*` (hashed file names) | the file | one year, immutable |
| `/index.html` and any page route like `/resume` | `index.html` | `no-cache` |
| `/api/*` | the API | none, except the snapshot above |

Replies over 1 KB are gzipped. Paths that try to leave the build folder are refused.

## `vercel.json`

- Pages are served from Vercel's CDN
- `/api/:path*` is rewritten to `https://<render service>/api/:path*`. Losing the `/api/:path*` ending sends every
  API call to the Render home page (found 2026-10-13, now covered by `tests/api/test_hosting.py`)

## `start.py` command line

| Command | What it does |
|---|---|
| `python start.py` | Set up if needed, then serve the built site and API on http://localhost:8000 |
| `python start.py --dev` | Vite with hot reload on :5173 proxying `/api` to uvicorn with reload on :8000 |
| `python start.py --hosted` | Host mode: migrate, start uvicorn on `$PORT` at once, seed next to it |
