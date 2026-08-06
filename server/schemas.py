from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from server.models import JobStatus


# ---------- Catálogo de RPAs ----------

class RpaCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    params_schema: dict[str, Any] | None = None
    default_timeout_seconds: int = Field(default=3600, gt=0)


class RpaUpdate(BaseModel):
    description: str | None = None
    params_schema: dict[str, Any] | None = None
    default_timeout_seconds: int | None = Field(default=None, gt=0)
    enabled: bool | None = None


class RpaOut(BaseModel):
    id: int
    name: str
    description: str | None
    params_schema: dict[str, Any] | None
    default_timeout_seconds: int
    enabled: bool
    created_at: datetime
    updated_at: datetime


# ---------- Jobs (lado cliente) ----------

class JobCreate(BaseModel):
    rpa: str
    params: dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=100, ge=0)
    timeout_seconds: int | None = Field(default=None, gt=0)
    max_attempts: int = Field(default=1, ge=1, le=10)


class JobOut(BaseModel):
    id: int
    rpa_name: str
    params: dict[str, Any]
    priority: int
    status: JobStatus
    worker_id: str | None
    attempt: int
    max_attempts: int
    result: dict[str, Any] | None
    log_tail: str | None
    exit_code: int | None
    error: str | None
    timeout_seconds: int
    created_at: datetime
    claimed_at: datetime | None
    started_at: datetime | None
    finished_at: datetime | None


class JobListOut(BaseModel):
    total: int
    items: list[JobOut]


# ---------- Workers ----------

class WorkerRegister(BaseModel):
    worker_id: str = Field(min_length=1, max_length=200)
    hostname: str | None = None
    agent_version: str | None = None
    rpas: list[str] = Field(default_factory=list)


class WorkerClaim(BaseModel):
    worker_id: str


class WorkerHeartbeat(BaseModel):
    worker_id: str


class WorkerReport(BaseModel):
    worker_id: str
    status: JobStatus
    exit_code: int | None = None
    result: dict[str, Any] | None = None
    log_tail: str | None = None
    error: str | None = None


class WorkerOut(BaseModel):
    worker_id: str
    hostname: str | None
    agent_version: str | None
    rpas: list[str]
    last_heartbeat_at: datetime
    current_job_id: int | None
    created_at: datetime
