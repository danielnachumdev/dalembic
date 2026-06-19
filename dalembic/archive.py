from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

from dalembic.settings import DeploySettings

logger = logging.getLogger(__name__)


class MigrationArchive:
    """Extract a previous commit's migrations tree from git into a temp directory."""

    def __init__(self, commit_sha: str, settings: DeploySettings) -> None:
        self._sha = commit_sha
        self._settings = settings
        self._tmpdir: Path | None = None

    @property
    def alembic_ini(self) -> str:
        return str(self._require_tmpdir() / "alembic.ini")

    @property
    def path(self) -> str:
        return str(self._require_tmpdir())

    def _require_tmpdir(self) -> Path:
        if self._tmpdir is None:
            raise RuntimeError("MigrationArchive.extract() must be called before accessing path or alembic_ini")
        return self._tmpdir

    def extract(self) -> None:
        self._tmpdir = Path(tempfile.mkdtemp(prefix="dalembic-prev-"))
        archive_path = f"{self._settings.migrations_subpath}/"
        logger.info("Extracting migrations from %s (%s) to %s", self._sha, archive_path, self._tmpdir)
        proc = subprocess.run(
            ["git", "archive", self._sha, archive_path, "alembic.ini"],
            stdout=subprocess.PIPE,
            check=True,
            cwd=self._settings.repo_root,
        )
        subprocess.run(["tar", "-x", "-C", str(self._tmpdir)], input=proc.stdout, check=True)

    def cleanup(self) -> None:
        if self._tmpdir:
            shutil.rmtree(self._tmpdir, ignore_errors=True)
            self._tmpdir = None
