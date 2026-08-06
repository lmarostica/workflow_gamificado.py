from datetime import timedelta

from sqlmodel import Session

from server.db import get_engine
from server.models import Job, JobStatus, Worker, utcnow
from server.services.reaper import run_reaper_once


def _session():
    return Session(get_engine())


def _setup_running_job(client, headers, make_rpa, make_job, register_worker, **job_kw):
    make_rpa()
    register_worker()
    job = make_job(**job_kw)
    resp = client.post(
        "/worker/claim", json={"worker_id": "worker-01"}, headers=headers
    )
    assert resp.status_code == 200
    return job["id"]


def test_orfao_vira_failed_sem_tentativas(
    client, worker_headers, make_rpa, make_job, register_worker
):
    job_id = _setup_running_job(
        client, worker_headers, make_rpa, make_job, register_worker
    )
    with _session() as s:
        actions = run_reaper_once(s, utcnow() + timedelta(seconds=300))
        assert actions == [(job_id, "failed")]
        job = s.get(Job, job_id)
        assert job.status == JobStatus.failed
        assert "heartbeat" in job.error
        worker = s.get(Worker, "worker-01")
        assert worker.current_job_id is None


def test_orfao_requeia_com_max_attempts(
    client, worker_headers, make_rpa, make_job, register_worker
):
    job_id = _setup_running_job(
        client, worker_headers, make_rpa, make_job, register_worker, max_attempts=2
    )
    with _session() as s:
        actions = run_reaper_once(s, utcnow() + timedelta(seconds=300))
        assert actions == [(job_id, "requeued")]
        job = s.get(Job, job_id)
        assert job.status == JobStatus.pending
        assert job.worker_id is None
        assert job.attempt == 1

    # re-claim funciona e incrementa attempt
    resp = client.post(
        "/worker/claim", json={"worker_id": "worker-01"}, headers=worker_headers
    )
    assert resp.status_code == 200
    assert resp.json()["attempt"] == 2


def test_heartbeat_recente_nao_e_orfao(
    client, worker_headers, make_rpa, make_job, register_worker
):
    job_id = _setup_running_job(
        client, worker_headers, make_rpa, make_job, register_worker
    )
    with _session() as s:
        actions = run_reaper_once(s, utcnow() + timedelta(seconds=30))
        assert actions == []
        assert s.get(Job, job_id).status == JobStatus.running


def test_timeout_duro(client, worker_headers, make_rpa, make_job, register_worker):
    job_id = _setup_running_job(
        client,
        worker_headers,
        make_rpa,
        make_job,
        register_worker,
        timeout_seconds=10,
    )
    # mantém heartbeat "fresco" simulando que o worker está vivo mas o job travou
    with _session() as s:
        worker = s.get(Worker, "worker-01")
        worker.last_heartbeat_at = utcnow() + timedelta(seconds=100)
        s.add(worker)
        s.commit()

        actions = run_reaper_once(s, utcnow() + timedelta(seconds=100))
        assert actions == [(job_id, "timeout")]
        job = s.get(Job, job_id)
        assert job.status == JobStatus.timeout


def test_heartbeat_apos_requeue_409(
    client, worker_headers, make_rpa, make_job, register_worker
):
    job_id = _setup_running_job(
        client, worker_headers, make_rpa, make_job, register_worker, max_attempts=2
    )
    with _session() as s:
        run_reaper_once(s, utcnow() + timedelta(seconds=300))

    resp = client.post(
        f"/worker/jobs/{job_id}/heartbeat",
        json={"worker_id": "worker-01"},
        headers=worker_headers,
    )
    assert resp.status_code == 409
