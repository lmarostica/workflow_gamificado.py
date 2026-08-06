import json

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session, select

from server.auth import require_client_key, require_worker_key
from server.db import get_session
from server.models import Worker, utcnow
from server.routers.jobs import to_out as job_to_out
from server.schemas import (
    JobOut,
    WorkerClaim,
    WorkerHeartbeat,
    WorkerOut,
    WorkerRegister,
    WorkerReport,
)
from server.services import queue

router = APIRouter(
    prefix="/worker", tags=["workers"], dependencies=[Depends(require_worker_key)]
)


@router.post("/register", response_model=WorkerOut)
def register(body: WorkerRegister, session: Session = Depends(get_session)):
    worker = session.get(Worker, body.worker_id)
    if worker is None:
        worker = Worker(worker_id=body.worker_id)
    worker.hostname = body.hostname
    worker.agent_version = body.agent_version
    worker.rpas = json.dumps(body.rpas)
    worker.last_heartbeat_at = utcnow()
    session.add(worker)
    session.commit()
    session.refresh(worker)
    return _worker_out(worker)


@router.post("/claim", response_model=JobOut)
def claim(body: WorkerClaim, session: Session = Depends(get_session)):
    try:
        job = queue.claim_next_job(session, body.worker_id)
    except queue.UnknownWorkerError:
        raise HTTPException(
            status_code=404, detail="Worker não registrado; chame /worker/register"
        )
    except queue.WorkerBusyError:
        raise HTTPException(
            status_code=409, detail="Worker já tem um job em andamento"
        )
    if job is None:
        return Response(status_code=204)
    return job_to_out(job)


@router.post("/jobs/{job_id}/heartbeat")
def heartbeat(
    job_id: int, body: WorkerHeartbeat, session: Session = Depends(get_session)
):
    try:
        queue.heartbeat(session, job_id, body.worker_id)
    except queue.UnknownWorkerError:
        raise HTTPException(status_code=404, detail="Worker não registrado")
    except queue.ConflictError as exc:
        raise HTTPException(status_code=409, detail=exc.detail)
    return {"ok": True}


@router.post("/jobs/{job_id}/report", response_model=JobOut)
def report(
    job_id: int, body: WorkerReport, session: Session = Depends(get_session)
):
    try:
        job = queue.report(
            session,
            job_id,
            body.worker_id,
            body.status,
            body.exit_code,
            body.result,
            body.log_tail,
            body.error,
        )
    except queue.ConflictError as exc:
        raise HTTPException(status_code=409, detail=exc.detail)
    return job_to_out(job)


def _worker_out(worker: Worker) -> WorkerOut:
    return WorkerOut(
        worker_id=worker.worker_id,
        hostname=worker.hostname,
        agent_version=worker.agent_version,
        rpas=json.loads(worker.rpas),
        last_heartbeat_at=worker.last_heartbeat_at,
        current_job_id=worker.current_job_id,
        created_at=worker.created_at,
    )


# Listagem de workers para o cliente (chave de cliente, não de worker)
client_router = APIRouter(tags=["workers"])


@client_router.get(
    "/workers",
    response_model=list[WorkerOut],
    dependencies=[Depends(require_client_key)],
)
def list_workers(session: Session = Depends(get_session)):
    workers = session.exec(select(Worker).order_by(Worker.worker_id)).all()
    return [_worker_out(w) for w in workers]
