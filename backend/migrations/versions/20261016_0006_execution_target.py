"""Preserve the actual target used by new executions, without inventing history."""

import sqlalchemy as sa
from alembic import op

revision = "20261016_0006"
down_revision = "20261015_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("test_executions", sa.Column("target_snapshot", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("test_executions", "target_snapshot")
