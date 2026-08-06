from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Column, Index, Text
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    # Naive em UTC: o SQLite descarta timezone ao gravar, então manter tudo
    # naive evita comparações aware vs. naive no reaper.
    return datetime.now(timezone.utc).replace(tzinfo=None)


class JobStatus(str, Enum):
    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"
    timeout = "timeout"


TERMINAL_STATUSES = {
    JobStatus.succeeded,
    JobStatus.failed,
    JobStatus.cancelled,
    JobStatus.timeout,
}


class Rpa(SQLModel, table=True):
    __tablename__ = "rpas"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    description: str | None = None
    # JSON Schema serializado; validado contra os params na criação do job
    params_schema: str | None = Field(default=None, sa_column=Column(Text))
    default_timeout_seconds: int = 3600
    enabled: bool = True
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class Job(SQLModel, table=True):
    __tablename__ = "jobs"
    __table_args__ = (Index("ix_jobs_claim", "status", "priority", "id"),)

    id: int | None = Field(default=None, primary_key=True)
    rpa_id: int = Field(foreign_key="rpas.id")
    rpa_name: str = Field(index=True)
    params: str = Field(default="{}", sa_column=Column(Text))
    priority: int = 100
    status: JobStatus = Field(default=JobStatus.pending, index=True)
    worker_id: str | None = Field(default=None, index=True)
    attempt: int = 0
    max_attempts: int = 1
    result: str | None = Field(default=None, sa_column=Column(Text))
    log_tail: str | None = Field(default=None, sa_column=Column(Text))
    exit_code: int | None = None
    error: str | None = None
    timeout_seconds: int = 3600
    created_at: datetime = Field(default_factory=utcnow)
    claimed_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class Worker(SQLModel, table=True):
    __tablename__ = "workers"

    worker_id: str = Field(primary_key=True)
    hostname: str | None = None
    agent_version: str | None = None
    # lista JSON dos nomes de RPA que este worker sabe executar
    rpas: str = Field(default="[]", sa_column=Column(Text))
    last_heartbeat_at: datetime = Field(default_factory=utcnow, index=True)
    current_job_id: int | None = None
    created_at: datetime = Field(default_factory=utcnow)
