def test_crud_rpa(client, client_headers, make_rpa):
    rpa = make_rpa(
        "importar_extrato",
        params_schema={
            "type": "object",
            "properties": {"empresa": {"type": "string"}},
            "required": ["empresa"],
        },
        default_timeout_seconds=600,
    )
    assert rpa["name"] == "importar_extrato"
    assert rpa["enabled"] is True
    assert rpa["default_timeout_seconds"] == 600

    resp = client.get("/rpas/importar_extrato", headers=client_headers)
    assert resp.status_code == 200
    assert resp.json()["params_schema"]["required"] == ["empresa"]

    resp = client.get("/rpas", headers=client_headers)
    assert [r["name"] for r in resp.json()] == ["importar_extrato"]

    resp = client.patch(
        "/rpas/importar_extrato",
        json={"enabled": False, "description": "atualizado"},
        headers=client_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["enabled"] is False
    assert resp.json()["description"] == "atualizado"

    resp = client.delete("/rpas/importar_extrato", headers=client_headers)
    assert resp.status_code == 204
    assert client.get("/rpas/importar_extrato", headers=client_headers).status_code == 404


def test_nome_duplicado(client, client_headers, make_rpa):
    make_rpa("x")
    resp = client.post("/rpas", json={"name": "x"}, headers=client_headers)
    assert resp.status_code == 409


def test_schema_malformado(client, client_headers):
    resp = client.post(
        "/rpas",
        json={"name": "y", "params_schema": {"type": "nao-existe"}},
        headers=client_headers,
    )
    assert resp.status_code == 422


def test_delete_com_jobs(client, client_headers, make_rpa, make_job):
    make_rpa("z")
    make_job("z")
    resp = client.delete("/rpas/z", headers=client_headers)
    assert resp.status_code == 409


def test_auth(client, client_headers):
    assert client.get("/rpas").status_code == 401
    assert client.get("/rpas", headers={"X-API-Key": "errada"}).status_code == 403
    assert client.get("/health").status_code == 200
