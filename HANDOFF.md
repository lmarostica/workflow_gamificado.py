# Handoff — API Contábil "contador 24/7"

**Data:** 2026-06-29 · **Branch:** `claude/accounting-api-concept-bjv4fb` ·
**Repo:** `lmarostica/workflow_gamificado.py`

Documento de passagem de bastão: o que foi decidido, o que foi entregue, o estado atual e os
próximos passos.

---

## 1. O que é o projeto
Uma **API contábil** que faz escrituração em tempo real: recebe documentos financeiros
(NF-e/NFS-e XML, extratos OFX, comprovantes, planilhas) e devolve a **escrituração contábil
(partida dobrada)** de cada transação, com **rastreabilidade completa** até o documento de origem.

## 2. Decisões tomadas (com o usuário)
| Tema | Decisão |
|------|---------|
| Posicionamento | **Copiloto do contador** — gera rascunhos auditáveis; humano aprova. Não substitui o contador (CRC). |
| Documentos | **Estruturados primeiro** (NF-e/NFS-e XML + OFX/CNAB); PDF/xlsx em fase posterior. |
| Regime tributário | **Simples Nacional**, escrituração **completa** (partida dobrada). |
| Plano de contas | **Da própria empresa**, sincronizado do "sistema único" (não um referencial fixo). |
| Base de conhecimento | **Lançamentos anteriores** da empresa alimentam a classificação (memória + few-shot). |
| Estratégia de execução | **PoC simples antes da API** — validar acurácia (a parte arriscada) antes da plataforma. |

## 3. Entregáveis no repositório
- **`CONCEITO.md`** — conceito e arquitetura: visão, modelo de domínio, pipeline assíncrono,
  contrato da API (insumos, formas de envio, devolução do lançamento), extração, conciliação,
  motor contábil, ledger/rastreabilidade, confiança/revisão, riscos e roadmap.
- **`SIMPLES_NACIONAL.md`** — recorte contábil do regime: anexos/Fator R, cálculo do DAS,
  obrigações (PGDAS-D/DEFIS), por que escrituração completa, plano de contas, catálogo de
  eventos → lançamentos, impacto no pipeline.
- **`poc/`** — Prova de Conceito executável (ver §4).

## 4. PoC (`poc/`) — estado e resultado
CLI em Python (sem API/banco/fila) que prova o núcleo: `NF-e XML → evento → classificação →
partida dobrada → saída com rastreabilidade`, mais um modo **backtest** que mede acurácia contra
o histórico.

**Componentes:** `nfe.py` (parser + validação vs vNF), `base_conhecimento.py` (memória por
contraparte + retrieval few-shot), `classificador.py` (memória → LLM Claude → heurística),
`partida.py` (partida dobrada balanceada), `cli.py` (`processar`/`backtest`), `sample_data/`
(dados sintéticos), `README.md`.

**Como rodar (da raiz do repo):**
```bash
pip install -r poc/requirements.txt
python -m poc.cli processar poc/sample_data     # gera CSV+JSON
python -m poc.cli backtest  poc/sample_data     # mede acurácia
# LLM opcional: export ANTHROPIC_API_KEY=... (padrão claude-sonnet-4-6)
```

**Resultado verificado (dados sintéticos, modo só-regras, sem API key):**
- Acurácia geral **75% (3/4)**.
- **Memória determinística: 100% (2/2)** — contrapartes recorrentes.
- Único erro: NF de software de **fornecedor novo** (sem histórico) → caiu na heurística.
  É exatamente o caso que o **LLM** resolveria (não testado aqui por falta de API key no ambiente).

## 5. Qualidade / ferramentas
- **ruff** instalado e configurado (`poc/ruff.toml`); `ruff check` + `ruff format` limpos.
- **ruflo** (ruvnet/ruflo) v3.15.0 instalado globalmente via npm. ⚠️ Ambiente remoto é efêmero —
  reinstalar localmente com `npm install -g ruflo@latest` ou usar `npx ruflo@latest`.

## 6. Decisões em aberto
- Conector do plano de contas / histórico: **push** do sistema único vs. **pull** agendado.
- Mapeamento `conta_referencial_sped` (Simples é dispensado de ECD — manter só p/ padronização?).
- NFS-e: definir municípios / adotar padrão nacional (DPS).
- Sublimite ICMS/ISS, Fator R (precisa de dados de folha) para serviços.

## 7. Próximos passos sugeridos (em ordem)
1. **Rodar o backtest com dados reais de 1 empresa** (trocar `poc/sample_data/`) — é o teste que
   decide se vale construir a API.
2. **Exercitar o caminho do LLM** (com `ANTHROPIC_API_KEY`) e medir o ganho sobre o modo só-regras.
3. Adicionar **OFX** como 2ª fonte (caixa) e iniciar **conciliação** NF ↔ extrato.
4. Só então: scaffold da **API** (FastAPI + fila + ledger) usando a PoC como motor.

## 8. Como retomar
```bash
git checkout claude/accounting-api-concept-bjv4fb
git pull origin claude/accounting-api-concept-bjv4fb
# ler CONCEITO.md, SIMPLES_NACIONAL.md e poc/README.md
```
