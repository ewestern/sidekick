"""Alembic migration environment.

Reads DATABASE_URL from environment (or .env file) at runtime.
SQLModel metadata is imported from core/models.py so that autogenerate
detects schema changes from the model definitions — never from raw SQL.
"""

import os
from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

# Load .env so DATABASE_URL is available when running alembic locally
load_dotenv()

# Import all models so SQLModel.metadata is populated
import sidekick.core.models  # noqa: F401  — side-effect: registers table metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override the sqlalchemy.url from alembic.ini with the real DATABASE_URL
db_url = os.environ.get("DATABASE_URL")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (no live DB connection required)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live database connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
