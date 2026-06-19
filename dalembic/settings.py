from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

DeployEnv = Literal["stg", "prod"]


def _env_bool(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes"}


@dataclass
class DeploySettings:
    """Configuration for deploy orchestration and DB access."""

    env: DeployEnv
    schema: str = "public"
    repo_root: Path = field(default_factory=Path.cwd)
    migrations_subpath: str = "migrations"
    versions_subpath: str = "versions"
    state_key: str = "deploy_commit_sha"
    state_row_id: str = "current"
    commit_sha: str | None = None
    main_head_revision: str | None = None
    revert_stamp: str | None = None
    local_dev: bool = False
    database_url: str | None = None
    db_host: str = "localhost"
    db_port: str = "5432"
    db_name: str = "postgres"
    db_user: str = "postgres"
    db_password: str = "postgres"
    seed_dir: Path | None = None

    @property
    def migrations_path(self) -> Path:
        return self.repo_root / self.migrations_subpath

    @property
    def versions_path(self) -> Path:
        return self.migrations_path / self.versions_subpath

    @property
    def alembic_ini(self) -> Path:
        return self.repo_root / "alembic.ini"

    def is_deployed(self) -> bool:
        """Return True unless LOCAL_DEV-style local-only mode is enabled."""
        return not self.local_dev

    @classmethod
    def from_env(cls, repo_root: Path | None = None) -> DeploySettings:
        """Build settings from environment variables."""
        root = Path(repo_root or os.environ.get("REPO_ROOT", Path.cwd()))
        env_raw = (os.environ.get("ENV") or "").strip().lower()
        if env_raw not in ("stg", "prod"):
            raise RuntimeError(f"ENV must be 'stg' or 'prod', got {env_raw!r}")

        seed_raw = os.environ.get("SEED_DIR", "").strip()
        seed_dir = Path(seed_raw) if seed_raw else None

        return cls(
            env=env_raw,  # type: ignore[arg-type]
            schema=os.environ.get("DB_SCHEMA", "public"),
            repo_root=root,
            migrations_subpath=os.environ.get("MIGRATIONS_SUBPATH", "migrations"),
            versions_subpath=os.environ.get("VERSIONS_SUBPATH", "versions"),
            state_key=os.environ.get("DEPLOY_STATE_KEY", "deploy_commit_sha"),
            commit_sha=os.environ.get("CI_COMMIT_SHA") or os.environ.get("COMMIT_SHA"),
            main_head_revision=os.environ.get("ALEMBIC_HEAD_REVISION_MAIN"),
            revert_stamp=os.environ.get("ALEMBIC_REVERT_STAMP"),
            local_dev=_env_bool("LOCAL_DEV"),
            database_url=os.environ.get("DATABASE_URL") or None,
            db_host=os.environ.get("DB_HOST", "localhost"),
            db_port=os.environ.get("DB_PORT", "5432"),
            db_name=os.environ.get("DB_NAME", "postgres"),
            db_user=os.environ.get("DB_USER", "postgres"),
            db_password=os.environ.get("DB_PASSWORD", "postgres"),
            seed_dir=seed_dir,
        )
