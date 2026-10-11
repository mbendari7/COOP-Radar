#!/bin/sh
# Production entrypoint for the all-in-one CoopRadar container (see the root Dockerfile).
# One container = the whole website: it prepares the database, then serves the React app
# and the API on one port, with the background worker running alongside.
set -e

echo "==> Applying database migrations"
alembic upgrade head

if [ "${SEED_ON_START:-true}" = "true" ]; then
  echo "==> Loading sample data (safe to repeat: existing rows are skipped)"
  python -m seed
fi

if [ "${RUN_WORKER:-true}" = "true" ]; then
  echo "==> Starting background worker (ingestion + embeddings)"
  python -m app.worker &
fi

if [ -n "${OPENAI_API_KEY:-}" ]; then
  echo "==> Creating embeddings for postings that don't have one yet (background)"
  python -m app.ingest.embed &
fi

echo "==> Starting web server on port ${PORT:-8000}"
# --proxy-headers: trust X-Forwarded-* from the hosting provider's HTTPS proxy
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" \
  --proxy-headers --forwarded-allow-ips='*'
