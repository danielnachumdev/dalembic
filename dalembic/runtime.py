from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from alembic import command
from alembic.config import Config

AlembicLoggingHook = Callable[[], None]


def to_sync_database_url(database_url: str) -> str:
    """Map async SQLAlchemy URLs to sync drivers for Alembic."""
    if database_url.startswith("sqlite+aiosqlite:"):
        return database_url.replace("sqlite+aiosqlite:", "sqlite:", 1)
    if "+asyncpg" in database_url:
        return database_url.replace("+asyncpg", "+psycopg", 1)
    if "+aiomysql" in database_url:
        return database_url.replace("+aiomysql", "+pymysql", 1)
    return database_url


def configure_alembic_console_logging(level: int = logging.INFO) -> None:
    """Attach a stderr StreamHandler to Alembic loggers when app logging is already configured."""
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(levelname)-5s [%(name)s] %(message)s"))
    for name in ("alembic", "alembic.runtime.migration"):
        logger = logging.getLogger(name)
        logger.setLevel(level)
        if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
            logger.addHandler(handler)


def upgrade_head(alembic_ini: Path, *, logging_hook: AlembicLoggingHook | None = None) -> None:
    """Apply all pending migrations (app startup helper)."""
    if logging_hook is not None:
        logging_hook()
    command.upgrade(Config(str(alembic_ini)), "head")
