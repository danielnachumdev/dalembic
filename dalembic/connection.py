from __future__ import annotations

import base64
import os
import stat
import tempfile
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from dalembic.settings import DeploySettings


class DatabaseConnection:
    """Build SQLAlchemy URLs and run simple queries."""

    def __init__(self, settings: DeploySettings) -> None:
        self._settings = settings

    def build_url(self) -> str:
        if self._settings.database_url:
            return self._settings.database_url
        s = self._settings
        return f"postgresql+psycopg://{s.db_user}:{s.db_password}@{s.db_host}:{s.db_port}/{s.db_name}"

    def build_connect_args(self) -> dict[str, Any]:
        """SSL connect_args from env certs. Returns {} when certs are unset (local dev)."""
        server_ca = _first_env("DB_SSL_SERVER_CA", "LIQUIBASE_COMMAND_SERVER_CA")
        client_cert = _first_env("DB_SSL_CLIENT_CERT", "LIQUIBASE_COMMAND_CLIENT_CERT")
        client_key_b64 = _first_env("DB_SSL_CLIENT_KEY", "LIQUIBASE_COMMAND_CLIENT_KEY")
        if not all([server_ca, client_cert, client_key_b64]):
            return {}

        ca_path = _write_temp(server_ca.encode(), ".pem")
        cert_path = _write_temp(client_cert.encode(), ".pem")
        key_path = _write_temp(_der_to_pem(base64.b64decode(client_key_b64)), ".pem")
        return {
            "sslmode": "verify-ca",
            "sslrootcert": ca_path,
            "sslcert": cert_path,
            "sslkey": key_path,
        }

    def create_engine(self) -> Engine:
        return create_engine(self.build_url(), connect_args=self.build_connect_args())

    def query_scalar(self, sql: str, params: dict[str, Any] | None = None) -> Any:
        engine = self.create_engine()
        try:
            with engine.connect() as conn:
                row = conn.execute(text(sql), params or {}).fetchone()
                return row[0] if row else None
        finally:
            engine.dispose()


def _first_env(*names: str) -> str:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return ""


def _der_to_pem(der_bytes: bytes) -> bytes:
    return b"-----BEGIN PRIVATE KEY-----\n" + base64.encodebytes(der_bytes) + b"-----END PRIVATE KEY-----\n"


def _write_temp(content: bytes, suffix: str) -> str:
    f = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    f.write(content)
    f.close()
    os.chmod(f.name, stat.S_IRUSR | stat.S_IWUSR)
    return f.name
