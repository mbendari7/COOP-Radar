FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first so this layer is cached until pyproject.toml changes.
# Empty package stubs let the editable install resolve before the source is copied.
COPY pyproject.toml ./
RUN mkdir -p app seed \
    && touch app/__init__.py seed/__init__.py \
    && pip install -e ".[dev]"

# Source is bind-mounted in dev (docker-compose); this COPY is for standalone builds.
COPY . .

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
