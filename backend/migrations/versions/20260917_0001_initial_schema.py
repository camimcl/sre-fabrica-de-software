"""Cria o esquema inicial da Sprint 02.

Revision ID: 20260917_0001
Revises: None
Create Date: 2026-09-17
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260917_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


user_role = postgresql.ENUM("QA", "VIEWER", name="user_role", create_type=False)
execution_status = postgresql.ENUM(
    "PENDING", "RUNNING", "COMPLETED", "CANCELLED", "FAILED",
    name="execution_status", create_type=False,
)
control_strategy = postgresql.ENUM(
    "FIXED", "RULES", "AI_HYBRID", name="control_strategy", create_type=False
)
control_action = postgresql.ENUM(
    "INCREASE", "HOLD", "DECREASE", "STOP", name="control_action", create_type=False
)
model_status = postgresql.ENUM(
    "CANDIDATE", "APPROVED", "RETIRED", name="model_status", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    for enum_type in (
        user_role, execution_status, control_strategy, control_action, model_status
    ):
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("full_name", sa.String(160), nullable=False),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_id", "name", name="uq_project_owner_name"),
    )
    op.create_table(
        "endpoints",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("base_url", sa.String(2048), nullable=False),
        sa.Column("http_method", sa.String(10), server_default="GET", nullable=False),
        sa.Column("authorization_confirmed", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("authorization_evidence", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("http_method IN ('GET','POST','PUT','PATCH','DELETE','HEAD')", name="ck_endpoint_http_method"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "id", name="uq_endpoint_project_id"),
    )
    op.create_table(
        "model_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("version", sa.String(80), nullable=False),
        sa.Column("algorithm", sa.String(80), nullable=False),
        sa.Column("artifact_path", sa.String(512), nullable=False),
        sa.Column("status", model_status, nullable=False),
        sa.Column("precision_score", sa.Numeric(6, 5)),
        sa.Column("recall_score", sa.Numeric(6, 5)),
        sa.Column("f1_score", sa.Numeric(6, 5)),
        sa.Column("training_dataset_hash", sa.String(128), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("precision_score IS NULL OR precision_score BETWEEN 0 AND 1", name="ck_model_precision"),
        sa.CheckConstraint("recall_score IS NULL OR recall_score BETWEEN 0 AND 1", name="ck_model_recall"),
        sa.CheckConstraint("f1_score IS NULL OR f1_score BETWEEN 0 AND 1", name="ck_model_f1"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("version", name="uq_model_versions_version"),
    )
    op.create_table(
        "test_scenarios",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("endpoint_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=False),
        sa.Column("initial_concurrency", sa.Integer(), nullable=False),
        sa.Column("max_concurrency", sa.Integer(), nullable=False),
        sa.Column("ramp_up_per_window", sa.Integer(), nullable=False),
        sa.Column("timeout_ms", sa.Integer(), nullable=False),
        sa.Column("strategy", control_strategy, nullable=False),
        sa.Column("p95_limit_ms", sa.Integer(), nullable=False),
        sa.Column("error_rate_limit", sa.Numeric(6, 5), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("duration_seconds > 0", name="ck_scenario_duration"),
        sa.CheckConstraint("initial_concurrency > 0 AND max_concurrency >= initial_concurrency", name="ck_scenario_concurrency"),
        sa.CheckConstraint("ramp_up_per_window > 0", name="ck_scenario_ramp_up"),
        sa.CheckConstraint("timeout_ms > 0", name="ck_scenario_timeout"),
        sa.CheckConstraint("p95_limit_ms > 0", name="ck_scenario_p95_limit"),
        sa.CheckConstraint("error_rate_limit BETWEEN 0 AND 1", name="ck_scenario_error_limit"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["project_id", "endpoint_id"], ["endpoints.project_id", "endpoints.id"], name="fk_scenario_endpoint_project", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "test_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("scenario_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("initiated_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("model_version_id", postgresql.UUID(as_uuid=True)),
        sa.Column("status", execution_status, nullable=False),
        sa.Column("strategy", control_strategy, nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=False),
        sa.Column("initial_concurrency", sa.Integer(), nullable=False),
        sa.Column("max_concurrency", sa.Integer(), nullable=False),
        sa.Column("timeout_ms", sa.Integer(), nullable=False),
        sa.Column("p95_limit_ms", sa.Integer(), nullable=False),
        sa.Column("error_rate_limit", sa.Numeric(6, 5), nullable=False),
        sa.Column("authorization_acknowledged", sa.Boolean(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column("cancellation_reason", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("duration_seconds > 0", name="ck_execution_duration"),
        sa.CheckConstraint("initial_concurrency > 0 AND max_concurrency >= initial_concurrency", name="ck_execution_concurrency"),
        sa.CheckConstraint("timeout_ms > 0", name="ck_execution_timeout"),
        sa.CheckConstraint("p95_limit_ms > 0", name="ck_execution_p95_limit"),
        sa.CheckConstraint("error_rate_limit BETWEEN 0 AND 1", name="ck_execution_error_limit"),
        sa.CheckConstraint("ended_at IS NULL OR started_at IS NULL OR ended_at >= started_at", name="ck_execution_dates"),
        sa.ForeignKeyConstraint(["initiated_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["model_version_id"], ["model_versions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["scenario_id"], ["test_scenarios.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "metric_windows",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("execution_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_duration_ms", sa.Integer(), nullable=False),
        sa.Column("concurrency", sa.Integer(), nullable=False),
        sa.Column("request_count", sa.Integer(), nullable=False),
        sa.Column("success_count", sa.Integer(), nullable=False),
        sa.Column("timeout_count", sa.Integer(), nullable=False),
        sa.Column("throughput_rps", sa.Numeric(12, 4), nullable=False),
        sa.Column("latency_p50_ms", sa.Numeric(12, 3), nullable=False),
        sa.Column("latency_p95_ms", sa.Numeric(12, 3), nullable=False),
        sa.Column("latency_p99_ms", sa.Numeric(12, 3), nullable=False),
        sa.Column("error_rate", sa.Numeric(6, 5), nullable=False),
        sa.Column("cpu_percent", sa.Numeric(6, 2), nullable=False),
        sa.Column("memory_mb", sa.Numeric(12, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("sequence_number >= 0", name="ck_metric_sequence"),
        sa.CheckConstraint("window_duration_ms > 0", name="ck_metric_window_duration"),
        sa.CheckConstraint("concurrency > 0 AND request_count >= 0 AND success_count >= 0 AND timeout_count >= 0 AND success_count <= request_count", name="ck_metric_counts"),
        sa.CheckConstraint("throughput_rps >= 0 AND latency_p50_ms >= 0 AND latency_p95_ms >= 0 AND latency_p99_ms >= 0 AND cpu_percent >= 0 AND memory_mb >= 0", name="ck_metric_non_negative"),
        sa.CheckConstraint("error_rate BETWEEN 0 AND 1", name="ck_metric_error_rate"),
        sa.ForeignKeyConstraint(["execution_id"], ["test_executions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("execution_id", "sequence_number", name="uq_metric_window_sequence"),
    )
    op.create_table(
        "risk_predictions",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("metric_window_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("model_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("risk_probability", sa.Numeric(6, 5), nullable=False),
        sa.Column("predicted_degradation", sa.Boolean(), nullable=False),
        sa.Column("inference_latency_ms", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("risk_probability BETWEEN 0 AND 1", name="ck_prediction_probability"),
        sa.CheckConstraint("inference_latency_ms >= 0", name="ck_prediction_latency"),
        sa.ForeignKeyConstraint(["metric_window_id"], ["metric_windows.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["model_version_id"], ["model_versions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("metric_window_id", name="uq_prediction_metric_window"),
    )
    op.create_table(
        "control_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("metric_window_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("risk_prediction_id", postgresql.UUID(as_uuid=True)),
        sa.Column("strategy", control_strategy, nullable=False),
        sa.Column("action", control_action, nullable=False),
        sa.Column("previous_concurrency", sa.Integer(), nullable=False),
        sa.Column("next_concurrency", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("previous_concurrency > 0 AND next_concurrency > 0", name="ck_decision_concurrency"),
        sa.ForeignKeyConstraint(["metric_window_id"], ["metric_windows.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["risk_prediction_id"], ["risk_predictions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("metric_window_id", name="uq_decision_metric_window"),
        sa.UniqueConstraint("risk_prediction_id", name="uq_decision_prediction"),
    )
    op.create_table(
        "execution_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("execution_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("total_requests", sa.Integer(), nullable=False),
        sa.Column("successful_requests", sa.Integer(), nullable=False),
        sa.Column("average_throughput_rps", sa.Numeric(12, 4), nullable=False),
        sa.Column("final_latency_p95_ms", sa.Numeric(12, 3), nullable=False),
        sa.Column("final_error_rate", sa.Numeric(6, 5), nullable=False),
        sa.Column("summary", sa.Text()),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("total_requests >= 0 AND successful_requests >= 0 AND successful_requests <= total_requests", name="ck_report_counts"),
        sa.CheckConstraint("average_throughput_rps >= 0 AND final_latency_p95_ms >= 0 AND final_error_rate BETWEEN 0 AND 1", name="ck_report_metrics"),
        sa.ForeignKeyConstraint(["execution_id"], ["test_executions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("execution_id", name="uq_report_execution"),
    )

    op.create_index("ix_projects_owner_id", "projects", ["owner_id"])
    op.create_index("ix_endpoints_project_id", "endpoints", ["project_id"])
    op.create_index("ix_scenarios_project_id", "test_scenarios", ["project_id"])
    op.create_index("ix_scenarios_endpoint_id", "test_scenarios", ["endpoint_id"])
    op.execute(
        "CREATE INDEX ix_executions_scenario_created "
        "ON test_executions (scenario_id, created_at DESC)"
    )
    op.create_index("ix_metric_windows_execution_time", "metric_windows", ["execution_id", "window_started_at"])
    op.create_index("ix_predictions_model_version", "risk_predictions", ["model_version_id"])
    op.create_index("ix_model_versions_status", "model_versions", ["status"])


def downgrade() -> None:
    for table in (
        "execution_reports", "control_decisions", "risk_predictions",
        "metric_windows", "test_executions", "test_scenarios",
        "model_versions", "endpoints", "projects", "users",
    ):
        op.drop_table(table)
    bind = op.get_bind()
    for enum_type in (
        model_status, control_action, control_strategy, execution_status, user_role
    ):
        enum_type.drop(bind, checkfirst=True)
