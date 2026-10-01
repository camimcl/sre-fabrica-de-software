"""Adiciona metadados auditaveis do modelo e completa o snapshot da execucao.

Revision ID: 20261001_0003
Revises: 20260925_0002
Create Date: 2026-10-01
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20261001_0003"
down_revision: str | None = "20260925_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "test_executions",
        sa.Column("ramp_up_per_window", sa.Integer(), nullable=True),
    )
    op.execute(
        """
        UPDATE test_executions AS execution
        SET ramp_up_per_window = scenario.ramp_up_per_window
        FROM test_scenarios AS scenario
        WHERE scenario.id = execution.scenario_id
        """
    )
    op.alter_column("test_executions", "ramp_up_per_window", nullable=False)
    op.create_check_constraint(
        "ck_execution_ramp_up", "test_executions", "ramp_up_per_window >= 0"
    )
    op.create_check_constraint(
        "ck_scenario_operational_limits",
        "test_scenarios",
        "duration_seconds <= 3600 AND max_concurrency <= 500 "
        "AND ramp_up_per_window <= 500 AND timeout_ms <= 60000 "
        "AND p95_limit_ms <= 300000",
    )
    op.create_check_constraint(
        "ck_execution_operational_limits",
        "test_executions",
        "duration_seconds <= 3600 AND max_concurrency <= 500 "
        "AND ramp_up_per_window <= 500 AND timeout_ms <= 60000 "
        "AND p95_limit_ms <= 300000",
    )

    op.add_column(
        "model_versions",
        sa.Column("accuracy_score", sa.Numeric(6, 5), nullable=True),
    )
    op.add_column(
        "model_versions",
        sa.Column("training_sample_count", sa.Integer(), nullable=True),
    )
    op.add_column(
        "model_versions",
        sa.Column("artifact_sha256", sa.String(length=64), nullable=True),
    )
    # Registros antigos eram apenas placeholders; os valores permitem a
    # migracao e deixam explicito que nao possuem artefato treinado confiavel.
    op.execute("UPDATE model_versions SET training_sample_count = 1 WHERE training_sample_count IS NULL")
    op.execute("UPDATE model_versions SET artifact_sha256 = repeat('0', 64) WHERE artifact_sha256 IS NULL")
    op.alter_column("model_versions", "training_sample_count", nullable=False)
    op.alter_column("model_versions", "artifact_sha256", nullable=False)
    op.create_check_constraint(
        "ck_model_accuracy",
        "model_versions",
        "accuracy_score IS NULL OR accuracy_score BETWEEN 0 AND 1",
    )
    op.create_check_constraint(
        "ck_model_sample_count", "model_versions", "training_sample_count > 0"
    )


def downgrade() -> None:
    op.drop_constraint("ck_model_sample_count", "model_versions", type_="check")
    op.drop_constraint("ck_model_accuracy", "model_versions", type_="check")
    op.drop_column("model_versions", "artifact_sha256")
    op.drop_column("model_versions", "training_sample_count")
    op.drop_column("model_versions", "accuracy_score")
    op.drop_constraint("ck_execution_ramp_up", "test_executions", type_="check")
    op.drop_constraint(
        "ck_execution_operational_limits", "test_executions", type_="check"
    )
    op.drop_constraint(
        "ck_scenario_operational_limits", "test_scenarios", type_="check"
    )
    op.drop_column("test_executions", "ramp_up_per_window")
