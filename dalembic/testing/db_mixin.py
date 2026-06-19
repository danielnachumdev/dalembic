from __future__ import annotations

import logging
import os

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from dalembic.dalembic_state import TABLE_NAME

logger = logging.getLogger(__name__)


class DbMixin:
    """DB connection, reset, queries, and assertions."""

    _db_engine: Engine
    _schema: str
    _state_key: str

    def assert_table_exists(self, table_name: str) -> None:
        assert self._table_exists(table_name), f"{table_name} should exist"
        logger.info("Verified: %s exists", table_name)

    def assert_table_not_exists(self, table_name: str) -> None:
        assert not self._table_exists(table_name), f"{table_name} should not exist"
        logger.info("Verified: %s does not exist", table_name)

    def assert_stamped_sha(self, expected_sha: str) -> None:
        actual = self._get_stamped_sha()
        assert actual == expected_sha, f"expected SHA {expected_sha}, got {actual}"
        logger.info("Verified: dalembic_state stamped with %s", expected_sha)

    def assert_column_exists(self, table_name: str, column_name: str) -> None:
        assert self._column_exists(table_name, column_name), f"{table_name}.{column_name} should exist"
        logger.info("Verified: %s.%s exists", table_name, column_name)

    def assert_column_not_exists(self, table_name: str, column_name: str) -> None:
        assert not self._column_exists(table_name, column_name), f"{table_name}.{column_name} should not exist"
        logger.info("Verified: %s.%s does not exist", table_name, column_name)

    def assert_column_type(self, table_name: str, column_name: str, expected_type: str) -> None:
        actual = self._get_column_type(table_name, column_name)
        assert actual == expected_type, f"{table_name}.{column_name}: expected '{expected_type}', got '{actual}'"
        logger.info("Verified: %s.%s is %s", table_name, column_name, expected_type)

    def assert_alembic_version(self, expected_revision: str) -> None:
        actual = self._get_alembic_version()
        assert actual == expected_revision, f"expected alembic_version '{expected_revision}', got '{actual}'"
        logger.info("Verified: alembic_version = %s", expected_revision)

    def _init_db_mixin(self) -> None:
        self._schema = os.environ.get("DB_SCHEMA", "public")
        self._state_key = os.environ.get("DEPLOY_STATE_KEY", "deploy_commit_sha")
        host = os.environ["DB_HOST"]
        port = os.environ["DB_PORT"]
        db_name = os.environ.get("DB_NAME", "dalembic_test")
        user = os.environ.get("DB_USER", "postgres")
        password = os.environ.get("DB_PASSWORD", "postgres")
        self._db_engine = create_engine(f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db_name}")
        try:
            with self._db_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception as exc:
            raise RuntimeError(
                f"Cannot connect to postgres at {host}:{port}. Run: docker compose up -d db"
            ) from exc
        self._reset_db()

    def _reset_db(self) -> None:
        with self._db_engine.begin() as conn:
            conn.execute(text(f"DROP SCHEMA IF EXISTS {self._schema} CASCADE"))
            conn.execute(text("DROP TABLE IF EXISTS alembic_version"))

    def _table_exists(self, table_name: str) -> bool:
        with self._db_engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema = :schema AND table_name = :table"
                ),
                {"schema": self._schema, "table": table_name},
            ).fetchone()
            return row is not None

    def _column_exists(self, table_name: str, column_name: str) -> bool:
        with self._db_engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT 1 FROM information_schema.columns "
                    "WHERE table_schema = :schema AND table_name = :table AND column_name = :column"
                ),
                {"schema": self._schema, "table": table_name, "column": column_name},
            ).fetchone()
            return row is not None

    def _get_column_type(self, table_name: str, column_name: str) -> str | None:
        with self._db_engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT data_type FROM information_schema.columns "
                    "WHERE table_schema = :schema AND table_name = :table AND column_name = :column"
                ),
                {"schema": self._schema, "table": table_name, "column": column_name},
            ).fetchone()
            return row[0] if row else None

    def _get_alembic_version(self) -> str | None:
        with self._db_engine.connect() as conn:
            row = conn.execute(text(f"SELECT version_num FROM {self._schema}.alembic_version")).fetchone()
            return row[0] if row else None

    def _get_stamped_sha(self) -> str | None:
        with self._db_engine.connect() as conn:
            row = conn.execute(
                text(f"SELECT data->>:key FROM {self._schema}.{TABLE_NAME} WHERE id = 'current'"),
                {"key": self._state_key},
            ).fetchone()
            return row[0] if row else None
