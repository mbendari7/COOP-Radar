FROM python:3.12-slim

WORKDIR /app

# Install system deps needed by asyncpg (libpq) and psycopg2 builds.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc && rm -rf /var/lib/apt/lists/*

# Copy deps first so Docker can cache this layer independently of source changes.
COPY pyproject.toml ./

# Install all deps including dev/test extras.
RUN pip install --no-cache-dir -e ".[dev]"

# Source is bind-mounted in dev; this COPY is for production-like builds.
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
