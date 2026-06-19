import os

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

SCHEMA = os.environ.get("DB_SCHEMA", "public")


def upgrade() -> None:
    op.alter_column(
        "tasks",
        "team_id",
        server_default=sa.text("1"),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.alter_column("tasks", "team_id", server_default=None, schema=SCHEMA)
