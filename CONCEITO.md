# API Contábil — Escrituração em Tempo Real ("contador 24/7")

> Documento de conceito e arquitetura. Versão 0.1 — base para discussão e para um futuro MVP.
> Status: proposta. Nada aqui ainda é código; é o desenho do produto e da arquitetura.

---

## 1. Visão e posicionamento

### O problema
Toda empresa gera um fluxo contínuo de documentos financeiros — notas fiscais (NF-e/NFS-e),
extratos bancários, comprovantes de pagamento, planilhas de controle. Hoje, transformar esses
documentos em **escrituração contábil** (lançamentos de débito e crédito) é um trabalho manual,
em lote (geralmente mensal), caro e sujeito a atraso. O contador recebe uma pilha de documentos
no fim do mês e precisa reconstruir, transação a transação, o que aconteceu.

### A ideia
Uma **API contábil** que recebe documentos financeiros à medida que eles surgem e devolve a
**escrituração contábil de cada transação**, com **rastreabilidade completa** até o documento de
origem. Em vez de um fechamento mensal manual, um fluxo contínuo e auditável — um "contador 24/7".

### Posicionamento: copiloto do contador (não substituto)
A API **não** substitui o contador responsável. Ela atua como um **copiloto**: gera os
lançamentos como **rascunho auditável**, com confiança e justificativa, e o contador
**revisa e aprova**. Isso é uma decisão de produto deliberada:

- **Reduz o risco jurídico.** No Brasil a escrituração tem responsável técnico (contador com
  registro no CRC) e fecha em obrigações acessórias (SPED). Uma máquina não assume essa
  responsabilidade; ela acelera quem assume.
- **Cria um ponto de confiança.** Lançamentos de baixa confiança vão para uma **fila de
  revisão**. O contador corrige, e o sistema aprende.
- **É mais fácil de vender.** "Elimino 80% do trabalho braçal e te dou rastreabilidade total"
  é uma promessa concreta; "demito o contador" não é.

### O que é / o que NÃO é (no escopo inicial)
| É | NÃO é (ainda) |
|---|---|
| Motor de pré-escrituração auditável | Sistema legal de registro que dispensa o contador |
| Geração de partidas dobradas em rascunho | Entrega autônoma de SPED sem revisão humana |
| Rastreabilidade documento → lançamento | Apuração fiscal completa / cálculo de todos os tributos |
| Foco inicial em documentos estruturados | Pipeline de OCR de PDF maduro (fase posterior) |

---

## 2. Modelo de domínio

O coração do sistema é separar **o que aconteceu economicamente** (o fato) **das suas
representações em documentos** (as evidências) **e da sua expressão contábil** (os lançamentos).
Essa separação é o que permite conciliação e rastreabilidade.

### Entidades canônicas

- **`Documento`** — um arquivo recebido (NF-e XML, OFX, comprovante PDF, xlsx). Guarda o arquivo
  original, seu `hash` (idempotência + auditoria), tipo, origem, data de recepção e o resultado
  bruto da extração. **Imutável** após ingestão.

- **`EventoEconomico`** — a transação **normalizada**, independente de quantos documentos a
  descrevem. É o "modelo canônico de transação". Ex.: *"pagamento de R$ 1.250,00 ao fornecedor
  ACME em 14/06/2026, referente à NF 12345"*. Um mesmo evento pode ser evidenciado por vários
  documentos (a NF, o comprovante e a linha do extrato).

- **`LancamentoContabil`** — a expressão contábil de um evento: uma **partida dobrada** com uma
  ou mais linhas de débito e crédito que **somam zero**. Aponta para o `EventoEconomico` e,
  através dele, para os `Documento`s de origem. Carrega `confianca` e `justificativa`.

- **`Conta`** — entrada do **plano de contas da própria empresa**, sincronizado a partir do
  **sistema único** (ver §4). Tem código, descrição, natureza (ativo/passivo/receita/despesa/
  resultado) e, opcionalmente, um **mapeamento para uma conta referencial SPED** (para
  padronização e export). A classificação (§7) só pode usar contas que existam neste plano.

- **`PlanoDeContas`** — o conjunto de `Conta`s de uma empresa, com **versão** e data de
  sincronização. É um insumo de configuração: a empresa o envia/atualiza antes (e ao longo) do
  processamento. Sem plano de contas vigente, não há classificação possível.

- **`Periodo`** — competência contábil (mês/ano); controla abertura/fechamento.

- **`Revisao`** — registro de uma intervenção humana: aprovação, correção ou rejeição de um
  lançamento, com autor e timestamp.

- **`Confianca`** — score (0–1) atribuído a uma extração e a uma classificação, com os fatores
  que o compõem (qualidade da extração, força da regra, ambiguidade da classificação).

### Modelo canônico de transação (esboço)
```
EventoEconomico
├── id
├── data_competencia
├── data_caixa            (quando o dinheiro se moveu, se aplicável)
├── valor
├── moeda
├── contraparte           (CNPJ/CPF, nome)
├── natureza              (receita | despesa | transferência | ...)
├── referencias_fiscais   (chave NF-e, número da nota, ...)
├── documentos[]          (ids dos Documentos que evidenciam este evento)
└── lancamentos[]         (ids dos LancamentoContabil gerados)
```
Normalizar tudo para esse modelo **antes** de classificar é o que permite tratar uma NF-e XML e
uma linha de extrato OFX pelo mesmo caminho a partir daí.

---

## 3. Pipeline de processamento

O processamento é um **pipeline assíncrono**. "Tempo real" se refere à **ingestão contínua**;
os livros chegam a **consistência eventual**, porque a conciliação correta às vezes depende de
documentos que ainda não chegaram (a NF chega antes do comprovante, ou vice-versa).

```
  ┌──────────┐   ┌──────────┐   ┌─────────────┐   ┌──────────────────┐
  │ Ingestão │──▶│ Extração │──▶│ Normalização│──▶│ Dedup/Conciliação│──┐
  └──────────┘   └──────────┘   └─────────────┘   └──────────────────┘  │
       ▲                                                                  ▼
       │         ┌──────────┐   ┌─────────────────────┐   ┌──────────────────┐
   webhook ◀─────│  Ledger  │◀──│ Geração + Validação │◀──│   Classificação  │
   (status)      │(imutável)│   │   (partida dobrada) │   │ (regras + LLM)   │
                 └──────────┘   └─────────────────────┘   └──────────────────┘
                       │                                          │
                       ▼                                          ▼
                  Export (SPED,                          baixa confiança →
                  relatórios)                            Fila de Revisão (humano)
```

Etapas:
1. **Ingestão** — recebe o documento, calcula o hash, deduplica arquivos idênticos, persiste o
   original e enfileira um job. Responde rápido (202 Accepted + id do job).
2. **Extração** — converte o documento no seu conteúdo estruturado (por tipo — ver §5).
3. **Normalização** — mapeia a extração para um ou mais `EventoEconomico` canônicos.
4. **Dedup/Conciliação** — casa o evento com eventos já conhecidos (ver §6).
5. **Classificação** — escolhe as contas do plano de contas (regras + LLM — ver §7).
6. **Geração + Validação** — monta a partida dobrada e valida (débito = crédito, contas válidas,
   período aberto).
7. **Ledger** — grava de forma **append-only**.
8. **Export / Webhook** — notifica o consumidor; baixa confiança vai para a fila de revisão.

Por que assíncrono: extração de PDF/OCR é lenta, classificação por LLM tem latência variável, e
a conciliação pode precisar esperar documentos relacionados. Síncrono ("manda e devolve na hora")
não sustenta nem o volume nem a correção.

---

## 4. Contrato da API (esboço)

Estilo REST, assíncrono, com **webhooks** para notificação e **idempotência por hash** do
documento. Versionado (`/v1`). Autenticação por API key/tenant (ver §13).

### Endpoints principais
| Método | Rota | Descrição |
|--------|------|-----------|
| `PUT`  | `/v1/empresas/{id}/plano-de-contas` | **Envia/sincroniza o plano de contas da empresa** (vindo do sistema único). Cria uma nova versão; idempotente por conteúdo. |
| `GET`  | `/v1/empresas/{id}/plano-de-contas` | Consulta o plano de contas vigente (ou uma versão específica via `?versao=`). |
| `POST` | `/v1/documentos` | Envia um documento (multipart ou base64). Retorna `job_id`. Idempotente por hash. |
| `GET`  | `/v1/jobs/{job_id}` | Status do processamento de um documento. |
| `GET`  | `/v1/eventos/{id}` | Um evento econômico normalizado + seus documentos e lançamentos. |
| `GET`  | `/v1/lancamentos` | Lista lançamentos (filtros: período, conta, status, confiança). |
| `GET`  | `/v1/revisoes` | Fila de revisão (lançamentos de baixa confiança ou em conflito). |
| `POST` | `/v1/lancamentos/{id}/aprovar` | Aprova um lançamento em rascunho. |
| `POST` | `/v1/lancamentos/{id}/corrigir` | Corrige (gera estorno + novo lançamento — ver §8). |
| `POST` | `/v1/exports/sped` | Solicita export do período (ECD/ECF) — fase posterior. |
| `POST` | `/v1/webhooks` | Registra URL para receber eventos de status. |

### Exemplo — envio do plano de contas (do sistema único)
```http
PUT /v1/empresas/emp_01HXZ.../plano-de-contas
Content-Type: application/json

{
  "origem": "sistema_unico",
  "referencia_versao": "2026-06",
  "contas": [
    { "codigo": "1.1.1.02.001", "descricao": "Banco Conta Movimento", "natureza": "ativo",   "aceita_lancamento": true,  "conta_referencial_sped": "1.01.01.02.00" },
    { "codigo": "2.1.3.00.001", "descricao": "Simples Nacional a Recolher", "natureza": "passivo", "aceita_lancamento": true,  "conta_referencial_sped": "2.01.04.00.00" },
    { "codigo": "3.1.2.00.000", "descricao": "Receita de Serviços", "natureza": "receita", "aceita_lancamento": false, "conta_referencial_sped": null },
    { "codigo": "3.1.2.01.001", "descricao": "Material de escritório", "natureza": "despesa", "aceita_lancamento": true,  "conta_referencial_sped": "3.02.01.00.00" }
  ]
}
```
```json
// 200 OK
{
  "empresa_id": "emp_01HXZ...",
  "plano_versao": 7,
  "total_contas": 142,
  "vigente_desde": "2026-06-27T14:03:00Z",
  "avisos": ["3 contas sem mapeamento referencial SPED"]
}
```
O `id` da empresa amarra todo o restante (documentos, eventos, lançamentos) a este plano. A
classificação (§7) só escolhe contas com `aceita_lancamento: true` deste plano vigente; contas
analíticas/sintéticas e o mapeamento SPED são preservados para validação e export.

### Exemplo — envio de documento
```http
POST /v1/documentos
Content-Type: application/json

{
  "tipo": "nfe_xml",
  "conteudo_base64": "PD94bWwg...",
  "origem": "integracao_erp",
  "metadados": { "filial": "matriz" }
}
```
```json
// 202 Accepted
{
  "job_id": "job_01HXZ...",
  "documento_id": "doc_01HXZ...",
  "hash": "sha256:9f2b...",
  "status": "processando",
  "duplicado": false
}
```

### Exemplo — lançamento gerado com rastreabilidade (saída)
```json
{
  "lancamento_id": "lanc_01HXZ...",
  "evento_id": "evt_01HXZ...",
  "data_competencia": "2026-06-14",
  "status": "rascunho",
  "confianca": 0.93,
  "justificativa": "NF-e de compra de material de escritório; CFOP 1.556 → despesa.",
  "partidas": [
    { "conta": "3.1.2.01.001", "descricao": "Material de escritório", "debito": 1250.00, "credito": 0.00 },
    { "conta": "1.1.1.02.001", "descricao": "Banco Conta Movimento",   "debito": 0.00,    "credito": 1250.00 }
  ],
  "rastreabilidade": [
    {
      "documento_id": "doc_01HXZ...",
      "tipo": "nfe_xml",
      "hash": "sha256:9f2b...",
      "referencia": { "chave_nfe": "3526...", "campo": "vNF" }
    }
  ],
  "revisao": null
}
```
Note que `partidas` soma zero (1250 débito / 1250 crédito) e cada lançamento aponta para o
documento, hash e o **campo exato** de onde o valor veio — essa é a rastreabilidade ponta a ponta.

---

## 5. Extração por tipo de documento

Princípio central: **estruturado primeiro**. Quanto mais estruturada a fonte, maior a acurácia e
menor o custo. E **sempre validar a extração contra um total conhecido** (ex.: somar as linhas e
conferir com o `vNF` da nota, ou com o saldo do extrato).

| Tipo | Estrutura | Estratégia | Fase |
|------|-----------|-----------|------|
| **NF-e / NFS-e (XML)** | Alta (layout 4.00 padronizado) | Parser determinístico do XML; campos fiscais diretos (CFOP, NCM, vNF, emitente/destinatário). | **1** |
| **Extrato OFX / CNAB** | Alta (formato padrão bancário) | Parser determinístico; cada transação vira um `EventoEconomico`. | **1** |
| **Extrato em PDF** | Baixa | OCR/LLM → tabela de transações; **validar somatório contra saldo inicial/final**. | 3 |
| **Comprovante em PDF** | Baixa | LLM extrai valor/data/contraparte; serve sobretudo como **evidência de pagamento** para conciliar. | 3 |
| **Planilha xlsx** | Variável | Mapeamento de schema (detecção de colunas + confirmação do usuário); validar totais. | 3 |

Começar por XML e OFX prova o pipeline inteiro (normalização, classificação, partida dobrada,
ledger, rastreabilidade) com **sinal limpo**, sem o ruído da extração não estruturada. PDF/xlsx
entram depois, reaproveitando todo o resto do pipeline.

---

## 6. Conciliação e deduplicação

**Este é o problema mais difícil — mais que a classificação.** Um único evento econômico aparece
em **múltiplos documentos, em papéis diferentes**:

> A **NF-e** (a obrigação/competência) + o **comprovante de pagamento** (a quitação) + a **linha
> do extrato** (o movimento de caixa) são, frequentemente, **o mesmo evento econômico**.

Se cada documento gerar seu próprio lançamento sem conciliação, a contabilidade **triplica** o
valor. A conciliação é o que evita isso e o que liga competência (regime de competência) a caixa.

### Estratégia de matching
- **Chave forte:** referência fiscal (chave da NF-e) presente no comprovante ou na descrição do
  extrato → casamento de alta confiança.
- **Chave composta (fuzzy):** `valor` + `data` (com janela de tolerância) + `contraparte`
  (CNPJ/CPF) → casamento provável.
- **Idempotência:** hash do documento evita reprocessar o mesmo arquivo; a chave do evento
  (referência fiscal normalizada) evita duplicar o mesmo fato vindo de fontes diferentes.

### Tratamento de casos
- **Match forte** → vincula o documento ao evento existente como nova evidência (sem novo
  lançamento; possivelmente atualiza competência → caixa).
- **Match parcial/ambíguo** → cria o evento mas marca **baixa confiança** → fila de revisão.
- **Sem match** → novo `EventoEconomico`.

---

## 7. Motor contábil

A geração da **partida dobrada é determinística e é a parte fácil** — é onde a engenharia
contábil clássica entra. A inteligência fica na **classificação** (qual conta usar).

### Classificação: regras + LLM (sempre dentro do plano da empresa)
A classificação **nunca inventa conta**: ela escolhe entre as `Conta`s com `aceita_lancamento:
true` do **plano de contas vigente da empresa** (sincronizado do sistema único — §2 e §4). O
plano é o espaço de busca fechado da classificação.

- **Camada de regras (primeiro):** mapeamentos determinísticos de alta confiança — ex.: CFOP →
  natureza da operação; histórico do fornecedor → conta usada da última vez **naquele plano**.
  Barata, explicável, auditável.
- **Camada LLM (quando a regra não decide):** para casos ambíguos, o LLM recebe **as contas do
  plano da empresa como opções** e sugere a mais adequada a partir do contexto (descrição,
  contraparte, histórico), **sempre retornando uma justificativa** e alimentando a `confianca`.
  Casos de baixa confiança vão para revisão humana.

### Plano de contas e regime
- **Plano de contas da própria empresa**, enviado/sincronizado pelo consumidor a partir do
  **sistema único** (§4). O mapeamento opcional `conta_referencial_sped` por conta permite
  padronização e export sem impor um plano fixo.
- Sensível ao **regime tributário**; **regime inicial definido: Simples Nacional**, com
  escrituração completa (partida dobrada). Detalhes em [`SIMPLES_NACIONAL.md`](SIMPLES_NACIONAL.md).
- **Contas faltantes:** se um evento não tem conta adequada no plano vigente, o lançamento vai
  para revisão sinalizando a lacuna (em vez de criar conta automaticamente).

### Validações (determinísticas, sempre)
- Soma dos débitos = soma dos créditos.
- Contas existem **no plano vigente da empresa**, aceitam lançamento e são válidas para a operação.
- Período de competência está aberto.
- Valores conferem com os totais do documento de origem.

---

## 8. Rastreabilidade e ledger

A rastreabilidade é **o diferencial** do produto e a razão para confiar numa máquina.

- **Ledger append-only / event-sourced.** Lançamentos nunca são apagados ou editados no lugar.
- **Vínculo completo:** cada `LancamentoContabil` → `EventoEconomico` → `Documento`(s) → `hash`
  do arquivo original → **campo/linha/página** de onde o dado veio.
- **Correções como estornos.** Corrigir um lançamento = gerar um **estorno** + um **novo
  lançamento**, ambos registrados. A trilha de auditoria preserva o que foi feito, por quem e
  quando (`Revisao`).
- **Imutabilidade dos originais.** O documento recebido é guardado intacto; o hash prova que não
  mudou.

Resultado: para qualquer número nos livros, é possível clicar e chegar ao documento exato (e ao
campo exato) que o originou, e ver se foi gerado por regra, por LLM ou por um humano.

---

## 9. Confiança e revisão humana

O fluxo de "copiloto" depende de **calibrar confiança** e rotear o que precisa de gente.

- **Confidence score por lançamento**, combinando qualidade da extração + força da classificação
  + ambiguidade da conciliação.
- **Fila de revisão** (`/v1/revisoes`): tudo abaixo de um limiar, ou em conflito de conciliação,
  espera aprovação humana antes de virar lançamento definitivo.
- **Fluxo de aprovação:** aprovar, corrigir (gera estorno+novo) ou rejeitar.
- **Aprendizado com correções:** correções do contador viram **novas regras** (ex.: "fornecedor X
  sempre na conta Y") e exemplos para melhorar a classificação — o sistema fica mais autônomo com
  o tempo, sem nunca perder a rastreabilidade.

---

## 10. Stack tecnológica sugerida

| Camada | Escolha sugerida | Por quê |
|--------|------------------|---------|
| API | **Python + FastAPI** | Tipagem, performance assíncrona, ecossistema fiscal/contábil em Python. |
| Modelos de dados | **Pydantic** | Validação dos modelos canônicos (EventoEconomico, Lancamento). |
| Fila/jobs | **Celery/RQ** ou fila gerenciada (cloud) | Processamento assíncrono e retry da extração/classificação. |
| Storage de documentos | **Object storage** (S3/GCS) | Guardar originais imutáveis + hash. |
| Ledger | **PostgreSQL** (append-only) | Transacional, auditável, consultas relacionais ricas. |
| Extração estruturada | Parsers dedicados (XML NF-e, OFX/CNAB) | Determinístico, alta acurácia. |
| Classificação / extração não estruturada | **Claude API** | LLM para casos ambíguos (classificação) e, em fase posterior, extração de PDF/comprovantes. |

Sobre os modelos Claude (família atual): usar um modelo **mais capaz** (ex.: Opus) para
classificação ambígua e raciocínio contábil, e um modelo **rápido/barato** (ex.: Haiku) para
extração estruturada de alto volume — equilibrando custo e acurácia. (Definir os IDs exatos na
fase de implementação, conferindo a documentação vigente da API.)

---

## 11. Riscos e conformidade

- **Regulatório.** A escrituração legal tem responsável técnico (contador/CRC) e fecha em SPED
  ECD/ECF. O posicionamento de **copiloto** mitiga isso: a máquina gera rascunhos; o humano
  responde legalmente. Export SPED é fase posterior e sempre sobre dados aprovados.
- **LGPD.** Dados financeiros são sensíveis: criptografia em trânsito e em repouso, segregação por
  tenant, política de retenção, trilha de acesso.
- **Acurácia / auditabilidade.** Toda saída precisa de confiança + justificativa + rastreabilidade.
  Validar extração contra totais é inegociável.
- **"Tempo real" vs. consistência eventual.** Comunicar claramente que os livros convergem à
  medida que os documentos chegam; conciliação correta pode exigir esperar evidências relacionadas.
- **Segurança.** Superfície de upload (arquivos não confiáveis), isolamento do processamento,
  autenticação forte por tenant.

---

## 12. Roadmap faseado

- **Fase 1 — Núcleo com sinal limpo.** Ingestão de **NF-e/NFS-e XML + OFX** → normalização →
  classificação (regras + LLM) → partida dobrada → **ledger imutável + rastreabilidade**.
  Entrega o pipeline inteiro de ponta a ponta para fontes estruturadas.
- **Fase 2 — Conciliação multi-documento.** Dedup e casamento de NF ↔ comprovante ↔ extrato;
  competência ↔ caixa; fila de revisão para conflitos.
- **Fase 3 — Documentos não estruturados.** PDF (extratos e comprovantes via OCR/LLM) e xlsx,
  reaproveitando o pipeline; validação contra totais.
- **Fase 4 — Saída fiscal e aprendizado.** Export SPED (ECD/ECF), fluxo de revisão/aprovação
  maduro, regras aprendidas a partir das correções do contador.

---

## 13. Decisões em aberto

- ~~**Regime tributário inicial.**~~ **DEFINIDO: Simples Nacional** (escrituração completa,
  partida dobrada). Especificidades em [`SIMPLES_NACIONAL.md`](SIMPLES_NACIONAL.md). O plano de
  contas continua projetado para ser **regime-aware**, permitindo expandir para Presumido/Real.
- **Multi-tenant.** Modelo de isolamento de dados entre clientes (schema por tenant vs. linha por
  tenant).
- **Autenticação / autorização.** API keys, escopos, papéis (integração vs. contador revisor).
- **Retenção de documentos.** Prazo de guarda dos originais (alinhado à legislação fiscal).
- **Granularidade do "tempo real".** Webhooks vs. polling; SLA de processamento por tipo.

---

*Próximo passo sugerido (fora deste documento): prototipar o MVP da Fase 1 — FastAPI + parser de
NF-e XML + geração de partida dobrada + ledger com rastreabilidade — para validar a tese com
dados reais.*
