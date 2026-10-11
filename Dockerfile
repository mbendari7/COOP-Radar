# Production image: the whole CoopRadar website in one container.
#
#   docker build -t coopradar .
#   docker run -p 8000:8000 -e DATABASE_URL=... -e REDIS_URL=... coopradar
#
# Stage 1 builds the React frontend; stage 2 installs the FastAPI backend and copies the
# built site into it. The API serves the site (STATIC_DIR), so there's one URL and no CORS.
# Development still uses docker-compose.yml (hot reload, separate containers).

# ── Stage 1: build the website ────────────────────────────────────────────────
FROM node:22-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ── Stage 2: API + built website ─────────────────────────────────────────────
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    STATIC_DIR=/app/static \
    PORT=8000
WORKDIR /app

# Dependencies first (cached until pyproject.toml changes). Empty package stubs let the
# editable install resolve before the source is copied in.
COPY backend/pyproject.toml ./
RUN mkdir -p app seed \
    && touch app/__init__.py seed/__init__.py \
    && pip install -e .

COPY backend/ ./
COPY --from=web /web/dist ./static

# Run as a non-root user
RUN useradd --create-home --uid 10001 appuser && chown -R appuser /app
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"8000\")}/api/health')"

CMD ["sh", "scripts/start.sh"]
