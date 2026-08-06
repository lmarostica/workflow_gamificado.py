import json

from fastapi import APIRouter, Depends, HTTPException, Query
from jsonschema import Draft202012Validator
from sqlmodel import Session, func, select

from server.auth import require_client_key
from server.db import get_session
from server.models import Job, JobStatus, Rpa
from server.schemas import JobCreate, JobListOut, JobOut

router = APIRouter(
    prefix="/jobs", tags=["jobs"], dependencies=[Depends(require_client_key)]
)


def to_out(job: Job) -> JobOut:
    return JobOut(
        id=job.id,
        rpa_name=job.rpa_name,
        params=json.loads(job.params) if job.params else {},
        priority=job.priority,
        status=job.status,
        worker_id=job.worker_id,
        attempt=job.attempt,
        max_attempts=job.max_attempts,
        result=json.loads(job.result) if job.result else None,
        log_tail=job.log_tail,
        exit_code=job.exit_code,
        error=job.error,
        timeout_seconds=job.timeout_seconds,
        created_at=job.created_at,
        claimed_at=job.claimed_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
    )


@router.post("", status_code=201, response_model=JobOut)
def create_job(body: JobCreate, session: Session = Depends(get_session)):
    rpa = session.exec(select(Rpa).where(Rpa.name == body.rpa)).first()
    if rpa is None:
        raise HTTPException(status_code=404, detail=f"RPA '{body.rpa}' não encontrado")
    if not rpa.enabled:
        raise HTTPException(status_code=409, detail=f"RPA '{body.rpa}' está desabilitado")

    if rpa.params_schema:
        validator = Draft202012Validator(json.loads(rpa.params_schema))
        errors = sorted(validator.iter_errors(body.params), key=lambda e: e.json_path)
        if errors:
            raise HTTPException(
                status_code=422,
                detail=[
                    {"path": e.json_path, "message": e.message} for e in errors
                ],
            )

    job = Job(
        rpa_id=rpa.id,
        rpa_name=rpa.name,
        params=json.dumps(body.params),
        priority=body.priority,
        max_attempts=body.max_attempts,
        timeout_seconds=body.timeout_seconds or rpa.default_timeout_seconds,
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    return to_out(job)


@router.get("", response_model=JobListOut)
def list_jobs(
    session: Session = Depends(get_session),
    status: JobStatus | None = None,
    rpa: str | None = None,
    worker_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    query = select(Job)
    if status is not None:
        query = query.where(Job.status == status)
    if rpa is not None:
        query = query.where(Job.rpa_name == rpa)
    if worker_id is not None:
        query = query.where(Job.worker_id == worker_id)

    total = session.exec(
        select(func.count()).select_from(query.subquery())
    ).one()
    jobs = session.exec(
        query.order_by(Job.id.desc()).limit(limit).offset(offset)
    ).all()
    return JobListOut(total=total, items=[to_out(j) for j in jobs])


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: int, session: Session = Depends(get_session)):
    job = session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    return to_out(job)


@router.post("/{job_id}/cancel", response_model=JobOut)
def cancel_job(job_id: int, session: Session = Depends(get_session)):
    job = session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    if job.status != JobStatus.pending:
        raise HTTPException(
            status_code=409,
            detail=f"Só jobs pending podem ser cancelados (atual: {job.status.value})",
        )
    from server.models import utcnow

    job.status = JobStatus.cancelled
    job.finished_at = utcnow()
    session.add(job)
    session.commit()
    session.refresh(job)
    return to_out(job)
