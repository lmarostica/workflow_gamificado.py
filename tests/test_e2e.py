"""Ponta a ponta: API real (uvicorn) + loop do agente executando o fake_rpa."""

import sys
import threading
import time
from pathlib import Path

import httpx
import pytest
import uvicorn

from agent.api_client import ApiClient
from agent.config import AgentConfig, RpaSpec
from agent.worker import register_with_retry, run_loop
from server.config import get_settings
from server.db import reset_engine
from tests.conftest import CLIENT_KEY, WORKER_KEY

FAKE_RPA = str(Path(__file__).resolve().parent.parent / "scripts" / "fake_rpa.py")


@pytest.fixture
def api_url(tmp_path, monkeypatch):
    monkeypatch.setenv("ORCH_DB_PATH", str(tmp_path / "e2e.db"))
    monkeypatch.setenv("ORCH_CLIENT_API_KEY", CLIENT_KEY)
    monkeypatch.setenv("ORCH_WORKER_API_KEY", WORKER_KEY)
    get_settings.cache_clear()
    reset_engine()

    from server.main import create_app

    server = uvicorn.Server(
        uvicorn.Config(create_app(), host="127.0.0.1", port=0, log_level="warning")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 15
    while not server.started:
        assert time.monotonic() < deadline, "uvicorn não subiu"
        time.sleep(0.05)
    port = server.servers[0].sockets[0].getsockname()[1]

    yield f"http://127.0.0.1:{port}"

    server.should_exit = True
    thread.join(timeout=10)
    reset_engine()
    get_settings.cache_clear()


def test_fluxo_completo_job_executado_pelo_agente(api_url):
    http = httpx.Client(base_url=api_url, headers={"X-API-Key": CLIENT_KEY})

    resp = http.post(
        "/rpas", json={"name": "fake_rpa", "description": "RPA de teste e2e"}
    )
    assert resp.status_code == 201
    job_ok = http.post(
        "/jobs", json={"rpa": "fake_rpa", "params": {"empresa": "ACME"}}
    ).json()
    job_falha = http.post(
        "/jobs", json={"rpa": "fake_rpa", "params": {"exit-code": 2}}
    ).json()

    config = AgentConfig(
        api_url=api_url,
        api_key=WORKER_KEY,
        worker_id="agente-e2e",
        poll_interval_seconds=0.1,
        heartbeat_interval_seconds=1,
        rpas={
            "fake_rpa": RpaSpec(
                name="fake_rpa",
                command=[sys.executable, FAKE_RPA],
                timeout_seconds=30,
            )
        },
    )
    api = ApiClient(config.api_url, config.api_key, config.worker_id)
    stop = threading.Event()
    assert register_with_retry(config, api, stop)
    # 3 iterações: executa os 2 jobs e recebe um 204 na terceira
    run_loop(config, api, stop, max_iterations=3)
    api.close()

    final_ok = http.get(f"/jobs/{job_ok['id']}").json()
    assert final_ok["status"] == "succeeded"
    assert final_ok["exit_code"] == 0
    assert final_ok["worker_id"] == "agente-e2e"
    assert "empresa=ACME" in final_ok["log_tail"]

    final_falha = http.get(f"/jobs/{job_falha['id']}").json()
    assert final_falha["status"] == "failed"
    assert final_falha["exit_code"] == 2

    workers = http.get("/workers").json()
    assert workers[0]["worker_id"] == "agente-e2e"
    assert workers[0]["current_job_id"] is None
    http.close()
