"""Add operation audit trail (Sprint 07).

Revision ID: 20261020_0007
Revises: 20261016_0006
Create Date: 2026-10-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20261020_0007"
down_revision: str | None = "20261016_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    audit_action = postgresql.ENUM(
        "CREATE", "UPDATE", "DELETE", "EXECUTE", name="audit_action", create_type=False
    )
    audit_action.create(bind, checkfirst=True)
    op.create_table(
        "operation_logs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", audit_action, nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_operation_logs_created", "operation_logs", ["created_at"])
    op.create_index(
        "ix_operation_logs_entity", "operation_logs", ["entity_type", "entity_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_operation_logs_entity", table_name="operation_logs")
    op.drop_index("ix_operation_logs_created", table_name="operation_logs")
    op.drop_table("operation_logs")
    bind = op.get_bind()
    postgresql.ENUM(name="audit_action").drop(bind, checkfirst=True)
