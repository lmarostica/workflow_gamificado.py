"""Lógica da fila: claim atômico e transições de estado dos jobs."""

import json

from sqlalchemy import text
from sqlmodel import Session

from server.models import TERMINAL_STATUSES, Job, JobStatus, Worker, utcnow


class WorkerBusyError(Exception):
    """Worker já tem um job em andamento."""


class UnknownWorkerError(Exception):
    """Worker não registrado."""


class ConflictError(Exception):
    """Transição de estado inválida (job de outro worker, já finalizado etc.)."""

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


def claim_next_job(session: Session, worker_id: str) -> Job | None:
    """Entrega o próximo job pendente ao worker, de forma atômica.

    Ordenação: menor priority primeiro; empate resolvido por id (FIFO).
    Toda a operação roda numa transação BEGIN IMMEDIATE (ver db.py), e o
    UPDATE com subselect é uma instrução única — dois claims concorrentes
    nunca levam o mesmo job.
    """
    worker = session.get(Worker, worker_id)
    if worker is None:
        raise UnknownWorkerError()

    if worker.current_job_id is not None:
        current = session.get(Job, worker.current_job_id)
        if (
            current is not None
            and current.status == JobStatus.running
            and current.worker_id == worker_id
        ):
            raise WorkerBusyError()
        # Referência velha (job já finalizado/requeado): limpa e segue.
        worker.current_job_id = None

    rpa_names = json.loads(worker.rpas)
    if not rpa_names:
        session.commit()
        return None

    now = utcnow()
    placeholders = ", ".join(f":rpa{i}" for i in range(len(rpa_names)))
    params = {f"rpa{i}": name for i, name in enumerate(rpa_names)}
    params.update(
        wid=worker_id,
        now=now.isoformat(sep=" ", timespec="microseconds"),
    )
    row = session.execute(
        text(
            f"""
            UPDATE jobs
            SET status='running', worker_id=:wid, attempt=attempt+1,
                claimed_at=:now, started_at=:now
            WHERE id = (
                SELECT id FROM jobs
                WHERE status='pending' AND rpa_name IN ({placeholders})
                ORDER BY priority ASC, id ASC
                LIMIT 1
            )
            RETURNING id
            """
        ),
        params,
    ).first()

    if row is None:
        session.commit()
        return None

    worker.current_job_id = row[0]
    worker.last_heartbeat_at = now
    session.add(worker)
    session.commit()
    job = session.get(Job, row[0])
    session.refresh(job)
    return job


def heartbeat(session: Session, job_id: int, worker_id: str) -> None:
    job = session.get(Job, job_id)
    if job is None:
        raise ConflictError("Job não existe")
    if job.status != JobStatus.running or job.worker_id != worker_id:
        raise ConflictError(
            "Job não pertence mais a este worker (requeado ou finalizado)"
        )
    worker = session.get(Worker, worker_id)
    if worker is None:
        raise UnknownWorkerError()
    worker.last_heartbeat_at = utcnow()
    session.add(worker)
    session.commit()


def report(
    session: Session,
    job_id: int,
    worker_id: str,
    status: JobStatus,
    exit_code: int | None,
    result: dict | None,
    log_tail: str | None,
    error: str | None,
) -> Job:
    if status not in (JobStatus.succeeded, JobStatus.failed, JobStatus.timeout):
        raise ConflictError("Status de report deve ser succeeded, failed ou timeout")

    job = session.get(Job, job_id)
    if job is None:
        raise ConflictError("Job não existe")

    if job.status in TERMINAL_STATUSES:
        # Idempotência: report repetido do mesmo worker com o mesmo desfecho.
        if job.worker_id == worker_id and job.status == status:
            return job
        raise ConflictError(f"Job já finalizado com status {job.status.value}")

    if job.status != JobStatus.running or job.worker_id != worker_id:
        raise ConflictError("Job não pertence a este worker")

    job.status = status
    job.exit_code = exit_code
    job.result = json.dumps(result) if result is not None else None
    job.log_tail = log_tail
    job.error = error
    job.finished_at = utcnow()
    session.add(job)

    worker = session.get(Worker, worker_id)
    if worker is not None:
        if worker.current_job_id == job_id:
            worker.current_job_id = None
        worker.last_heartbeat_at = utcnow()
        session.add(worker)

    session.commit()
    session.refresh(job)
    return job
