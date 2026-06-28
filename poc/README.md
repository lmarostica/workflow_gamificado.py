# PoC — Escriturador contábil a partir de NF-e

Prova de conceito **mínima** da ideia do `../CONCEITO.md`: transformar documentos em
**lançamentos contábeis** (partida dobrada) com **confiança, justificativa e rastreabilidade** —
e, principalmente, **medir a acurácia** contra o histórico real da empresa (backtest).

É deliberadamente **simples**: um script de linha de comando, sem API, sem banco, sem fila.
O objetivo é testar a parte *arriscada* (dá para classificar certo?) antes de construir a
plataforma. Escopo: **NF-e XML**, regime **Simples Nacional**, escrituração completa.

## Como funciona

```
NF-e XML  ──parse──►  EventoEconomico  ──classifica──►  conta  ──►  partida dobrada  ──►  saída
                                          │
                  1) memória: contraparte → conta histórica mais usada
                  2) LLM (Claude): contas do plano + exemplos do histórico (few-shot)
                  3) heurística de fallback
```

A classificação **só escolhe contas do plano da empresa** e se apoia nos **lançamentos
anteriores** como base de conhecimento (resolve o cold-start). Cada lançamento sai com a
rastreabilidade até o arquivo (hash), a chave da NF-e e o campo de origem.

## Instalação

```bash
pip install -r requirements.txt        # runtime (anthropic)
pip install -r requirements-dev.txt    # + ruff (lint/format)
```

## Uso

A partir da raiz do repositório:

```bash
# Gera os lançamentos sugeridos (CSV + JSON) na própria pasta de dados
python -m poc.cli processar poc/sample_data

# Mede acurácia: conta sugerida × conta real (precisa de gabarito.csv)
python -m poc.cli backtest poc/sample_data
```

### Classificação por LLM (opcional)
Sem chave, roda em **modo só-regras** (memória + heurística). Para ativar o LLM:

```bash
export ANTHROPIC_API_KEY=sk-...
export ESCRITURADOR_MODELO=claude-sonnet-4-6   # opcional; padrão já é este
python -m poc.cli backtest poc/sample_data
```

## Dados (pasta `sample_data/`, sintéticos)

| Arquivo | Papel |
|---------|-------|
| `plano_de_contas.csv` | Plano de contas da empresa (com `alvo_classificacao`). |
| `lancamentos_historicos.csv` | Base de conhecimento (histórico já classificado). |
| `nfe_*.xml` | Notas a escriturar (o "mês recente"). |
| `gabarito.csv` | `chave_nfe → conta_real`, usado só no backtest. |

### Apontando para dados reais
Troque os arquivos de `sample_data/` pelos reais de **uma empresa** (NF-e XML + plano +
histórico + gabarito do mês a avaliar) e rode o `backtest`. O número de acurácia é o que diz se
vale construir a API.

## O que a PoC mostra (resultado nos dados sintéticos)
- **Memória determinística** (contrapartes recorrentes): acerto alto, sem custo de LLM.
- O caso que **só o LLM resolve**: fornecedor novo, sem histórico — no modo só-regras ele cai na
  heurística e erra, evidenciando exatamente onde a IA agrega valor.

## Fora do escopo (continua no `CONCEITO.md`)
Conciliação multi-documento, OFX/PDF/xlsx, persistência, autenticação, webhooks, UI.
