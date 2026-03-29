"""FastAPI application entrypoint."""

import logging
from contextlib import asynccontextmanager

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import migrations
from sidekick.api.routers.agent_configs import router as agent_configs_router
from sidekick.api.routers.api_clients import router as api_clients_router
from sidekick.api.routers.artifacts import router as artifacts_router
from sidekick.api.routers.assignments import router as assignments_router
from sidekick.api.routers.sources import router as sources_router
from sidekick.api.settings import get_settings

logger = logging.getLogger(__name__)


def run_migrations() -> None:
    """Apply all pending Alembic migrations."""
    settings = get_settings()
    cfg = Config()
    cfg.set_main_option("script_location", str(migrations.MIGRATIONS_DIR))
    cfg.set_main_option("sqlalchemy.url", settings.database_url)
    logger.info("Running database migrations…")
    command.upgrade(cfg, "head")
    logger.info("Migrations complete.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_migrations()
    yield


def create_app() -> FastAPI:
    """Build and configure the API app."""
    app = FastAPI(title="Sidekick API", version="0.1.0", lifespan=lifespan)
    settings = get_settings()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(sources_router)
    app.include_router(assignments_router)
    app.include_router(agent_configs_router)
    app.include_router(artifacts_router)
    app.include_router(api_clients_router)
    return app


app = create_app()
