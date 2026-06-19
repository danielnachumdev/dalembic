from __future__ import annotations

import os

import pytest

from dalembic.connection import DatabaseConnection
from dalembic.settings import DeploySettings


def _settings(**kwargs: object) -> DeploySettings:
    defaults = {
        "env": "prod",
        "database_url": None,
        "db_host": "localhost",
        "db_port": "5432",
        "db_name": "mydb",
        "db_user": "user",
        "db_password": "secret",
    }
    defaults.update(kwargs)
    return DeploySettings(**defaults)  # type: ignore[arg-type]


def test_build_url_from_components() -> None:
    conn = DatabaseConnection(_settings())
    assert conn.build_url() == "postgresql+psycopg://user:secret@localhost:5432/mydb"


def test_build_url_from_database_url_override() -> None:
    conn = DatabaseConnection(_settings(database_url="postgresql+psycopg://override/db"))
    assert conn.build_url() == "postgresql+psycopg://override/db"


def test_build_connect_args_empty_without_ssl() -> None:
    conn = DatabaseConnection(_settings())
    assert conn.build_connect_args() == {}


def test_build_connect_args_from_db_ssl_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DB_SSL_SERVER_CA", "ca-content")
    monkeypatch.setenv("DB_SSL_CLIENT_CERT", "cert-content")
    monkeypatch.setenv("DB_SSL_CLIENT_KEY", "a2V5")  # base64 "key"

    conn = DatabaseConnection(_settings())
    args = conn.build_connect_args()

    assert args["sslmode"] == "verify-ca"
    assert os.path.isfile(args["sslrootcert"])
    assert os.path.isfile(args["sslcert"])
    assert os.path.isfile(args["sslkey"])


def test_build_connect_args_liquibase_aliases(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DB_SSL_SERVER_CA", raising=False)
    monkeypatch.setenv("LIQUIBASE_COMMAND_SERVER_CA", "ca-content")
    monkeypatch.setenv("LIQUIBASE_COMMAND_CLIENT_CERT", "cert-content")
    monkeypatch.setenv("LIQUIBASE_COMMAND_CLIENT_KEY", "a2V5")

    conn = DatabaseConnection(_settings())
    args = conn.build_connect_args()

    assert args["sslmode"] == "verify-ca"
