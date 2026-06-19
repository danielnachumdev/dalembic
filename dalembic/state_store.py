from __future__ import annotations

import json
import logging

from sqlalchemy import text

from dalembic.connection import DatabaseConnection
from dalembic.settings import DeploySettings

logger = logging.getLogger(__name__)


class StateStore:
    """Key-value deploy metadata in a Postgres JSONB singleton row."""

    def __init__(self, settings: DeploySettings) -> None:
        self._settings = settings
        self._connection = DatabaseConnection(settings)
        self._engine = self._connection.create_engine()
        self._table = f"{settings.schema}.{settings.state_table}"
        self._ensure_table()

    def _ensure_table(self) -> None:
        schema = self._settings.schema
        table = self._settings.state_table
        row_id = self._settings.state_row_id
        with self._engine.begin() as conn:
            conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
            conn.execute(
                text(
                    f"""
                CREATE TABLE IF NOT EXISTS {schema}.{table} (
                    id TEXT PRIMARY KEY,
                    data JSONB NOT NULL DEFAULT '{{}}'::jsonb,
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """
                )
            )
            conn.execute(
                text(
                    f"""
                INSERT INTO {schema}.{table} (id, data) VALUES (:id, '{{}}'::jsonb)
                ON CONFLICT (id) DO NOTHING
            """
                ),
                {"id": row_id},
            )

    def get(self, key: str) -> str | None:
        row_id = self._settings.state_row_id
        with self._engine.connect() as conn:
            row = conn.execute(
                text(f"SELECT data->>:key FROM {self._table} WHERE id = :id"),
                {"key": key, "id": row_id},
            ).fetchone()
            return row[0] if row else None

    def set(self, key: str, value: str) -> None:
        row_id = self._settings.state_row_id
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    f"""
                    UPDATE {self._table}
                    SET data = jsonb_set(data, :path, CAST(:value AS jsonb)), updated_at = NOW()
                    WHERE id = :id
                """
                ),
                {"path": f"{{{key}}}", "value": json.dumps(value), "id": row_id},
            )
