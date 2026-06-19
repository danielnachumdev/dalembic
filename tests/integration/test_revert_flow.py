"""Integration tests for revert_to() and ALEMBIC_REVERT_STAMP."""

import os

import pytest

from dalembic.testing.base import BaseDeployTest


class TestRevertAndReapply(BaseDeployTest):
    def test_revert_then_reapply(self) -> None:
        self.checkout_new_branch("test-revert")
        sha_v1 = self.head_sha()
        self.deploy(sha_v1)

        self.assert_table_exists("teams")
        self.assert_column_exists("tasks", "team_id")
        self.assert_table_exists("task_events")
        self.assert_alembic_version("0005")

        sha_v2 = self.commit_revert_migration(
            "0006_revert_to_0002.py",
            target="0002",
            from_revision="0005",
        )
        os.environ["ALEMBIC_REVERT_STAMP"] = "0002"
        try:
            self.deploy(sha_v2)
        finally:
            os.environ.pop("ALEMBIC_REVERT_STAMP", None)

        self.assert_table_exists("teams")
        self.assert_table_not_exists("tasks")
        self.assert_table_not_exists("task_events")
        self.assert_alembic_version("0002")

        sha_v3 = self.delete_and_commit("migrations/versions/0006_revert_to_0002.py")
        self.deploy(sha_v3)

        self.assert_table_exists("tasks")
        self.assert_column_exists("tasks", "team_id")
        self.assert_table_exists("task_events")
        self.assert_alembic_version("0005")


class TestRevertBlockedWithoutStamp(BaseDeployTest):
    def test_deploy_fails_without_stamp(self) -> None:
        self.checkout_new_branch("test-revert-safety")
        sha_v1 = self.head_sha()
        self.deploy(sha_v1)

        self.assert_table_exists("teams")
        self.assert_alembic_version("0005")

        sha_v2 = self.commit_revert_migration(
            "0006_revert_to_0002.py",
            target="0002",
            from_revision="0005",
        )
        os.environ.pop("ALEMBIC_REVERT_STAMP", None)

        with pytest.raises(RuntimeError):
            self.deploy(sha_v2)

        self.assert_table_exists("teams")
        self.assert_column_exists("tasks", "team_id")
        self.assert_alembic_version("0005")
