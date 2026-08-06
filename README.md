# Orquestrador de RPAs — SCI Único

API central que recebe requisições de execução de RPAs, enfileira com prioridade e coordena a execução em agentes instalados nas máquinas Windows onde o **SCI Único** roda. O SCI Único não tem API — a automação é feita por scripts de RPA já existentes; este projeto é o orquestrador deles.

```
Cliente (curl / sistema interno)
   │  POST /jobs                     (X-API-Key de cliente)
   ▼
API FastAPI + SQLite ──── fila com prioridade · claim atômico · reaper de órfãos
   ▲
   │  register / claim / heartbeat / report   (X-API-Key de worker)
   │
Agente Windows (1 RPA por vez) ── subprocess ── script RPA ── SCI Único
```

Conceitos:

- **RPA** — entrada no catálogo (`POST /rpas`): nome, descrição, schema de parâmetros opcional (JSON Schema) e timeout padrão. O nome liga o catálogo ao `rpas.yaml` do agente.
- **Job** — uma requisição de execução: RPA + parâmetros + prioridade. Estados: `pending → running → succeeded | failed | timeout`, além de `cancelled` (só a partir de `pending`).
- **Worker** — um agente registrado. Executa **um job por vez** (o SCI Único é aplicação desktop; duas automações simultâneas na mesma sessão não funcionam).

## 1. Rodar a API (servidor)

Requisitos: Python 3.11+.

```bash
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# gere duas chaves e cole no .env:
python -c "import secrets; print(secrets.token_urlsafe(32))"

uvicorn server.main:app --host 0.0.0.0 --port 8000
```

- Documentação interativa em `http://servidor:8000/docs`.
- Health check sem autenticação: `GET /health`.
- O banco é o arquivo definido em `ORCH_DB_PATH` (padrão `orquestrador.db`). Faça backup periódico desse arquivo (junto com `-wal`/`-shm`, ou após parar a API).
- **Rode com um único processo** (o padrão do uvicorn). A garantia de atomicidade da fila pressupõe um processo só; não use `--workers N` sem revisar o design.

## 2. Configurar o agente na máquina Windows

Na máquina onde o SCI Único e os scripts de RPA estão instalados:

1. Instale Python 3.11 e copie a pasta `agent/` (ex.: para `C:\orquestrador\`).
2. `pip install -r agent\requirements-agent.txt`
3. Copie `agent\config.example.yaml` → `config.yaml` e preencha `api_url`, `api_key` (a chave de worker do `.env` do servidor) e um `worker_id` único por máquina.
4. Copie `agent\rpas.example.yaml` → `rpas.yaml` e mapeie cada RPA para o comando local que o executa (os campos estão comentados no exemplo).
5. Rode:

```bat
python -m agent.worker --config C:\orquestrador\config.yaml --rpas C:\orquestrador\rpas.yaml
```

Para iniciar junto com o Windows, crie uma tarefa no **Agendador de Tarefas** disparada "ao efetuar logon", com reinício em caso de falha.

> **Importante:** RPAs que controlam a interface do SCI Único precisam de uma **sessão Windows interativa e logada** (não funciona como serviço nem com a tela bloqueada, dependendo da técnica de automação usada pelos scripts).

### Como o agente entrega os parâmetros ao script

Definido por RPA no `rpas.yaml` (`params_as`):

| modo | como o script recebe `{"empresa": "ACME"}` |
|---|---|
| `args` | `--empresa ACME` na linha de comando |
| `env` | variável de ambiente `RPA_PARAM_EMPRESA=ACME` |
| `json_file` | caminho de um `.json` temporário como último argumento |

Convenção de resultado: exit code `0` = sucesso; qualquer outro = falha. Os últimos 64 KB de stdout/stderr são enviados no report e ficam visíveis em `GET /jobs/{id}` (`log_tail`).

## 3. Cadastrar um RPA e disparar uma execução

```bash
API=http://servidor:8000
KEY="sua-chave-de-cliente"

# cadastrar o RPA no catálogo (uma vez)
curl -s -X POST $API/rpas -H "X-API-Key: $KEY" -H "Content-Type: application/json" -d '{
  "name": "conciliacao_bancaria",
  "description": "Conciliação bancária no SCI Único",
  "default_timeout_seconds": 3600,
  "params_schema": {
    "type": "object",
    "properties": {"empresa": {"type": "string"}, "competencia": {"type": "string"}},
    "required": ["empresa", "competencia"]
  }
}'

# criar um job (prioridade menor = executa antes; padrão 100)
curl -s -X POST $API/jobs -H "X-API-Key: $KEY" -H "Content-Type: application/json" -d '{
  "rpa": "conciliacao_bancaria",
  "params": {"empresa": "ACME", "competencia": "2026-07"},
  "priority": 50
}'

# acompanhar
curl -s $API/jobs/1 -H "X-API-Key: $KEY"
curl -s "$API/jobs?status=pending" -H "X-API-Key: $KEY"
curl -s $API/workers -H "X-API-Key: $KEY"

# cancelar (só enquanto pending)
curl -s -X POST $API/jobs/1/cancel -H "X-API-Key: $KEY"
```

## 4. Operação

- **Estados do job**: `pending` (na fila) → `running` (um worker executando) → `succeeded` / `failed` / `timeout`; `cancelled` só a partir de `pending`.
- **Órfãos**: se o worker parar de enviar heartbeat por mais de `ORCH_ORPHAN_TIMEOUT_SECONDS` (padrão 120 s) com um job `running`, o reaper age: reenfileira se o job ainda tiver tentativas (`max_attempts` > tentativa atual) ou marca `failed`. O padrão é `max_attempts: 1` — **de propósito**: um RPA interrompido no meio pode ter feito parte dos lançamentos no SCI, então a reexecução automática é opt-in por job (`"max_attempts": 2` no `POST /jobs`) e o caso padrão pede um humano avaliando antes de criar novo job.
- **Timeout**: o agente mata o processo do RPA (e toda a árvore) ao exceder o timeout do job e reporta `timeout`. Se o próprio agente morrer, o servidor marca `timeout` por conta própria após `timeout_seconds + 60 s` sem report.
- **Reprocessar**: crie um novo job (`POST /jobs`); jobs finalizados são histórico e não mudam de estado.
- **Limitações conhecidas (v1)**: API em processo único; cancelamento só de jobs `pending`; sem encadeamento de jobs.

## 5. Desenvolvimento e testes

```bash
pip install -r requirements-dev.txt
python -m pytest tests/ -q
```

A suíte cobre o catálogo, a fila (incluindo atomicidade de claims concorrentes), o reaper, o executor do agente e um teste ponta a ponta com API real + agente executando `scripts/fake_rpa.py`.

## Roadmap

- **Encadeamento de jobs** (job B só roda após A ter sucesso): o design já prevê — basta adicionar `depends_on_job_id` + estado `waiting`; o claim ignora `waiting` e o report de sucesso promove dependentes a `pending`.
- Cancelamento de job em execução (o protocolo de heartbeat já sinaliza 409 para o agente abortar; falta expor no endpoint de cancel).
- Painel web de acompanhamento.

---

*Nota: o `app.py` na raiz é um protótipo antigo de checklist gamificado, sem relação com o orquestrador.*
