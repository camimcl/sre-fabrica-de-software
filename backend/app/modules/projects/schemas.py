from datetime import datetime
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator, model_validator


class ProjectWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=5000)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Project name is required")
        return cleaned


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class EndpointWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    base_url: AnyHttpUrl
    http_method: str = "GET"
    authorization_confirmed: bool = False
    authorization_evidence: str | None = Field(default=None, max_length=5000)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Endpoint name is required")
        return cleaned

    @field_validator("http_method")
    @classmethod
    def allowed_method(cls, value: str) -> str:
        method = value.strip().upper()
        if method not in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"}:
            raise ValueError("Unsupported HTTP method")
        return method

    @model_validator(mode="after")
    def validate_authorization(self):
        if self.base_url.username or self.base_url.password or self.base_url.fragment:
            raise ValueError("Target URL cannot contain credentials or a fragment")
        if self.authorization_confirmed and not (self.authorization_evidence or "").strip():
            raise ValueError("Evidence is required when authorization is confirmed")
        return self


class EndpointResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    name: str
    base_url: str
    http_method: str
    authorization_confirmed: bool
    authorization_evidence: str | None
    created_at: datetime
