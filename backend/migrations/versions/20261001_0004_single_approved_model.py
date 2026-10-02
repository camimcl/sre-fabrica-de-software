"""Enforce one approved model even for concurrent approval requests."""
from alembic import op
import sqlalchemy as sa

revision = "20261001_0004"
down_revision = "20261001_0003"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""UPDATE model_versions SET status = 'RETIRED' WHERE id IN (
        SELECT id FROM (SELECT id, row_number() OVER (
            ORDER BY created_at DESC, id DESC) AS rank
            FROM model_versions WHERE status = 'APPROVED') AS ranked WHERE rank > 1
    )""")
    op.create_index("uq_model_single_approved", "model_versions", ["status"],
                    unique=True, postgresql_where=sa.text("status = 'APPROVED'"))


def downgrade():
    op.drop_index("uq_model_single_approved", table_name="model_versions")
