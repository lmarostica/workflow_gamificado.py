import json
import sys
import time
from pathlib import Path

from agent.config import RpaSpec, load_config
from agent.executor import build_command, run_rpa

FAKE_RPA = str(Path(__file__).resolve().parent.parent / "scripts" / "fake_rpa.py")


def _spec(**overrides) -> RpaSpec:
    defaults = dict(
        name="fake",
        command=[sys.executable, FAKE_RPA],
        timeout_seconds=30,
        params_as="args",
    )
    defaults.update(overrides)
    return RpaSpec(**defaults)


def test_sucesso_com_params_como_args():
    result = run_rpa(_spec(), {"empresa": "ACME"})
    assert result.status == "succeeded"
    assert result.exit_code == 0
    assert "empresa=ACME" in result.log_tail


def test_exit_code_diferente_de_zero_e_failed():
    result = run_rpa(_spec(), {"exit-code": 3})
    assert result.status == "failed"
    assert result.exit_code == 3
    assert "exit code 3" in result.error


def test_timeout_mata_processo():
    start = time.monotonic()
    result = run_rpa(_spec(), {"sleep": 30}, timeout_seconds=1)
    elapsed = time.monotonic() - start
    assert result.status == "timeout"
    assert elapsed < 15
    assert "timeout" in result.error.lower()


def test_truncagem_do_log_tail():
    result = run_rpa(_spec(), {"spam-kb": 200}, log_tail_bytes=1024)
    assert result.status == "succeeded"
    assert len(result.log_tail.encode()) <= 1024


def test_comando_inexistente_e_failed():
    result = run_rpa(_spec(command=["/caminho/que/nao/existe.exe"]), {})
    assert result.status == "failed"
    assert "Falha ao iniciar" in result.error


def test_build_command_env():
    spec = _spec(params_as="env")
    command, env_extra, temp_file = build_command(
        spec, {"empresa": "ACME", "competencia": "2026-07"}
    )
    assert command == spec.command
    assert env_extra == {
        "RPA_PARAM_EMPRESA": "ACME",
        "RPA_PARAM_COMPETENCIA": "2026-07",
    }
    assert temp_file is None


def test_build_command_json_file():
    spec = _spec(params_as="json_file")
    command, env_extra, temp_file = build_command(spec, {"empresa": "ACME"})
    assert command[-1] == temp_file
    assert json.loads(Path(temp_file).read_text(encoding="utf-8")) == {
        "empresa": "ACME"
    }
    Path(temp_file).unlink()


def test_load_config_valida_campos(tmp_path):
    config_path = tmp_path / "config.yaml"
    rpas_path = tmp_path / "rpas.yaml"
    config_path.write_text(
        "api_url: http://x:8000\napi_key: k\nworker_id: w1\n", encoding="utf-8"
    )
    rpas_path.write_text(
        "rpas:\n  meu_rpa:\n    command: [python, x.py]\n    timeout_seconds: 60\n",
        encoding="utf-8",
    )
    config = load_config(str(config_path), str(rpas_path))
    assert config.worker_id == "w1"
    assert config.rpas["meu_rpa"].timeout_seconds == 60

    rpas_path.write_text("rpas:\n  quebrado:\n    workdir: /x\n", encoding="utf-8")
    try:
        load_config(str(config_path), str(rpas_path))
        raise AssertionError("deveria ter falhado sem command")
    except ValueError as exc:
        assert "command" in str(exc)
