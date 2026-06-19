from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


class GitMixin:
    """Git operations on a temp copy of a fixture project."""

    _workdir: Path
    _base_sha: str

    def checkout_new_branch(self, name: str) -> None:
        logger.info("Creating branch: %s", name)
        self.git("checkout", "-b", name)

    def checkout_base(self) -> None:
        logger.info("Switching back to base: %s", self._base_sha)
        self.git("checkout", self._base_sha)

    def head_sha(self) -> str:
        return self.git("rev-parse", "HEAD")

    def delete_and_commit(self, filepath: str) -> str:
        self.git("rm", filepath)
        self.git("commit", "-m", f"test: delete {filepath}")
        sha = self.head_sha()
        logger.info("Deleted %s → %s", filepath, sha)
        return sha

    def git(self, *args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            check=True,
            cwd=self._workdir,
            stdout=subprocess.PIPE,
            text=True,
        )
        return result.stdout.strip()

    def _init_git_mixin(self, fixture_root: Path) -> None:
        self._workdir = Path(tempfile.mkdtemp(prefix="dalembic-deploy-test-"))
        logger.info("Copying fixture from %s to %s", fixture_root, self._workdir)
        shutil.copytree(fixture_root, self._workdir, dirs_exist_ok=True)
        self.git("init")
        self.git("add", ".")
        self.git("commit", "-m", "test: baseline fixture")
        self.git("config", "user.email", "test@test.com")
        self.git("config", "user.name", "test")
        self._base_sha = self.head_sha()
