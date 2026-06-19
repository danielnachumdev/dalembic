"""Publish dalembic to PyPI via quickpub."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import fire
from quickpub import (
    LicenseEnforcer,
    LocalVersionEnforcer,
    PypircEnforcer,
    PypircUploadTarget,
    PytestRunner,
    ReadmeEnforcer,
    SetuptoolsBuildSchema,
    publish,
)

from dalembic.cli import main as dalembic_cli_main

PYPROJECT_BACKUP = Path(".pyproject.toml.bak")
GENERATED_PATHS = ("setup.py", "MANIFEST.in", "quickpub.egg-info")
_VERSION_REGEX = __import__("re").compile(r"^\d+\.\d+\.\d+$")


def _patch_quickpub_pip_list() -> None:
    """Use the active venv's pip list; quickpub's default `pip` may hit the wrong interpreter."""
    import quickpub.qa as qa_module
    from quickpub.structures import Dependency, Version

    async def _get_installed_packages(_executor: object, _env_name: str) -> dict[str, Dependency | str]:
        proc = subprocess.run(
            [sys.executable, "-m", "pip", "list"],
            capture_output=True,
            text=True,
            check=True,
        )
        currently_installed: dict[str, Dependency | str] = {}
        for line in proc.stdout.splitlines()[2:]:
            parts = line.split()
            if len(parts) < 2:
                continue
            name, ver = parts[0], parts[1]
            key = name.lower()
            if _VERSION_REGEX.match(ver):
                currently_installed[key] = Dependency(name, "==", Version.from_str(ver))
            else:
                currently_installed[key] = ver
        if "psycopg" in currently_installed:
            currently_installed["psycopg[binary]"] = currently_installed["psycopg"]
        return currently_installed

    qa_module._get_installed_packages = _get_installed_packages


def _ensure_pip() -> None:
    try:
        import pip  # noqa: F401
    except ImportError:
        subprocess.run([sys.executable, "-m", "ensurepip", "--upgrade"], check=True)


def _read_version() -> str:
    with Path("pyproject.toml").open("rb") as f:
        return tomllib.load(f)["project"]["version"]


def _ensure_pypirc() -> None:
    if Path(".pypirc").exists():
        return
    token = os.environ.get("PYPI_API_TOKEN")
    if not token:
        return
    Path(".pypirc").write_text(
        "[distutils]\n"
        "index-servers =\n"
        "    pypi\n"
        "    testpypi\n\n"
        "[pypi]\n"
        "username = __token__\n"
        f"password = {token}\n\n"
        "[testpypi]\n"
        "username = __token__\n"
        f"password = {token}\n",
        encoding="utf-8",
    )


def _backup_pyproject() -> None:
    shutil.copy("pyproject.toml", PYPROJECT_BACKUP)


def _restore_pyproject() -> None:
    if PYPROJECT_BACKUP.exists():
        shutil.move(PYPROJECT_BACKUP, "pyproject.toml")


def _cleanup_generated() -> None:
    for name in GENERATED_PATHS:
        path = Path(name)
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        elif path.exists():
            path.unlink()


def main(*, demo: bool = False) -> None:
    _ensure_pip()
    _patch_quickpub_pip_list()
    _ensure_pypirc()
    _backup_pyproject()
    enforcers = [
        ReadmeEnforcer(),
        LicenseEnforcer(),
        LocalVersionEnforcer(),
    ]
    if not demo:
        enforcers.insert(0, PypircEnforcer())
    try:
        publish(
            name="dalembic",
            version=_read_version(),
            author="Daniel Nachum",
            author_email="danielnachumdev@gmail.com",
            description=(
                "Branch-aware Alembic deployment: STG downgrade-to-main, "
                "prod upgrade-to-head, reverts, and deploy state."
            ),
            homepage="https://github.com/danielnachumdev/dalembic",
            min_python="3.11.0",
            keywords=["alembic", "migrations", "database", "deploy", "postgresql"],
            dependencies=[
                "alembic>=1.13",
                "sqlalchemy>=2.0",
                "psycopg[binary]>=3.1",
            ],
            scripts={"dalembic": dalembic_cli_main},
            global_quality_assurance_runners=[
                PytestRunner(bound=">=0.95", target="./tests/unit"),
            ],
            build_schemas=[SetuptoolsBuildSchema()],
            upload_targets=[] if demo else [PypircUploadTarget()],
            enforcers=enforcers,
            demo=demo,
        )
    finally:
        _restore_pyproject()
        _cleanup_generated()


if __name__ == "__main__":
    fire.Fire(main)
