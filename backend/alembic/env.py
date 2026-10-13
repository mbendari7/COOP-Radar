"""
Alembic setup that works with async.

run_async_migrations() lets the app and the migrations share the same DATABASE_URL
so there is only one connection string to keep track of.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy.pool import NullPool

# Import every model so Base knows about them before autogenerate runs
import app.models  # noqa: F401
from app.config import get_settings

# Import Base so Alembic can see every table for autogenerate
from app.db import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Tell Alembic which models to compare with the database
target_metadata = Base.metadata


def get_url() -> str:
    """Get the real URL from settings and not from alembic.ini."""
    return get_settings().database_url


def run_migrations_offline() -> None:
    """
    Offline mode writes SQL to a file instead of running it on a live database.
    Handy for reading a migration before you apply it.
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
    Online mode connects to the database and runs the migrations.
    NullPool skips connection pooling since migrations run once and exit.
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
