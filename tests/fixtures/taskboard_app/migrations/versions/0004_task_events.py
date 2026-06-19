import os

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

SCHEMA = os.environ.get("DB_SCHEMA", "public")


def upgrade() -> None:
    op.create_table(
        "task_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("logged_at", sa.DateTime(timezone=False)),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_table("task_events", schema=SCHEMA)
