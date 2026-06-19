"""Programmatic migration revert via downgrade() calls."""

from __future__ import annotations

import importlib.util
import logging
import os
from pathlib import Path
from types import ModuleType

from dalembic.settings import DeploySettings

logger = logging.getLogger(__name__)


def _load_revision_chain(versions_dir: Path, target: str, start: str | None = None) -> list[ModuleType]:
    modules: dict[str, ModuleType] = {}
    for path in versions_dir.glob("*.py"):
        if path.name.startswith("_"):
            continue
        spec = importlib.util.spec_from_file_location(path.stem, path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Failed to load migration module: {path}")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        modules[mod.revision] = mod

    if start:
        if start not in modules:
            raise RuntimeError(f"Start revision {start!r} not found")
        current = start
    else:
        all_revisions = set(modules.keys())
        downstream = {m.down_revision for m in modules.values() if m.down_revision}
        heads = all_revisions - downstream
        if len(heads) != 1:
            raise RuntimeError(f"Expected exactly one head revision, found: {heads}")
        current = heads.pop()

    chain: list[ModuleType] = []
    while current != target:
        chain.append(modules[current])
        current = modules[current].down_revision
        if current is None:
            raise RuntimeError(f"Target revision {target!r} not found in chain")

    return chain


def revert_to(
    target: str,
    from_revision: str | None = None,
    *,
    settings: DeploySettings | None = None,
    versions_dir: Path | None = None,
) -> None:
    """Run downgrade() from from_revision down to target (exclusive)."""
    if not os.environ.get("ALEMBIC_REVERT_STAMP"):
        raise RuntimeError(
            "ALEMBIC_REVERT_STAMP env var must be set when running a revert migration. "
            "This ensures alembic_version is stamped to the target revision after upgrade."
        )

    resolved_settings = settings or DeploySettings.from_env()
    resolved_versions = versions_dir or resolved_settings.versions_path
    chain = _load_revision_chain(resolved_versions, target, start=from_revision)
    for mod in chain:
        logger.info("Reverting %s (%s)", mod.revision, mod.__name__)
        mod.downgrade()
    logger.info("Reverted to %s (%s migrations undone)", target, len(chain))
