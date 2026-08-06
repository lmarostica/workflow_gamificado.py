"""Cliente HTTP fino para os endpoints /worker/* da API de orquestração."""

import logging
import time

import httpx

logger = logging.getLogger("agente.api")


class JobConflict(Exception):
    """409: o job não pertence mais a este worker (requeado/cancelado)."""


class ApiClient:
    def __init__(
        self,
        api_url: str,
        api_key: str,
        worker_id: str,
        transport: httpx.BaseTransport | None = None,
    ):
        self.worker_id = worker_id
        self._http = httpx.Client(
            base_url=api_url,
            headers={"X-API-Key": api_key},
            timeout=30.0,
            transport=transport,
        )

    def register(self, rpas: list[str], hostname: str, agent_version: str) -> None:
        resp = self._http.post(
            "/worker/register",
            json={
                "worker_id": self.worker_id,
                "hostname": hostname,
                "agent_version": agent_version,
                "rpas": rpas,
            },
        )
        resp.raise_for_status()

    def claim(self) -> dict | None:
        resp = self._http.post("/worker/claim", json={"worker_id": self.worker_id})
        if resp.status_code == 204:
            return None
        resp.raise_for_status()
        return resp.json()

    def heartbeat(self, job_id: int) -> None:
        resp = self._http.post(
            f"/worker/jobs/{job_id}/heartbeat", json={"worker_id": self.worker_id}
        )
        if resp.status_code == 409:
            raise JobConflict(resp.text)
        resp.raise_for_status()

    def report(
        self,
        job_id: int,
        status: str,
        exit_code: int | None = None,
        result: dict | None = None,
        log_tail: str | None = None,
        error: str | None = None,
        max_retry_seconds: float = 300.0,
    ) -> None:
        """Reporta o desfecho com retry — o resultado não pode se perder
        por uma instabilidade de rede momentânea."""
        payload = {
            "worker_id": self.worker_id,
            "status": status,
            "exit_code": exit_code,
            "result": result,
            "log_tail": log_tail,
            "error": error,
        }
        delay = 2.0
        deadline = time.monotonic() + max_retry_seconds
        while True:
            try:
                resp = self._http.post(
                    f"/worker/jobs/{job_id}/report", json=payload
                )
                if resp.status_code == 409:
                    # Job requeado/cancelado no servidor; nada mais a fazer.
                    logger.warning("report do job %s rejeitado: %s", job_id, resp.text)
                    return
                resp.raise_for_status()
                return
            except httpx.HTTPError as exc:
                if time.monotonic() >= deadline:
                    logger.error(
                        "report do job %s perdido após retries: %s", job_id, exc
                    )
                    raise
                logger.warning(
                    "report do job %s falhou (%s); retry em %.0fs", job_id, exc, delay
                )
                time.sleep(delay)
                delay = min(delay * 2, 60.0)

    def close(self) -> None:
        self._http.close()
