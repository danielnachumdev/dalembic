"""Integration tests for the STG deploy downgrade/upgrade flow."""

from dalembic.testing.base import BaseDeployTest


class TestFirstDeploy(BaseDeployTest):
    def test_stamps_sha_on_first_deploy(self) -> None:
        self.checkout_new_branch("test-first-deploy")
        sha = self.head_sha()

        self.deploy(sha)

        self.assert_stamped_sha(sha)
        self.assert_table_exists("deploy_audit")
        self.assert_table_exists("teams")
        self.assert_table_exists("tasks")


class TestSameDevModifiedMigration(BaseDeployTest):
    def test_old_table_removed_new_table_created(self) -> None:
        self.checkout_new_branch("test-same-dev")

        sha_v1 = self.commit_migration("0006_test.py", "sprint_alpha", ["name"])
        self.deploy(sha_v1)
        self.assert_table_exists("sprint_alpha")

        sha_v2 = self.commit_migration("0006_test.py", "sprint_beta", ["score", "category"])
        self.deploy(sha_v2)

        self.assert_table_not_exists("sprint_alpha")
        self.assert_table_exists("sprint_beta")
        self.assert_stamped_sha(sha_v2)


class TestDifferentDevsDifferentMigrations(BaseDeployTest):
    def test_dev1_table_removed_dev2_table_created(self) -> None:
        self.checkout_new_branch("test-dev1")
        sha_dev1 = self.commit_migration("0006_dev1.py", "lane_one", ["label"])
        self.deploy(sha_dev1)
        self.assert_table_exists("lane_one")

        self.checkout_base()
        self.checkout_new_branch("test-dev2")
        sha_dev2 = self.commit_migration("0006_dev2.py", "lane_two", ["value"])
        self.deploy(sha_dev2)

        self.assert_table_not_exists("lane_one")
        self.assert_table_exists("lane_two")
        self.assert_stamped_sha(sha_dev2)
