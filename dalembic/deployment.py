from __future__ import annotations

import logging
import subprocess

from dalembic.archive import MigrationArchive
from dalembic.connection import DatabaseConnection
from dalembic.settings import DeploySettings
from dalembic.state_store import StateStore

logger = logging.getLogger(__name__)


class DeploymentManager:
    """Orchestrate STG downgrade-before-upgrade or PROD upgrade-to-head."""

    def __init__(self, settings: DeploySettings) -> None:
        self._settings = settings
        self._connection = DatabaseConnection(settings)
        self._state = StateStore(settings) if settings.env == "stg" else None

    def deploy(self) -> None:
        if self._settings.env == "stg":
            self._deploy_stg()
        elif self._settings.env == "prod":
            self._deploy_prod()
        else:
            raise RuntimeError(f"Unknown ENV {self._settings.env!r}. Use 'stg' or 'prod'.")

        if self._settings.revert_stamp:
            self._stamp_revision(self._settings.revert_stamp)

        logger.info("Done.")

    def _deploy_stg(self) -> None:
        if not self._settings.commit_sha or not self._settings.main_head_revision:
            raise RuntimeError("CI_COMMIT_SHA and ALEMBIC_HEAD_REVISION_MAIN are required for STG deploys")

        assert self._state is not None
        prev_sha = self._state.get(self._settings.state_key)
        logger.info(
            "Current SHA: %s, previous STG SHA: %s",
            self._settings.commit_sha,
            prev_sha or "none",
        )

        if not prev_sha:
            logger.info("No previous deploy — first deploy.")
        elif prev_sha == self._settings.commit_sha:
            logger.info("Same commit as previous deploy")
        elif self._commit_exists(prev_sha):
            logger.info("Previous commit %s is reachable — downgrading before upgrade.", prev_sha)
            self._downgrade_previous_commit(prev_sha)
        else:
            logger.warning(
                "Previous commit %s is unreachable — skipping downgrade, attempting upgrade directly.",
                prev_sha,
            )

        try:
            self._upgrade()
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                "Upgrade failed. Possible causes:\n"
                "  1. Branch is not rebased on main — rebase and redeploy.\n"
                "  2. A previous branch was closed without merging, leaving an orphaned revision\n"
                "     in the DB. Fix: run 'alembic stamp <main_head>' and drop orphaned tables."
            ) from e

        self._stamp_sha(self._settings.commit_sha)

    def _deploy_prod(self) -> None:
        logger.info("Prod deploy: upgrading to head.")
        self._run(["alembic", "upgrade", "head"])

    def _downgrade_previous_commit(self, prev_sha: str) -> None:
        current = self._get_current_revision()
        target = self._settings.main_head_revision
        assert target is not None
        if current and current <= target:
            logger.info("DB at %s, already at or below %s — skipping downgrade.", current, target)
            return

        archive = MigrationArchive(prev_sha, self._settings)
        archive.extract()
        try:
            logger.info("Downgrading to main head (%s) using %s's migrations.", target, prev_sha)
            self._run(["alembic", "-c", archive.alembic_ini, "downgrade", target], cwd=archive.path)
        finally:
            archive.cleanup()

    def _get_current_revision(self) -> str | None:
        schema = self._settings.schema
        try:
            return self._connection.query_scalar(f"SELECT version_num FROM {schema}.alembic_version")
        except Exception:
            return None

    def _upgrade(self) -> None:
        logger.info("Upgrading to branch head.")
        self._run(["alembic", "upgrade", "head"], cwd=str(self._settings.repo_root))

    def _stamp_sha(self, sha: str) -> None:
        assert self._state is not None
        self._state.set(self._settings.state_key, sha)
        logger.info("Stamped app_state with SHA %s.", sha)

    def _stamp_revision(self, revision: str) -> None:
        logger.info("Stamping alembic_version to %s (ALEMBIC_REVERT_STAMP override).", revision)
        subprocess.run(
            ["alembic", "stamp", revision],
            check=True,
            cwd=str(self._settings.repo_root),
        )

    @staticmethod
    def _commit_exists(sha: str) -> bool:
        result = subprocess.run(["git", "cat-file", "-t", sha], capture_output=True, text=True)
        return result.returncode == 0 and result.stdout.strip() == "commit"

    def _run(self, cmd: list[str], cwd: str | None = None) -> None:
        logger.info("Running: %s", " ".join(cmd))
        subprocess.run(cmd, check=True, cwd=cwd or str(self._settings.repo_root))
