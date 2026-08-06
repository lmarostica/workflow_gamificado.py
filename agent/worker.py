"""Agente worker: faz polling na API, executa RPAs locais e reporta o resultado.

Uso (na máquina Windows com o SCI Único):
    python -m agent.worker --config C:\\orquestrador\\config.yaml \\
                           --rpas C:\\orquestrador\\rpas.yaml

Executa um job por vez — o SCI Único é uma aplicação desktop e não suporta
duas automações simultâneas na mesma sessão.
"""

import argparse
import logging
import signal
import socket
import threading
import time

import httpx

from agent.api_client import ApiClient, JobConflict
from agent.config import AgentConfig, load_config
from agent.executor import _kill_tree, run_rpa

AGENT_VERSION = "1.0.0"

logger = logging.getLogger("agente")


class HeartbeatThread(threading.Thread):
    """Envia heartbeat enquanto o RPA roda; num 409, pede abort do processo."""

    def __init__(self, api: ApiClient, job_id: int, interval: float):
        super().__init__(daemon=True)
        self.api = api
        self.job_id = job_id
        self.interval = interval
        self.stop_event = threading.Event()
        self.abort = threading.Event()

    def run(self) -> None:
        while not self.stop_event.wait(self.interval):
            try:
                self.api.heartbeat(self.job_id)
            except JobConflict:
                logger.warning(
                    "job %s foi requeado/cancelado no servidor; abortando",
                    self.job_id,
                )
                self.abort.set()
                return
            except httpx.HTTPError as exc:
                # Blip de rede: o reaper só age após vários heartbeats perdidos.
                logger.warning("heartbeat do job %s falhou: %s", self.job_id, exc)


def process_job(config: AgentConfig, api: ApiClient, job: dict) -> None:
    job_id = job["id"]
    rpa_name = job["rpa_name"]
    spec = config.rpas.get(rpa_name)
    if spec is None:
        # Defesa extra: o servidor filtra pelo register, mas o rpas.yaml
        # pode ter mudado desde então.
        api.report(
            job_id,
            status="failed",
            error=f"RPA '{rpa_name}' não configurado no rpas.yaml deste worker",
        )
        return

    hb = HeartbeatThread(api, job_id, config.heartbeat_interval_seconds)
    hb.start()

    process_holder: dict = {}

    def watch_abort():
        # Mata a árvore de processos se o servidor mandar abortar (409).
        while not hb.stop_event.is_set():
            if hb.abort.is_set():
                pid = process_holder.get("pid")
                if pid:
                    _kill_tree(pid)
                return
            time.sleep(1)

    threading.Thread(target=watch_abort, daemon=True).start()
    try:
        result = run_rpa(
            spec,
            job.get("params") or {},
            timeout_seconds=job.get("timeout_seconds"),
            log_tail_bytes=config.log_tail_kb * 1024,
            on_start=lambda pid: process_holder.update(pid=pid),
        )
    finally:
        hb.stop_event.set()

    if hb.abort.is_set():
        # Servidor já deu outro destino ao job; report seria rejeitado (409).
        logger.info("job %s abortado a pedido do servidor", job_id)
        return

    api.report(
        job_id,
        status=result.status,
        exit_code=result.exit_code,
        log_tail=result.log_tail,
        error=result.error,
    )
    logger.info("job %s finalizado: %s", job_id, result.status)


def run_loop(
    config: AgentConfig,
    api: ApiClient,
    stop: threading.Event,
    max_iterations: int | None = None,
) -> None:
    """Loop principal. max_iterations existe para os testes."""
    iterations = 0
    while not stop.is_set():
        if max_iterations is not None and iterations >= max_iterations:
            return
        iterations += 1
        try:
            job = api.claim()
        except httpx.HTTPError as exc:
            logger.warning("claim falhou: %s", exc)
            stop.wait(config.poll_interval_seconds)
            continue

        if job is None:
            stop.wait(config.poll_interval_seconds)
            continue

        logger.info("job %s recebido (%s)", job["id"], job["rpa_name"])
        process_job(config, api, job)


def register_with_retry(config: AgentConfig, api: ApiClient, stop: threading.Event) -> bool:
    delay = 2.0
    while not stop.is_set():
        try:
            api.register(
                rpas=sorted(config.rpas),
                hostname=socket.gethostname(),
                agent_version=AGENT_VERSION,
            )
            logger.info(
                "registrado como '%s' com %d RPAs", config.worker_id, len(config.rpas)
            )
            return True
        except httpx.HTTPError as exc:
            logger.warning("register falhou (%s); retry em %.0fs", exc, delay)
            stop.wait(delay)
            delay = min(delay * 2, 60.0)
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Agente worker de RPAs (SCI Único)")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--rpas", default="rpas.yaml")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    config = load_config(args.config, args.rpas)
    api = ApiClient(config.api_url, config.api_key, config.worker_id)

    stop = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())

    try:
        if register_with_retry(config, api, stop):
            run_loop(config, api, stop)
    finally:
        api.close()
        logger.info("agente encerrado")


if __name__ == "__main__":
    main()
