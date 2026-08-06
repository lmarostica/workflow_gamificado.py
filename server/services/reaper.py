"""Recuperação de jobs órfãos e timeouts server-side."""

import asyncio
import logging
from datetime import datetime, timedelta

from sqlmodel import Session, select

from server.config import get_settings
from server.db import get_engine
from server.models import Job, JobStatus, Worker

logger = logging.getLogger("orquestrador.reaper")


def run_reaper_once(session: Session, now: datetime) -> list[tuple[int, str]]:
    """Uma passada do reaper. Retorna [(job_id, ação)] para log/teste."""
    settings = get_settings()
    orphan_cutoff = now - timedelta(seconds=settings.orphan_timeout_seconds)
    actions: list[tuple[int, str]] = []

    running_jobs = session.exec(
        select(Job).where(Job.status == JobStatus.running)
    ).all()

    for job in running_jobs:
        worker = session.get(Worker, job.worker_id) if job.worker_id else None

        # 1) Timeout duro: worker deveria ter reportado há tempo (folga de 60s
        #    sobre o timeout do job). Cobre agente que morreu sem matar o RPA.
        hard_deadline = (job.started_at or job.created_at) + timedelta(
            seconds=job.timeout_seconds + 60
        )
        if now >= hard_deadline:
            job.status = JobStatus.timeout
            job.error = (
                f"Timeout server-side: sem report após "
                f"{job.timeout_seconds + 60}s de execução"
            )
            job.finished_at = now
            session.add(job)
            _release_worker(session, worker, job.id)
            actions.append((job.id, "timeout"))
            continue

        # 2) Órfão: worker sumiu (sem heartbeat) ou nem existe mais.
        if worker is None or worker.last_heartbeat_at < orphan_cutoff:
            if job.attempt < job.max_attempts:
                job.status = JobStatus.pending
                job.worker_id = None
                job.claimed_at = None
                job.started_at = None
                job.error = "Requeued: worker sem heartbeat"
                actions.append((job.id, "requeued"))
            else:
                job.status = JobStatus.failed
                job.error = (
                    "Worker sem heartbeat e sem tentativas restantes; "
                    "verifique a máquina e crie um novo job se necessário"
                )
                job.finished_at = now
                actions.append((job.id, "failed"))
            session.add(job)
            _release_worker(session, worker, job.id)

    session.commit()
    for job_id, action in actions:
        logger.warning("reaper: job %s -> %s", job_id, action)
    return actions


def _release_worker(session: Session, worker: Worker | None, job_id: int) -> None:
    if worker is not None and worker.current_job_id == job_id:
        worker.current_job_id = None
        session.add(worker)


async def reaper_loop(stop: asyncio.Event) -> None:
    from server.models import utcnow

    settings = get_settings()
    while not stop.is_set():
        try:
            with Session(get_engine()) as session:
                run_reaper_once(session, utcnow())
        except Exception:
            logger.exception("reaper: erro na passada")
        try:
            await asyncio.wait_for(
                stop.wait(), timeout=settings.reaper_interval_seconds
            )
        except asyncio.TimeoutError:
            pass
