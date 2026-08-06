"""Executa um RPA local via subprocess, com timeout e captura de saída."""

import json
import logging
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import psutil

from agent.config import RpaSpec

logger = logging.getLogger("agente.executor")

CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0


@dataclass
class ExecutionResult:
    status: str  # succeeded | failed | timeout
    exit_code: int | None
    log_tail: str
    error: str | None = None


def build_command(spec: RpaSpec, params: dict) -> tuple[list[str], dict | None, str | None]:
    """Retorna (command, env_extra, temp_file) conforme params_as."""
    command = list(spec.command)
    env_extra: dict | None = None
    temp_file: str | None = None

    if not params:
        return command, env_extra, temp_file

    if spec.params_as == "args":
        for key, value in params.items():
            command.append(f"--{key}")
            command.append(
                json.dumps(value, ensure_ascii=False)
                if isinstance(value, (dict, list))
                else str(value)
            )
    elif spec.params_as == "env":
        env_extra = {
            f"RPA_PARAM_{key.upper()}": (
                json.dumps(value, ensure_ascii=False)
                if isinstance(value, (dict, list))
                else str(value)
            )
            for key, value in params.items()
        }
    elif spec.params_as == "json_file":
        fd = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        )
        json.dump(params, fd, ensure_ascii=False)
        fd.close()
        temp_file = fd.name
        command.append(temp_file)

    return command, env_extra, temp_file


def _kill_tree(pid: int) -> None:
    """Mata o processo e todos os descendentes (o RPA pode abrir o SCI etc.)."""
    try:
        parent = psutil.Process(pid)
    except psutil.NoSuchProcess:
        return
    procs = parent.children(recursive=True) + [parent]
    for proc in procs:
        try:
            proc.kill()
        except psutil.NoSuchProcess:
            pass
    psutil.wait_procs(procs, timeout=10)


def run_rpa(
    spec: RpaSpec,
    params: dict,
    timeout_seconds: int | None = None,
    log_tail_bytes: int = 64 * 1024,
    on_start=None,
) -> ExecutionResult:
    timeout = timeout_seconds or spec.timeout_seconds
    command, env_extra, temp_file = build_command(spec, params)

    env = None
    if env_extra:
        import os

        env = {**os.environ, **env_extra}

    logger.info("executando %s: %s (timeout %ss)", spec.name, command, timeout)
    try:
        process = subprocess.Popen(
            command,
            cwd=spec.workdir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=CREATE_NO_WINDOW,
        )
    except OSError as exc:
        return ExecutionResult(
            status="failed",
            exit_code=None,
            log_tail="",
            error=f"Falha ao iniciar o comando: {exc}",
        )

    if on_start is not None:
        on_start(process.pid)

    try:
        output, _ = process.communicate(timeout=timeout)
        tail = output[-log_tail_bytes:] if output else ""
        if process.returncode == 0:
            return ExecutionResult(status="succeeded", exit_code=0, log_tail=tail)
        return ExecutionResult(
            status="failed",
            exit_code=process.returncode,
            log_tail=tail,
            error=f"Processo terminou com exit code {process.returncode}",
        )
    except subprocess.TimeoutExpired:
        _kill_tree(process.pid)
        output = ""
        try:
            output, _ = process.communicate(timeout=10)
        except Exception:
            pass
        return ExecutionResult(
            status="timeout",
            exit_code=None,
            log_tail=(output or "")[-log_tail_bytes:],
            error=f"RPA excedeu o timeout de {timeout}s e foi finalizado",
        )
    finally:
        if temp_file:
            Path(temp_file).unlink(missing_ok=True)
