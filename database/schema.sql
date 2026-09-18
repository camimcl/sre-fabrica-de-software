CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TYPE user_role AS ENUM ('QA', 'VIEWER');
CREATE TYPE execution_status AS ENUM ('PENDING', 'RUNNING', 'COMPLETED', 'CANCELLED', 'FAILED');
CREATE TYPE control_strategy AS ENUM ('FIXED', 'RULES', 'AI_HYBRID');
CREATE TYPE control_action AS ENUM ('INCREASE', 'HOLD', 'DECREASE', 'STOP');
CREATE TYPE model_status AS ENUM ('CANDIDATE', 'APPROVED', 'RETIRED');

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name VARCHAR(160) NOT NULL,
    email VARCHAR(254) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role user_role NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    name VARCHAR(120) NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_project_owner_name UNIQUE (owner_id, name)
);

CREATE TABLE endpoints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
    name VARCHAR(120) NOT NULL,
    base_url VARCHAR(2048) NOT NULL,
    http_method VARCHAR(10) NOT NULL DEFAULT 'GET',
    authorization_confirmed BOOLEAN NOT NULL DEFAULT false,
    authorization_evidence TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_endpoint_project_id UNIQUE (project_id, id),
    CONSTRAINT ck_endpoint_http_method CHECK (http_method IN ('GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD'))
);

CREATE TABLE model_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version VARCHAR(80) NOT NULL UNIQUE,
    algorithm VARCHAR(80) NOT NULL,
    artifact_path VARCHAR(512) NOT NULL,
    status model_status NOT NULL,
    precision_score NUMERIC(6,5),
    recall_score NUMERIC(6,5),
    f1_score NUMERIC(6,5),
    training_dataset_hash VARCHAR(128) NOT NULL,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_model_precision CHECK (precision_score IS NULL OR precision_score BETWEEN 0 AND 1),
    CONSTRAINT ck_model_recall CHECK (recall_score IS NULL OR recall_score BETWEEN 0 AND 1),
    CONSTRAINT ck_model_f1 CHECK (f1_score IS NULL OR f1_score BETWEEN 0 AND 1)
);

CREATE TABLE test_scenarios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
    endpoint_id UUID NOT NULL,
    created_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    name VARCHAR(120) NOT NULL,
    duration_seconds INTEGER NOT NULL,
    initial_concurrency INTEGER NOT NULL,
    max_concurrency INTEGER NOT NULL,
    ramp_up_per_window INTEGER NOT NULL,
    timeout_ms INTEGER NOT NULL,
    strategy control_strategy NOT NULL,
    p95_limit_ms INTEGER NOT NULL,
    error_rate_limit NUMERIC(6,5) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_scenario_endpoint_project FOREIGN KEY (project_id, endpoint_id)
        REFERENCES endpoints(project_id, id) ON DELETE RESTRICT,
    CONSTRAINT ck_scenario_duration CHECK (duration_seconds > 0),
    CONSTRAINT ck_scenario_concurrency CHECK (initial_concurrency > 0 AND max_concurrency >= initial_concurrency),
    CONSTRAINT ck_scenario_ramp_up CHECK (ramp_up_per_window > 0),
    CONSTRAINT ck_scenario_timeout CHECK (timeout_ms > 0),
    CONSTRAINT ck_scenario_p95_limit CHECK (p95_limit_ms > 0),
    CONSTRAINT ck_scenario_error_limit CHECK (error_rate_limit BETWEEN 0 AND 1)
);

CREATE TABLE test_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_id UUID NOT NULL REFERENCES test_scenarios(id) ON DELETE RESTRICT,
    initiated_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    model_version_id UUID REFERENCES model_versions(id) ON DELETE RESTRICT,
    status execution_status NOT NULL,
    strategy control_strategy NOT NULL,
    duration_seconds INTEGER NOT NULL,
    initial_concurrency INTEGER NOT NULL,
    max_concurrency INTEGER NOT NULL,
    timeout_ms INTEGER NOT NULL,
    p95_limit_ms INTEGER NOT NULL,
    error_rate_limit NUMERIC(6,5) NOT NULL,
    authorization_acknowledged BOOLEAN NOT NULL,
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    cancellation_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_execution_duration CHECK (duration_seconds > 0),
    CONSTRAINT ck_execution_concurrency CHECK (initial_concurrency > 0 AND max_concurrency >= initial_concurrency),
    CONSTRAINT ck_execution_timeout CHECK (timeout_ms > 0),
    CONSTRAINT ck_execution_p95_limit CHECK (p95_limit_ms > 0),
    CONSTRAINT ck_execution_error_limit CHECK (error_rate_limit BETWEEN 0 AND 1),
    CONSTRAINT ck_execution_dates CHECK (ended_at IS NULL OR started_at IS NULL OR ended_at >= started_at)
);

CREATE TABLE metric_windows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id UUID NOT NULL REFERENCES test_executions(id) ON DELETE CASCADE,
    sequence_number INTEGER NOT NULL,
    window_started_at TIMESTAMPTZ NOT NULL,
    window_duration_ms INTEGER NOT NULL,
    concurrency INTEGER NOT NULL,
    request_count INTEGER NOT NULL,
    success_count INTEGER NOT NULL,
    timeout_count INTEGER NOT NULL,
    throughput_rps NUMERIC(12,4) NOT NULL,
    latency_p50_ms NUMERIC(12,3) NOT NULL,
    latency_p95_ms NUMERIC(12,3) NOT NULL,
    latency_p99_ms NUMERIC(12,3) NOT NULL,
    error_rate NUMERIC(6,5) NOT NULL,
    cpu_percent NUMERIC(6,2) NOT NULL,
    memory_mb NUMERIC(12,2) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_metric_window_sequence UNIQUE (execution_id, sequence_number),
    CONSTRAINT ck_metric_sequence CHECK (sequence_number >= 0),
    CONSTRAINT ck_metric_window_duration CHECK (window_duration_ms > 0),
    CONSTRAINT ck_metric_counts CHECK (
        concurrency > 0 AND request_count >= 0 AND success_count >= 0
        AND timeout_count >= 0 AND success_count <= request_count
    ),
    CONSTRAINT ck_metric_non_negative CHECK (
        throughput_rps >= 0 AND latency_p50_ms >= 0 AND latency_p95_ms >= 0
        AND latency_p99_ms >= 0 AND cpu_percent >= 0 AND memory_mb >= 0
    ),
    CONSTRAINT ck_metric_error_rate CHECK (error_rate BETWEEN 0 AND 1)
);

CREATE TABLE risk_predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_window_id UUID NOT NULL UNIQUE REFERENCES metric_windows(id) ON DELETE CASCADE,
    model_version_id UUID NOT NULL REFERENCES model_versions(id) ON DELETE RESTRICT,
    risk_probability NUMERIC(6,5) NOT NULL,
    predicted_degradation BOOLEAN NOT NULL,
    inference_latency_ms INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_prediction_probability CHECK (risk_probability BETWEEN 0 AND 1),
    CONSTRAINT ck_prediction_latency CHECK (inference_latency_ms >= 0)
);

CREATE TABLE control_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_window_id UUID NOT NULL UNIQUE REFERENCES metric_windows(id) ON DELETE CASCADE,
    risk_prediction_id UUID UNIQUE REFERENCES risk_predictions(id) ON DELETE SET NULL,
    strategy control_strategy NOT NULL,
    action control_action NOT NULL,
    previous_concurrency INTEGER NOT NULL,
    next_concurrency INTEGER NOT NULL,
    reason TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_decision_concurrency CHECK (previous_concurrency > 0 AND next_concurrency > 0)
);

CREATE TABLE execution_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id UUID NOT NULL UNIQUE REFERENCES test_executions(id) ON DELETE CASCADE,
    total_requests INTEGER NOT NULL,
    successful_requests INTEGER NOT NULL,
    average_throughput_rps NUMERIC(12,4) NOT NULL,
    final_latency_p95_ms NUMERIC(12,3) NOT NULL,
    final_error_rate NUMERIC(6,5) NOT NULL,
    summary TEXT,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_report_counts CHECK (
        total_requests >= 0 AND successful_requests >= 0 AND successful_requests <= total_requests
    ),
    CONSTRAINT ck_report_metrics CHECK (
        average_throughput_rps >= 0 AND final_latency_p95_ms >= 0
        AND final_error_rate BETWEEN 0 AND 1
    )
);

CREATE INDEX ix_projects_owner_id ON projects(owner_id);
CREATE INDEX ix_endpoints_project_id ON endpoints(project_id);
CREATE INDEX ix_scenarios_project_id ON test_scenarios(project_id);
CREATE INDEX ix_scenarios_endpoint_id ON test_scenarios(endpoint_id);
CREATE INDEX ix_executions_scenario_created ON test_executions(scenario_id, created_at DESC);
CREATE INDEX ix_metric_windows_execution_time ON metric_windows(execution_id, window_started_at);
CREATE INDEX ix_predictions_model_version ON risk_predictions(model_version_id);
CREATE INDEX ix_model_versions_status ON model_versions(status);
