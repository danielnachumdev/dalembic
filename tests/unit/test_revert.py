from __future__ import annotations

from pathlib import Path

import pytest

from dalembic.revert import revert_to


def _write_migration(
    path: Path,
    revision: str,
    down_revision: str | None,
    log_path: Path,
) -> None:
    down = "None" if down_revision is None else f'"{down_revision}"'
    content = (
        f"from pathlib import Path\n"
        f"\n"
        f'revision = "{revision}"\n'
        f"down_revision = {down}\n"
        f"branch_labels = None\n"
        f"depends_on = None\n"
        f"\n"
        f"LOG = Path({str(log_path)!r})\n"
        f"\n"
        f"def upgrade() -> None:\n"
        f"    pass\n"
        f"\n"
        f"def downgrade() -> None:\n"
        f'    LOG.write_text(LOG.read_text() + "{revision}\\n" if LOG.exists() else "{revision}\\n")\n'
    )
    path.write_text(content)


def test_revert_to_calls_downgrades_in_order(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    versions = tmp_path / "versions"
    versions.mkdir()
    log_path = tmp_path / "downgrade.log"
    _write_migration(versions / "0001.py", "0001", None, log_path)
    _write_migration(versions / "0002.py", "0002", "0001", log_path)
    _write_migration(versions / "0003.py", "0003", "0002", log_path)

    monkeypatch.setenv("ENV", "prod")
    monkeypatch.setenv("ALEMBIC_REVERT_STAMP", "0001")

    revert_to("0001", from_revision="0003", versions_dir=versions)

    assert log_path.read_text() == "0003\n0002\n"


def test_revert_to_raises_without_stamp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    versions = tmp_path / "versions"
    versions.mkdir()
    log_path = tmp_path / "downgrade.log"
    _write_migration(versions / "0001.py", "0001", None, log_path)
    _write_migration(versions / "0002.py", "0002", "0001", log_path)

    monkeypatch.setenv("ENV", "prod")
    monkeypatch.delenv("ALEMBIC_REVERT_STAMP", raising=False)

    with pytest.raises(RuntimeError, match="ALEMBIC_REVERT_STAMP"):
        revert_to("0001", from_revision="0002", versions_dir=versions)
