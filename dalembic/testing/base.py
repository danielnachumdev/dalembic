"""Base class for deploy integration tests."""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

from dalembic.deployment import DeploymentManager
from dalembic.settings import DeploySettings
from dalembic.testing.db_mixin import DbMixin
from dalembic.testing.git_mixin import GitMixin

logger = logging.getLogger(__name__)

FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "taskboard_app"


class BaseDeployTest(GitMixin, DbMixin):
    """Fresh fixture git repo + Postgres per test method."""

    _original_env: dict[str, str]
    _migrations_dir: Path
    _main_head_rev: str

    def setup_method(self) -> None:
        self._original_env = os.environ.copy()
        self._init_git_mixin(FIXTURE_ROOT)
        self._migrations_dir = self._workdir / "migrations" / "versions"
        self._configure_env()
        self._init_db_mixin()

    def teardown_method(self) -> None:
        logger.info("Cleaning up: resetting DB and removing temp workdir")
        self._reset_db()
        self._db_engine.dispose()
        shutil.rmtree(self._workdir, ignore_errors=True)
        os.environ.clear()
        os.environ.update(self._original_env)

    def commit_migration(self, filename: str, table_name: str, columns: list[str]) -> str:
        self._write_migration_file(filename, table_name, columns)
        self.git("add", str(self._migrations_dir / filename))
        self.git("commit", "-m", f"test: add {table_name}")
        sha = self.head_sha()
        logger.info("Committed migration %s (%s) → %s", filename, table_name, sha)
        return sha

    def commit_revert_migration(self, filename: str, target: str, from_revision: str) -> str:
        self._write_revert_migration_file(filename, target, from_revision)
        self.git("add", str(self._migrations_dir / filename))
        self.git("commit", "-m", f"test: revert to {target}")
        sha = self.head_sha()
        logger.info("Committed revert migration %s (target=%s) → %s", filename, target, sha)
        return sha

    def deploy(self, commit_sha: str) -> None:
        logger.info("Deploying SHA %s", commit_sha)
        os.environ["CI_COMMIT_SHA"] = commit_sha
        original_cwd = os.getcwd()
        os.chdir(self._workdir)
        try:
            settings = DeploySettings.from_env(repo_root=self._workdir)
            DeploymentManager(settings).deploy()
        finally:
            os.chdir(original_cwd)

    def _configure_env(self) -> None:
        self._main_head_rev = self._resolve_main_head()
        os.environ.update(
            {
                "DB_HOST": os.environ.get("DB_HOST", "localhost"),
                "DB_PORT": os.environ.get("DB_PORT", "5433"),
                "DB_NAME": os.environ.get("DB_NAME", "dalembic_test"),
                "DB_USER": os.environ.get("DB_USER", "postgres"),
                "DB_PASSWORD": os.environ.get("DB_PASSWORD", "postgres"),
                "DB_SCHEMA": os.environ.get("DB_SCHEMA", "public"),
                "ENV": "stg",
                "LOCAL_DEV": "true",
                "ALEMBIC_HEAD_REVISION_MAIN": self._main_head_rev,
                "CI_COMMIT_SHA": "placeholder",
                "REPO_ROOT": str(self._workdir),
                "PATH": os.pathsep.join(
                    p for p in (os.environ.get("PATH", "").split(os.pathsep)) if "dalembic-deploy-test-" not in p
                ),
            }
        )

    def _write_migration_file(self, filename: str, table_name: str, columns: list[str]) -> None:
        down_rev = self._main_head_rev
        next_rev = str(int(down_rev) + 1).zfill(4)
        col_lines = ['        sa.Column("id", sa.Integer(), primary_key=True),']
        for col in columns:
            col_lines.append(f'        sa.Column("{col}", sa.Text()),')
        col_block = "\n".join(col_lines)
        schema = os.environ.get("DB_SCHEMA", "public")

        content = (
            f"from alembic import op\n"
            f"import sqlalchemy as sa\n"
            f"\n"
            f'revision = "{next_rev}"\n'
            f'down_revision = "{down_rev}"\n'
            f"branch_labels = None\n"
            f"depends_on = None\n"
            f"\n"
            f'SCHEMA = "{schema}"\n'
            f"\n"
            f"def upgrade() -> None:\n"
            f"    op.create_table(\n"
            f'        "{table_name}",\n'
            f"{col_block}\n"
            f"        schema=SCHEMA,\n"
            f"    )\n"
            f"\n"
            f"def downgrade() -> None:\n"
            f'    op.drop_table("{table_name}", schema=SCHEMA)\n'
        )
        (self._migrations_dir / filename).write_text(content)

    def _write_revert_migration_file(self, filename: str, target: str, from_revision: str) -> None:
        next_rev = str(int(from_revision) + 1).zfill(4)
        content = (
            f"from dalembic.revert import revert_to\n"
            f"\n"
            f'revision = "{next_rev}"\n'
            f'down_revision = "{from_revision}"\n'
            f"branch_labels = None\n"
            f"depends_on = None\n"
            f"\n"
            f"def upgrade() -> None:\n"
            f'    revert_to("{target}", from_revision="{from_revision}")\n'
            f"\n"
            f"def downgrade() -> None:\n"
            f"    pass\n"
        )
        (self._migrations_dir / filename).write_text(content)

    def _resolve_main_head(self) -> str:
        files = sorted(f.name for f in self._migrations_dir.iterdir() if f.suffix == ".py" and f.name[0].isdigit())
        return files[-1].split("_")[0]
