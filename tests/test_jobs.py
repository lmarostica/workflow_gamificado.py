def test_criar_e_consultar_job(client, client_headers, make_rpa, make_job):
    make_rpa(default_timeout_seconds=900)
    job = make_job(params={"empresa": "ACME"}, priority=10)
    assert job["status"] == "pending"
    assert job["priority"] == 10
    assert job["params"] == {"empresa": "ACME"}
    assert job["timeout_seconds"] == 900  # herdado do RPA

    resp = client.get(f"/jobs/{job['id']}", headers=client_headers)
    assert resp.status_code == 200
    assert resp.json()["rpa_name"] == "conciliacao_bancaria"


def test_job_rpa_inexistente(client, client_headers):
    resp = client.post("/jobs", json={"rpa": "nao_existe"}, headers=client_headers)
    assert resp.status_code == 404


def test_job_rpa_desabilitado(client, client_headers, make_rpa):
    make_rpa("desligado")
    client.patch("/rpas/desligado", json={"enabled": False}, headers=client_headers)
    resp = client.post("/jobs", json={"rpa": "desligado"}, headers=client_headers)
    assert resp.status_code == 409


def test_validacao_params_contra_schema(client, client_headers, make_rpa):
    make_rpa(
        "com_schema",
        params_schema={
            "type": "object",
            "properties": {"empresa": {"type": "string"}},
            "required": ["empresa"],
            "additionalProperties": False,
        },
    )
    resp = client.post(
        "/jobs", json={"rpa": "com_schema", "params": {}}, headers=client_headers
    )
    assert resp.status_code == 422

    resp = client.post(
        "/jobs",
        json={"rpa": "com_schema", "params": {"empresa": "ACME"}},
        headers=client_headers,
    )
    assert resp.status_code == 201


def test_listagem_com_filtros(client, client_headers, make_rpa, make_job):
    make_rpa("a")
    make_rpa("b")
    for _ in range(3):
        make_job("a")
    make_job("b")

    resp = client.get("/jobs?rpa=a", headers=client_headers)
    assert resp.json()["total"] == 3

    resp = client.get("/jobs?status=pending&limit=2", headers=client_headers)
    body = resp.json()
    assert body["total"] == 4
    assert len(body["items"]) == 2
    # mais recentes primeiro
    assert body["items"][0]["id"] > body["items"][1]["id"]


def test_cancel_somente_pending(client, client_headers, make_rpa, make_job):
    make_rpa()
    job = make_job()
    resp = client.post(f"/jobs/{job['id']}/cancel", headers=client_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"

    resp = client.post(f"/jobs/{job['id']}/cancel", headers=client_headers)
    assert resp.status_code == 409


def test_auth_worker_nao_acessa_rota_cliente(client, worker_headers):
    assert client.get("/jobs", headers=worker_headers).status_code == 403
