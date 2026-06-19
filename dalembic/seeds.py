from __future__ import annotations

import csv

from alembic import op
from sqlalchemy import text

from dalembic.settings import DeploySettings


class DataLoader:
    """Load CSV seed files into migrations (guarded by is_deployed())."""

    def __init__(self, settings: DeploySettings) -> None:
        self._settings = settings

    def load_csv(self, revision: str, table: str) -> list[dict[str, str]]:
        seed_dir = self._settings.seed_dir
        if seed_dir is None:
            raise RuntimeError("seed_dir is not configured on DeploySettings")
        path = seed_dir / f"{revision}_{table}.csv"
        with path.open(newline="") as f:
            return list(csv.DictReader(f))

    def insert_row(self, table: str, row: dict[str, str]) -> None:
        schema = self._settings.schema
        cols = ", ".join(row.keys())
        placeholders = ", ".join(f":{k}" for k in row.keys())
        cleaned = {k: (None if v == "" else v) for k, v in row.items()}
        op.get_bind().execute(
            text(f"INSERT INTO {schema}.{table} ({cols}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"),
            cleaned,
        )
