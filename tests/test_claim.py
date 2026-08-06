from concurrent.futures import ThreadPoolExecutor


def test_fila_vazia_204(client, worker_headers, register_worker):
    register_worker()
    resp = client.post(
        "/worker/claim", json={"worker_id": "worker-01"}, headers=worker_headers
    )
    assert resp.status_code == 204


def test_worker_nao_registrado(client, worker_headers):
    resp = client.post(
        "/worker/claim", json={"worker_id": "fantasma"}, headers=worker_headers
    )
    assert resp.status_code == 404


def test_ordenacao_prioridade_e_fifo(
    client, client_headers, worker_headers, make_rpa, make_job, register_worker
):
    make_rpa()
    register_worker()
    normal_1 = make_job(priority=100)
    normal_2 = make_job(priority=100)
    urgente = make_job(priority=1)

    ordem_esperada = [urgente["id"], normal_1["id"], normal_2["id"]]
    for esperado in ordem_esperada:
        resp = client.post(
            "/worker/claim", json={"worker_id": "worker-01"}, headers=worker_headers
        )
        assert resp.status_code == 200
        job = resp.json()
        assert job["id"] == esperado
        assert job["status"] == "running"
        assert job["attempt"] == 1
        # finaliza para liberar o worker para o próximo claim
        client.post(
            f"/worker/jobs/{job['id']}/report",
            json={"worker_id": "worker-01", "status": "succeeded", "exit_code": 0},
            headers=worker_headers,
        )


def test_claim_filtra_por_rpas_suportados(
    client, worker_headers, make_rpa, make_job, register_worker
):
    make_rpa("suportado")
    make_rpa("nao_suportado")
    register_worker(rpas=["suportado"])
    job_fora = make_job("nao_suportado")
    job_dentro = make_job("suportado")

    resp = client.post(
        "/worker/claim", json={"worker_id": "worker-01"}, headers=worker_headers
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == job_dentro["id"]
    assert job_fora["id"] != job_dentro["id"]


def test_worker_ocupado_409(
    client, worker_headers, make_rpa, make_job, register_worker
):
    make_rpa()
    register_worker()
    make_job()
    make_job()

    resp = client.post(
        "/worker/claim", json={"worker_id": "worker-01"}, headers=worker_headers
    )
    assert resp.status_code == 200

    resp = client.post(
        "/worker/claim", json={"worker_id": "worker-01"}, headers=worker_headers
    )
    assert resp.status_code == 409


def test_atomicidade_claims_concorrentes(
    client, worker_headers, make_rpa, make_job, register_worker
):
    """N workers disputam 1 job: exatamente um leva, os demais recebem 204."""
    make_rpa()
    n_workers = 8
    for i in range(n_workers):
        register_worker(worker_id=f"w-{i}")
    job = make_job()

    def do_claim(i):
        return client.post(
            "/worker/claim", json={"worker_id": f"w-{i}"}, headers=worker_headers
        )

    with ThreadPoolExecutor(max_workers=n_workers) as pool:
        responses = list(pool.map(do_claim, range(n_workers)))

    winners = [r for r in responses if r.status_code == 200]
    empty = [r for r in responses if r.status_code == 204]
    assert len(winners) == 1, [r.status_code for r in responses]
    assert len(empty) == n_workers - 1
    assert winners[0].json()["id"] == job["id"]


def test_ciclo_completo_report(
    client, client_headers, worker_headers, make_rpa, make_job, register_worker
):
    make_rpa()
    register_worker()
    job = make_job()

    claimed = client.post(
        "/worker/claim", json={"worker_id": "worker-01"}, headers=worker_headers
    ).json()
    assert claimed["started_at"] is not None

    resp = client.post(
        f"/worker/jobs/{job['id']}/heartbeat",
        json={"worker_id": "worker-01"},
        headers=worker_headers,
    )
    assert resp.status_code == 200

    resp = client.post(
        f"/worker/jobs/{job['id']}/report",
        json={
            "worker_id": "worker-01",
            "status": "succeeded",
            "exit_code": 0,
            "result": {"lancamentos": 42},
            "log_tail": "tudo certo",
        },
        headers=worker_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "succeeded"
    assert body["result"] == {"lancamentos": 42}
    assert body["finished_at"] is not None

    # report idempotente
    resp = client.post(
        f"/worker/jobs/{job['id']}/report",
        json={"worker_id": "worker-01", "status": "succeeded", "exit_code": 0},
        headers=worker_headers,
    )
    assert resp.status_code == 200

    # desfecho conflitante -> 409
    resp = client.post(
        f"/worker/jobs/{job['id']}/report",
        json={"worker_id": "worker-01", "status": "failed"},
        headers=worker_headers,
    )
    assert resp.status_code == 409

    # worker liberado para o próximo claim
    resp = client.post(
        "/worker/claim", json={"worker_id": "worker-01"}, headers=worker_headers
    )
    assert resp.status_code == 204

    # visão do cliente reflete o desfecho
    resp = client.get(f"/jobs/{job['id']}", headers=client_headers)
    assert resp.json()["status"] == "succeeded"


def test_report_de_worker_errado_409(
    client, worker_headers, make_rpa, make_job, register_worker
):
    make_rpa()
    register_worker(worker_id="w-a")
    register_worker(worker_id="w-b")
    job = make_job()
    client.post("/worker/claim", json={"worker_id": "w-a"}, headers=worker_headers)

    resp = client.post(
        f"/worker/jobs/{job['id']}/report",
        json={"worker_id": "w-b", "status": "succeeded"},
        headers=worker_headers,
    )
    assert resp.status_code == 409

    resp = client.post(
        f"/worker/jobs/{job['id']}/heartbeat",
        json={"worker_id": "w-b"},
        headers=worker_headers,
    )
    assert resp.status_code == 409


def test_report_failed(client, worker_headers, make_rpa, make_job, register_worker):
    make_rpa()
    register_worker()
    job = make_job()
    client.post(
        "/worker/claim", json={"worker_id": "worker-01"}, headers=worker_headers
    )
    resp = client.post(
        f"/worker/jobs/{job['id']}/report",
        json={
            "worker_id": "worker-01",
            "status": "failed",
            "exit_code": 3,
            "error": "SCI não abriu",
        },
        headers=worker_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "failed"
    assert resp.json()["exit_code"] == 3


def test_auth_chave_cliente_nao_acessa_worker(client, client_headers):
    resp = client.post(
        "/worker/claim", json={"worker_id": "x"}, headers=client_headers
    )
    assert resp.status_code == 403
