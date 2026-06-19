# dalembic

**Branch-aware Alembic deployment:** STG downgrade-to-main, prod upgrade-to-head, reverts, and deploy state.

> **Not SQLAlchemy Alembic.** SQLAlchemy's tool is `import alembic` / `alembic upgrade head`. This package is `import dalembic` / `dalembic` (deploy orchestration). Different names, different binaries.

## Install

```bash
uv add dalembic
# or
pip install dalembic
```

## Quick start

From a repo with `alembic.ini` and migrations:

```bash
export ENV=prod
export DB_HOST=localhost DB_PORT=5432 DB_NAME=mydb DB_USER=postgres DB_PASSWORD=secret
dalembic
```

STG deploys require `ENV=stg`, `CI_COMMIT_SHA`, and `ALEMBIC_HEAD_REVISION_MAIN` (main's head revision).

## Deploy modes

| Mode | Behavior |
|------|----------|
| **STG** (`ENV=stg`) | Read previous deploy SHA from Postgres → optionally downgrade to main head using prior commit's migration code → upgrade to branch head → stamp new SHA |
| **PROD** (`ENV=prod`) | `alembic upgrade head` |
| **Runtime** | `dalembic.runtime.upgrade_head(alembic_ini)` for app-embedded startup |

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ENV` | *(required)* | `stg` or `prod` |
| `CI_COMMIT_SHA` / `COMMIT_SHA` | | Current deploy commit (STG) |
| `ALEMBIC_HEAD_REVISION_MAIN` | | Main branch head revision (STG) |
| `ALEMBIC_REVERT_STAMP` | | Stamp `alembic_version` after upgrade (revert workflow) |
| `REPO_ROOT` | cwd | Path to `alembic.ini` |
| `MIGRATIONS_SUBPATH` | `migrations` | Use `alembic` when migrations live under `alembic/` |
| `VERSIONS_SUBPATH` | `versions` | Versions directory under migrations |
| `DB_SCHEMA` | `public` | Postgres schema |
| `DEPLOY_STATE_KEY` | `deploy_commit_sha` | JSONB key in `app_state` |
| `DATABASE_URL` | | Full URL override |
| `DB_HOST` / `DB_PORT` / `DB_NAME` / `DB_USER` / `DB_PASSWORD` | see `DeploySettings` | Connection components |
| `DB_SSL_SERVER_CA` / `DB_SSL_CLIENT_CERT` / `DB_SSL_CLIENT_KEY` | | SSL certs (`LIQUIBASE_COMMAND_*` aliases accepted) |
| `LOCAL_DEV` | `false` | When `true`, `is_deployed()` is false (seed migrations no-op) |
| `SEED_DIR` | | CSV seed directory for `DataLoader` |

## Consumer layout

```
my-app/
├── alembic.ini
├── migrations/          # or alembic/ with MIGRATIONS_SUBPATH=alembic
│   ├── env.py
│   └── versions/
│       └── 0001_*.py
```

## CI wiring (STG)

Before STG deploy, export main's head revision:

```bash
export ALEMBIC_HEAD_REVISION_MAIN=$(git show origin/main:migrations/versions/ | grep -oP '^\d{4}' | sort | tail -1)
export CI_COMMIT_SHA=$CI_COMMIT_SHA
export ENV=stg
dalembic
```

## Revert workflow (2-MR)

**Warning:** reverting runs `downgrade()` — data loss is possible. Review downgrade bodies first.

**MR 1 — apply revert:** Add a migration that calls `revert_to` and set `ALEMBIC_REVERT_STAMP` in deploy jobs.

```python
from dalembic.revert import revert_to

revision = "0006"
down_revision = "0005"
TARGET = "0002"

def upgrade() -> None:
    revert_to(TARGET, from_revision=down_revision)

def downgrade() -> None:
    pass
```

Deploy STG → PROD with `ALEMBIC_REVERT_STAMP=0002`.

**MR 2 — cleanup:**

| Intent | Action |
|--------|--------|
| Temporary revert | Delete revert migration; remove `ALEMBIC_REVERT_STAMP` — redeploy re-applies originals |
| Permanent revert | Delete original reverted migrations; remove `ALEMBIC_REVERT_STAMP` |

## Abandon MR on STG

Empty your migration's `upgrade()` (keep `downgrade()`), redeploy. STG downgrades your changes via the previous migration code, then the empty upgrade is a no-op.

## Runtime helper (app startup)

```python
from pathlib import Path
from dalembic.runtime import configure_alembic_console_logging, upgrade_head

configure_alembic_console_logging()
upgrade_head(Path("alembic.ini"))
```

## Development

```bash
uv sync --all-extras
docker compose up -d
uv run pytest tests/unit -q
uv run pytest tests/integration -q
```

**pgAdmin:** http://localhost:5050 — login `admin@admin.com` / `admin`. The `dalembic-test` server is pre-configured (password via `pgadmin-pgpass`, no per-connection prompt).

## License

MIT
