import pytest
from fastapi.testclient import TestClient

from server.config import get_settings
from server.db import reset_engine

CLIENT_KEY = "test-client-key"
WORKER_KEY = "test-worker-key"


@pytest.fixture
def client(tmp_path, monkeypatch):
    # DB em arquivo (não :memory:) para exercitar WAL e locking reais.
    monkeypatch.setenv("ORCH_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("ORCH_CLIENT_API_KEY", CLIENT_KEY)
    monkeypatch.setenv("ORCH_WORKER_API_KEY", WORKER_KEY)
    monkeypatch.setenv("ORCH_ORPHAN_TIMEOUT_SECONDS", "120")
    get_settings.cache_clear()
    reset_engine()

    from server.main import create_app

    with TestClient(create_app()) as test_client:
        yield test_client

    reset_engine()
    get_settings.cache_clear()


@pytest.fixture
def client_headers():
    return {"X-API-Key": CLIENT_KEY}


@pytest.fixture
def worker_headers():
    return {"X-API-Key": WORKER_KEY}


@pytest.fixture
def make_rpa(client, client_headers):
    def _make(name="conciliacao_bancaria", **overrides):
        body = {"name": name, "description": "RPA de teste", **overrides}
        resp = client.post("/rpas", json=body, headers=client_headers)
        assert resp.status_code == 201, resp.text
        return resp.json()

    return _make


@pytest.fixture
def make_job(client, client_headers):
    def _make(rpa="conciliacao_bancaria", **overrides):
        resp = client.post(
            "/jobs", json={"rpa": rpa, **overrides}, headers=client_headers
        )
        assert resp.status_code == 201, resp.text
        return resp.json()

    return _make


@pytest.fixture
def register_worker(client, worker_headers):
    def _register(worker_id="worker-01", rpas=("conciliacao_bancaria",)):
        resp = client.post(
            "/worker/register",
            json={"worker_id": worker_id, "hostname": "test", "rpas": list(rpas)},
            headers=worker_headers,
        )
        assert resp.status_code == 200, resp.text
        return resp.json()

    return _register
