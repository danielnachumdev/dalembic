# AGENTS.md — dalembic package

## Purpose

Independent Python package for **Alembic deploy orchestration** (STG downgrade-before-upgrade, prod upgrade, reverts, deploy state).

**PyPI / import:** `dalembic`  
**CLI:** `dalembic` → `dalembic.cli:main` (also `python -m dalembic`)  
**GitHub:** https://github.com/danielnachumdev/dalembic

## Public API

Stable exports from `dalembic/__init__.py`:

- `DeploySettings` — configuration dataclass + `from_env()`
- `DeploymentManager` — STG/PROD deploy orchestration
- `MigrationArchive` — git archive of prior commit migrations
- `StateStore` — Postgres JSONB deploy SHA storage (STG)
- `revert_to` — programmatic revert via `downgrade()` chain

Additional public modules:

- `dalembic.connection.DatabaseConnection`
- `dalembic.runtime` — `to_sync_database_url`, `upgrade_head`, `configure_alembic_console_logging`
- `dalembic.seeds.DataLoader`
- `dalembic.testing` — integration test kit (`BaseDeployTest`, mixins)

## Private / internal

Modules without leading underscores are still **library internals** unless listed above. Do not rely on undocumented helpers.

## Running tests

```bash
uv sync --all-extras
uv run ruff check dalembic tests
uv run pytest tests/unit -q

# Integration (Postgres on :5433)
docker compose up -d
uv run pytest tests/integration -q
```

Integration tests copy `tests/fixtures/taskboard_app/` into a temp git repo — no side effects on the working tree.

## Behavioral spec

STG deploy semantics:

1. Require `CI_COMMIT_SHA` + `ALEMBIC_HEAD_REVISION_MAIN`
2. Read previous SHA from `StateStore`
3. If reachable → archive prior migrations → downgrade to main head
4. Upgrade to branch head
5. Stamp commit SHA
6. Optional `ALEMBIC_REVERT_STAMP` → `alembic stamp`

## Conventions

- Python `>=3.11`, line length 120
- All migration paths/schema via `DeploySettings` — no static global config
- Consumer migrations: `from dalembic.revert import revert_to`
- Postgres required for `StateStore` (JSONB)
- Revision IDs: zero-padded numeric strings (`0001`, `0002`, …) for string comparison in downgrade skip logic

## Contributing

- Run `ruff` and `pytest` before pushing
- Do not merge via automation without human review
