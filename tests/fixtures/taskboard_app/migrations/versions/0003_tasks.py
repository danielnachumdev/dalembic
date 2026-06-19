import os

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

SCHEMA = os.environ.get("DB_SCHEMA", "public")


def upgrade() -> None:
    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=True),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_table("tasks", schema=SCHEMA)
