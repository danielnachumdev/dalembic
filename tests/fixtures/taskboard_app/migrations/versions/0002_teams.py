import os

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

SCHEMA = os.environ.get("DB_SCHEMA", "public")


def upgrade() -> None:
    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.Text(), nullable=False),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_table("teams", schema=SCHEMA)
