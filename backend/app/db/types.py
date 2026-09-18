from enum import StrEnum


class UserRole(StrEnum):
    QA = "QA"
    VIEWER = "VIEWER"


class ExecutionStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class ControlStrategy(StrEnum):
    FIXED = "FIXED"
    RULES = "RULES"
    AI_HYBRID = "AI_HYBRID"


class ControlAction(StrEnum):
    INCREASE = "INCREASE"
    HOLD = "HOLD"
    DECREASE = "DECREASE"
    STOP = "STOP"


class ModelStatus(StrEnum):
    CANDIDATE = "CANDIDATE"
    APPROVED = "APPROVED"
    RETIRED = "RETIRED"
