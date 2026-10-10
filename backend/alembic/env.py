"""
Alembic environment — async-compatible.

We use run_async_migrations() so the same DATABASE_URL (postgresql+asyncpg://…)
works for both the app and migrations without maintaining two connection strings.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy.pool import NullPool

# Import Base so Alembic can see all mapped tables for autogenerate
from app.db import Base
from app.config import get_settings

# Import all models so their metadata is registered on Base before autogenerate runs
import app.models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Tell Alembic which metadata to diff against the DB
target_metadata = Base.metadata


def get_url() -> str:
    """Read the real URL from settings rather than alembic.ini."""
    return get_settings().database_url


def run_migrations_offline() -> None:
    """
    Offline mode: write SQL to a file instead of running against a live DB.
    Useful for generating migration scripts for review before applying.
    """
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: object) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)  # type: ignore[arg-type]
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """
    Online mode: connect to the DB and apply migrations.
    NullPool prevents connection pooling during migrations (one-shot operation).
    """
    cfg = config.get_section(config.config_ini_section, {})
    cfg["sqlalchemy.url"] = get_url()

    engine = async_engine_from_config(
        cfg,
        prefix="sqlalchemy.",
        poolclass=NullPool,
    )

    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
