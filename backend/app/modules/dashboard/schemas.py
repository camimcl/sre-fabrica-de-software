from pydantic import BaseModel


class DashboardTotals(BaseModel):
    executions: int
    scenarios: int
    endpoints: int
    comparisons: int


class DashboardPerformance(BaseModel):
    avg_throughput_rps: float
    avg_latency_p95_ms: float
    avg_error_rate: float


class TimeseriesPoint(BaseModel):
    day: str
    count: int


class DashboardResponse(BaseModel):
    totals: DashboardTotals
    executions_by_status: dict[str, int]
    executions_by_strategy: dict[str, int]
    completion_rate: float
    performance: DashboardPerformance
    timeseries_executions_per_day: list[TimeseriesPoint]
