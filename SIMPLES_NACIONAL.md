# Contabilidade no Simples Nacional — Especificidades para a API

> Aprofundamento do regime tributário inicial escolhido: **Simples Nacional**, mirando
> **escrituração contábil completa (partida dobrada)**. Complementa o `CONCEITO.md`.
> Versão 0.1 — proposta para discussão.
>
> ⚠️ **Aviso:** alíquotas, limites e obrigações mudam por lei (LC 123/2006 e Resoluções CGSN).
> Os valores aqui são referência para o desenho do sistema e **devem ser confirmados contra a
> legislação vigente e validados por um contador** antes de virar regra de produção.

---

## 1. Visão geral do Simples Nacional

Regime tributário simplificado e unificado para **ME** (microempresa) e **EPP** (empresa de
pequeno porte):

- **ME:** receita bruta anual até **R$ 360.000,00**.
- **EPP:** acima de R$ 360.000,00 até **R$ 4.800.000,00**.
- **MEI** (até R$ 81.000/ano) tem tratamento próprio e **está fora do escopo** desta API (sequer
  exige escrituração contábil completa).

O grande traço do regime: **vários tributos num único pagamento**, o **DAS** (Documento de
Arrecadação do Simples Nacional). O DAS pode englobar: **IRPJ, CSLL, PIS/Pasep, COFINS, IPI,
ICMS, ISS e CPP** (contribuição patronal previdenciária) — quais entram depende do **anexo** da
atividade.

---

## 2. Anexos e Fator R (classificação da atividade)

A atividade da empresa determina o **anexo**, que determina as alíquotas e quais tributos entram
no DAS:

| Anexo | Atividade | Observação contábil relevante |
|-------|-----------|-------------------------------|
| **I** | Comércio | — |
| **II** | Indústria | Inclui IPI |
| **III** | Serviços (instalação, reparos, agências etc.) e serviços do V com **Fator R ≥ 28%** | CPP dentro do DAS |
| **IV** | Serviços (construção, advocacia, vigilância, limpeza) | **CPP (INSS patronal) recolhida FORA do DAS** → contabilização separada |
| **V** | Serviços intelectuais (TI, engenharia etc.) com **Fator R < 28%** | CPP dentro do DAS; alíquotas maiores |

**Fator R** = folha de salários (12 meses) ÷ receita bruta (12 meses). Se **≥ 28%**, certos
serviços migram do Anexo V para o III (alíquotas menores). Isso impacta a **classificação** de
receitas de serviço na API e exige conhecer a folha — ver §6.

---

## 3. Cálculo do DAS (alíquota efetiva)

O DAS não usa alíquota fixa: é **progressivo por faixa** da receita bruta acumulada dos últimos
12 meses (**RBT12**), com **alíquota nominal** e **parcela a deduzir** por faixa.

```
alíquota_efetiva = (RBT12 × alíquota_nominal − parcela_a_deduzir) / RBT12
DAS_do_mês       = receita_bruta_do_mês × alíquota_efetiva
```

Implicações para a API:
- O DAS é uma **apuração mensal derivada** da receita do mês + histórico (RBT12). **Não nasce de
  um documento isolado** — é calculado no fechamento do período (ver §9).
- A segregação do DAS por tributo componente (quanto foi ICMS, ISS, IRPJ...) vem da declaração
  **PGDAS-D** e pode ser usada para uma contabilização mais granular (ver §6).

---

## 4. Obrigações acessórias e SPED

- **PGDAS-D** — apuração/declaração mensal que gera o DAS.
- **DEFIS** — declaração socioeconômica e fiscal, **anual**.
- **ECD / ECF (SPED contábil/fiscal):** ME/EPP do Simples são **em regra dispensadas**, salvo
  exceções (ex.: distribuição de lucros acima do limite presumido, recebimento de aporte via
  investidor-anjo, entre outras). 

Consequência de produto: para o Simples, o **export SPED do `CONCEITO.md` deixa de ser
prioritário** — o foco é a escrituração completa para fins societários e gerenciais, além de
**PGDAS-D/DEFIS** como possíveis saídas futuras.

---

## 5. Por que escrituração completa (e não só Livro Caixa)

Para fins fiscais o Simples admite escrituração simplificada (Livro Caixa). Mas a **escrituração
contábil completa (partida dobrada)** é a escolha aqui por um motivo concreto e valioso:

> **Distribuição de lucros isenta de IR.** Sem contabilidade, a distribuição isenta aos sócios é
> limitada ao **lucro presumido** (percentual de presunção da atividade menos o IRPJ do Simples).
> **Com escrituração contábil completa** que comprove lucro maior, a distribuição isenta pode ser
> **maior** (até o lucro contábil apurado). Isso paga a contabilidade sozinho.

Além disso: base auditável, rastreabilidade real, gestão e crédito bancário. Ou seja, a tese
"copiloto auditável" do `CONCEITO.md` se encaixa perfeitamente no Simples com escrituração
completa.

---

## 6. Especificidades contábeis que impactam a API

1. **Receita por competência.** A contabilidade reconhece receita por **competência**, ainda que
   o contribuinte possa optar por **caixa ou competência** no cálculo do DAS (PGDAS-D). A API deve
   registrar a receita por competência e tratar o regime de caixa, se houver, apenas na apuração.

2. **DAS unificado — como contabilizar.** Parte do DAS são **tributos sobre a receita** (ICMS,
   ISS, PIS, COFINS, IPI → redutores da receita bruta) e parte são **tributos sobre lucro/folha**
   (IRPJ, CSLL, CPP → despesas). Duas abordagens:
   - **Simplificada:** registrar o DAS agregado (ex.: "Impostos sobre Vendas — Simples Nacional").
   - **Granular (recomendada):** usar o detalhamento do **PGDAS-D** para segregar entre redutores
     de receita e despesas tributárias. A API pode ingerir o PGDAS-D para fazer essa segregação.

3. **Compras sem crédito de impostos.** O optante do Simples, em regra, **não se credita** de
   ICMS/PIS/COFINS. Compras entram pelo **valor cheio** (sem "impostos a recuperar"), salvo
   exceções (ICMS-ST, DIFAL etc.). Isso simplifica a classificação de NF-e de entrada.

4. **CPP no Anexo IV.** No Anexo IV a **CPP (INSS patronal) é recolhida fora do DAS** → exige
   conta e lançamento próprios de "INSS a Recolher". Nos demais anexos a CPP está dentro do DAS.

5. **Sublimite de ICMS/ISS.** Acima de **R$ 3.600.000,00** de receita, **ICMS e ISS passam a ser
   recolhidos fora do Simples** (regime normal para esses tributos). Caso de borda a sinalizar.

6. **Fator R.** Para serviços dos Anexos III/V, classificar a receita corretamente exige conhecer
   a folha (Fator R). A API precisa de acesso a essa informação ou de marcá-la como **decisão de
   baixa confiança → fila de revisão**.

---

## 7. Plano de contas — recorte para o Simples

> **O plano de contas é o da própria empresa**, sincronizado a partir do sistema único (ver
> `CONCEITO.md` §2 e §4). O recorte abaixo é **ilustrativo**: serve como referência das
> contas-chave que o regime costuma exigir e para conferir se o plano da empresa as cobre (e, se
> não cobrir, sinalizar a lacuna na revisão). A classificação só usa contas existentes no plano
> vigente.

```
1 ATIVO
  1.1.1 Caixa e Bancos
  1.1.2 Clientes
  1.1.3 Estoques
2 PASSIVO
  2.1.1 Fornecedores
  2.1.2 Salários a Pagar
  2.1.3 Simples Nacional a Recolher        ← tributo unificado (DAS)
  2.1.4 INSS a Recolher                     ← CPP fora do DAS (Anexo IV)
3 RECEITAS
  3.1.1 Receita de Vendas
  3.1.2 Receita de Serviços
  3.2.1 (-) Impostos sobre Vendas — Simples ← parcela redutora da receita
4 CUSTOS E DESPESAS
  4.1.1 Custo das Mercadorias/Serviços
  4.2.1 Despesas com Pessoal (Salários, INSS)
  4.3.1 Despesas Tributárias — Simples      ← parcela "lucro/folha" do DAS
```

---

## 8. Catálogo de eventos econômicos → lançamentos (partida dobrada)

Mapeamento dos eventos típicos do Simples para os lançamentos que a API geraria. Cada lançamento
soma zero (débito = crédito) e aponta para o(s) documento(s) de origem.

| Evento (documento) | Débito | Crédito |
|--------------------|--------|---------|
| **Venda/serviço** (NF-e / NFS-e) | Clientes *(ou Banco)* | Receita de Vendas/Serviços |
| **Compra de mercadoria** (NF-e entrada) | Estoques *(valor cheio, sem crédito)* | Fornecedores |
| **Pagamento a fornecedor** (comprovante/extrato) | Fornecedores | Banco |
| **Recebimento de cliente** (extrato) | Banco | Clientes |
| **Apuração mensal do DAS** (PGDAS-D / derivado) | (-) Impostos sobre Vendas + Despesas Tributárias | Simples Nacional a Recolher |
| **Pagamento do DAS** (guia/extrato) | Simples Nacional a Recolher | Banco |
| **Folha — salários** (folha) | Despesas com Pessoal | Salários a Pagar |
| **INSS patronal Anexo IV** (folha/guia) | Despesas com Pessoal (INSS) | INSS a Recolher |

---

## 9. Impacto no pipeline e no modelo da API

Em relação ao pipeline do `CONCEITO.md`, o Simples acrescenta dois pontos importantes:

1. **Lançamentos de apuração periódica.** Nem todo lançamento nasce de um documento que chegou.
   A **apuração do DAS** é **derivada** da receita do mês + RBT12, gerada no **fechamento do
   período** (`Periodo`). O modelo de domínio precisa de um tipo de `EventoEconomico` "de
   apuração", calculado pelo motor, não extraído de arquivo.

2. **DAS / PGDAS-D como documentos de conciliação e segregação.** A guia do DAS (e o PGDAS-D)
   podem ser **ingeridos** para (a) conciliar o valor apurado com o efetivamente recolhido e
   (b) **segregar** o DAS por tributo na contabilização granular (§6.2).

3. **Classificação sensível ao anexo e ao Fator R.** A regra de classificação de receitas de
   serviço depende do anexo e do Fator R → casos sem folha disponível viram **baixa confiança →
   revisão humana**, coerente com o posicionamento de copiloto.

Isso **não muda** a arquitetura central (pipeline assíncrono, ledger imutável, rastreabilidade);
apenas adiciona o conceito de **eventos derivados de apuração** e regras de classificação
específicas do Simples.

---

## 10. Riscos e limitações específicos

- **Mudança legislativa frequente.** Alíquotas, faixas, sublimites e dispensa de SPED mudam —
  manter como **tabela/configuração versionada**, nunca hard-coded.
- **Fator R e folha.** Sem dados de folha confiáveis, a classificação de serviços III/V fica
  incerta → revisão.
- **Granularidade do DAS.** A segregação por tributo depende do PGDAS-D; sem ele, registrar
  agregado e sinalizar.
- **Necessidade de validação profissional.** Toda regra contábil/fiscal deve ser homologada por
  contador antes de produção; a API gera **rascunhos auditáveis**, não verdade fiscal final.

---

*Próximo passo sugerido: usar este recorte para definir o plano de contas inicial e as regras de
classificação determinísticas do MVP da Fase 1 (NF-e/NFS-e XML + OFX) já no contexto Simples
Nacional.*
