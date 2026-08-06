"""Carrega e valida a configuração do agente (config.yaml + rpas.yaml)."""

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class RpaSpec:
    name: str
    command: list[str]
    workdir: str | None = None
    timeout_seconds: int = 3600
    # como entregar os params ao script:
    #   args      -> --chave valor na linha de comando
    #   env       -> variáveis RPA_PARAM_<CHAVE>
    #   json_file -> caminho de um .json temporário como último argumento
    params_as: str = "args"


@dataclass
class AgentConfig:
    api_url: str
    api_key: str
    worker_id: str
    poll_interval_seconds: float = 5.0
    heartbeat_interval_seconds: float = 30.0
    log_tail_kb: int = 64
    rpas: dict[str, RpaSpec] = field(default_factory=dict)


def load_config(config_path: str, rpas_path: str) -> AgentConfig:
    raw = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    for required in ("api_url", "api_key", "worker_id"):
        if not raw.get(required):
            raise ValueError(f"config.yaml: campo obrigatório ausente: {required}")

    raw_rpas = yaml.safe_load(Path(rpas_path).read_text(encoding="utf-8")) or {}
    rpas: dict[str, RpaSpec] = {}
    for name, spec in (raw_rpas.get("rpas") or {}).items():
        command = spec.get("command")
        if not command or not isinstance(command, list):
            raise ValueError(
                f"rpas.yaml: '{name}' precisa de 'command' como lista de strings"
            )
        params_as = spec.get("params_as", "args")
        if params_as not in ("args", "env", "json_file"):
            raise ValueError(
                f"rpas.yaml: '{name}': params_as deve ser args, env ou json_file"
            )
        rpas[name] = RpaSpec(
            name=name,
            command=[str(part) for part in command],
            workdir=spec.get("workdir"),
            timeout_seconds=int(spec.get("timeout_seconds", 3600)),
            params_as=params_as,
        )
    if not rpas:
        raise ValueError("rpas.yaml: nenhum RPA configurado")

    return AgentConfig(
        api_url=str(raw["api_url"]).rstrip("/"),
        api_key=str(raw["api_key"]),
        worker_id=str(raw["worker_id"]),
        poll_interval_seconds=float(raw.get("poll_interval_seconds", 5)),
        heartbeat_interval_seconds=float(raw.get("heartbeat_interval_seconds", 30)),
        log_tail_kb=int(raw.get("log_tail_kb", 64)),
        rpas=rpas,
    )
