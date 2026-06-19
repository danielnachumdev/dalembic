import os

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

SCHEMA = os.environ.get("DB_SCHEMA", "public")


def upgrade() -> None:
    op.create_table(
        "deploy_audit",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("note", sa.Text(), nullable=False, server_default="bootstrap"),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_table("deploy_audit", schema=SCHEMA)
