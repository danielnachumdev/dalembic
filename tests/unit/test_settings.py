from __future__ import annotations

from pathlib import Path

import pytest

from dalembic.settings import DeploySettings


def test_from_env_parses_stg_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "stg")
    monkeypatch.setenv("DB_HOST", "db.example.com")
    monkeypatch.setenv("DB_PORT", "5433")
    monkeypatch.setenv("ALEMBIC_HEAD_REVISION_MAIN", "0005")
    monkeypatch.setenv("CI_COMMIT_SHA", "abc123")

    settings = DeploySettings.from_env(repo_root=Path("/app"))

    assert settings.env == "stg"
    assert settings.db_host == "db.example.com"
    assert settings.db_port == "5433"
    assert settings.main_head_revision == "0005"
    assert settings.commit_sha == "abc123"
    assert settings.repo_root == Path("/app")


def test_is_deployed_false_when_local_dev(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "prod")
    monkeypatch.setenv("LOCAL_DEV", "true")

    settings = DeploySettings.from_env()

    assert settings.is_deployed() is False


def test_migrations_path_with_custom_subpath(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "prod")
    monkeypatch.setenv("MIGRATIONS_SUBPATH", "alembic")
    monkeypatch.setenv("VERSIONS_SUBPATH", "versions")

    settings = DeploySettings.from_env(repo_root=Path("/repo"))

    assert settings.migrations_path == Path("/repo/alembic")
    assert settings.versions_path == Path("/repo/alembic/versions")


def test_from_env_rejects_invalid_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "dev")

    with pytest.raises(RuntimeError, match="ENV must be"):
        DeploySettings.from_env()
