# dalembic

**Branch-aware Alembic deployment:** STG downgrade-to-main, prod upgrade-to-head, reverts, and deploy state.

> **Not SQLAlchemy Alembic.** SQLAlchemy: `import alembic` / `alembic upgrade head`. This package: `import dalembic` / `dalembic`.

## Problems this solves

- **Concurrent STG merges** — Downgrade with the previous branch's migration code, then upgrade to the new head.
- **Edited migration on the same branch** — Redeploy after changing an unreleased revision; STG uses the prior commit's migration files to downgrade first.
- **Abandoned MR on STG** — Empty `upgrade()` (keep `downgrade()`), redeploy to roll back.
- **Controlled reverts** — Revert migration + `ALEMBIC_REVERT_STAMP` to run `downgrade()` and stamp a target revision.
- **Deploy audit trail** — STG records the last deployed commit SHA in Postgres `dalembic_state`.
- **Prod stays simple** — Production is still upgrade-to-head.

## Install

```bash
uv add dalembic   # or: pip install dalembic
```

## CI: use `dalembic`, not `alembic upgrade head`

Replace `alembic upgrade head` in deploy jobs with `dalembic`. It picks the Alembic operation from deploy state (`ENV`, commit SHA, last STG deploy, optional revert stamp).

| `ENV` | What runs |
|-------|-----------|
| **prod** | `alembic upgrade head` |
| **stg** | Optional downgrade to main head (prior commit's migrations) → upgrade head → stamp commit SHA |
| **+ `ALEMBIC_REVERT_STAMP`** | `alembic stamp <revision>` after upgrade |

**Prod:**

```bash
export ENV=prod DB_HOST=... DB_PORT=... DB_NAME=... DB_USER=... DB_PASSWORD=...
dalembic
```

**STG** (also set `CI_COMMIT_SHA` and main's head revision):

```bash
export ALEMBIC_HEAD_REVISION_MAIN=$(git show origin/main:migrations/versions/ | grep -oP '^\d{4}' | sort | tail -1)
export CI_COMMIT_SHA=$CI_COMMIT_SHA ENV=stg
dalembic
```

On STG, do not call `alembic upgrade head` directly — you lose downgrade-before-upgrade and deploy-state tracking.

## Key environment variables

| Variable | Purpose |
|----------|---------|
| `ENV` | `stg` or `prod` (required) |
| `CI_COMMIT_SHA` | Deploy commit (STG) |
| `ALEMBIC_HEAD_REVISION_MAIN` | Main branch head revision (STG) |
| `ALEMBIC_REVERT_STAMP` | Post-upgrade `alembic stamp` target |
| `MIGRATIONS_SUBPATH` | `migrations` (default) or `alembic` |
| `DB_*` / `DATABASE_URL` | Postgres connection |
| `LOCAL_DEV` | `true` → seed migrations no-op |

See `DeploySettings` in code for the full list.

## Revert workflow (2-MR)

Reverting is **lossy** — review `downgrade()` bodies first.

**MR 1:** Add a migration calling `revert_to`, deploy with `ALEMBIC_REVERT_STAMP=<target>`.

```python
from dalembic.revert import revert_to

def upgrade() -> None:
    revert_to("0002", from_revision="0005")

def downgrade() -> None:
    pass
```

**MR 2:** Remove the revert migration and `ALEMBIC_REVERT_STAMP`. Temporary revert: originals re-apply on deploy. Permanent revert: delete the original migrations too.

## App startup (optional)

For embedded upgrades without STG state: `dalembic.runtime.upgrade_head(Path("alembic.ini"))`.

## Development

```bash
uv sync --all-extras
docker compose up -d
uv run pytest tests/unit tests/integration -q
```

pgAdmin: http://localhost:5050 (`admin@admin.com` / `admin`, server pre-configured).

## License

MIT
