"""Add persisted repeated-strategy comparison reports.

Revision ID: 20261015_0005
Revises: 20261001_0004
Create Date: 2026-10-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20261015_0005"
down_revision: str | None = "20261001_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    control_strategy = postgresql.ENUM(
        "FIXED", "RULES", "AI_HYBRID", name="control_strategy", create_type=False
    )
    op.create_table(
        "comparison_reports",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("repetitions_per_strategy", sa.Integer(), nullable=False),
        sa.Column("conditions_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("conditions_json", sa.Text(), nullable=False),
        sa.Column("results_json", sa.Text(), nullable=False),
        sa.Column("conclusion", sa.Text(), nullable=False),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "repetitions_per_strategy >= 3", name="ck_comparison_repetitions"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_comparison_reports_project_generated",
        "comparison_reports",
        ["project_id", "generated_at"],
    )
    op.create_table(
        "comparison_report_executions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "comparison_report_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("execution_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("strategy", control_strategy, nullable=False),
        sa.Column("repetition_number", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "repetition_number > 0", name="ck_comparison_repetition_number"
        ),
        sa.ForeignKeyConstraint(
            ["comparison_report_id"],
            ["comparison_reports.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["execution_id"], ["test_executions.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "comparison_report_id",
            "execution_id",
            name="uq_comparison_report_execution",
        ),
        sa.UniqueConstraint(
            "comparison_report_id",
            "strategy",
            "repetition_number",
            name="uq_comparison_strategy_repetition",
        ),
    )


def downgrade() -> None:
    op.drop_table("comparison_report_executions")
    op.drop_index(
        "ix_comparison_reports_project_generated", table_name="comparison_reports"
    )
    op.drop_table("comparison_reports")
