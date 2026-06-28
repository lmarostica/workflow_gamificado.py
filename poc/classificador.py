"""Classificação contábil: escolhe a conta (receita/despesa/estoque) de um evento.

Camadas, na ordem do CONCEITO.md §7:
1. memória determinística (contraparte → conta histórica mais usada);
2. LLM (Claude) com as contas do plano como opções + exemplos do histórico (few-shot);
3. heurística de fallback (quando não há memória nem LLM disponível).

A classificação nunca inventa conta: só escolhe entre as contas do plano vigente.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

from .base_conhecimento import BaseConhecimento
from .modelos import Conta, EventoEconomico
from .plano_contas import PlanoDeContas

LIMIAR_REVISAO = 0.75
MODELO_PADRAO = os.environ.get("ESCRITURADOR_MODELO", "claude-sonnet-4-6")

# Naturezas candidatas à conta classificada, por tipo de operação.
_NATUREZAS = {
    "entrada": {"despesa", "ativo", "custo"},
    "saida": {"receita"},
}


@dataclass
class ResultadoClassificacao:
    conta: str
    confianca: float
    justificativa: str
    origem: str  # memoria | llm | heuristica


def classificar(
    evento: EventoEconomico,
    plano: PlanoDeContas,
    base: BaseConhecimento,
) -> ResultadoClassificacao:
    candidatas = plano.classificaveis(_NATUREZAS.get(evento.tipo_operacao, set()))

    memoria = _por_memoria(evento, plano, base)
    if memoria is not None:
        return memoria

    via_llm = _por_llm(evento, candidatas, base)
    if via_llm is not None:
        return via_llm

    return _heuristica(candidatas)


def _por_memoria(
    evento: EventoEconomico, plano: PlanoDeContas, base: BaseConhecimento
) -> ResultadoClassificacao | None:
    if not evento.contraparte_cnpj:
        return None
    palpite = base.palpite_por_contraparte(evento.contraparte_cnpj)
    if palpite is None or not plano.existe(palpite.conta):
        return None
    return ResultadoClassificacao(
        conta=palpite.conta,
        confianca=round(min(palpite.proporcao, 0.99), 2),
        justificativa=(
            f"Contraparte {evento.contraparte_nome or evento.contraparte_cnpj} "
            f"classificada em {palpite.conta} em {palpite.ocorrencias} de "
            f"{palpite.total} lançamentos anteriores."
        ),
        origem="memoria",
    )


def _por_llm(
    evento: EventoEconomico,
    candidatas: list[Conta],
    base: BaseConhecimento,
) -> ResultadoClassificacao | None:
    if not os.environ.get("ANTHROPIC_API_KEY") or not candidatas:
        return None
    try:
        import anthropic
    except ImportError:
        return None

    exemplos = base.semelhantes(evento.cfop_principal, evento.tipo_operacao)
    opcoes = "\n".join(f"- {c.codigo}: {c.descricao}" for c in candidatas)
    historico = (
        "\n".join(f"- {h.descricao} (CFOP {h.cfop}) -> {h.conta}" for h in exemplos)
        or "(sem exemplos)"
    )

    prompt = (
        "Você é um contador classificando uma NF-e no plano de contas da empresa "
        "(regime Simples Nacional, escrituração completa). Escolha UMA conta da lista.\n\n"
        f"Operação: {evento.tipo_operacao}\n"
        f"Natureza: {evento.natureza_operacao}\n"
        f"CFOP: {evento.cfop_principal}\n"
        f"Contraparte: {evento.contraparte_nome}\n"
        f"Itens: {evento.descricao_resumo}\n"
        f"Valor: {evento.valor_total}\n\n"
        f"Contas possíveis:\n{opcoes}\n\n"
        f"Exemplos de lançamentos anteriores semelhantes:\n{historico}\n\n"
        'Responda APENAS um JSON: {"conta": "<codigo>", "confianca": <0..1>, '
        '"justificativa": "<curta>"}'
    )

    try:
        cliente = anthropic.Anthropic()
        resp = cliente.messages.create(
            model=MODELO_PADRAO,
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        texto = "".join(b.text for b in resp.content if b.type == "text")
        dados = json.loads(_extrair_json(texto))
    except Exception:  # noqa: BLE001 — PoC: qualquer falha cai no fallback
        return None

    conta = str(dados.get("conta", "")).strip()
    if not any(c.codigo == conta for c in candidatas):
        return None
    return ResultadoClassificacao(
        conta=conta,
        confianca=round(float(dados.get("confianca", 0.5)), 2),
        justificativa=str(dados.get("justificativa", "Classificado por LLM.")),
        origem="llm",
    )


def _heuristica(candidatas: list[Conta]) -> ResultadoClassificacao:
    if not candidatas:
        return ResultadoClassificacao(
            conta="",
            confianca=0.0,
            justificativa="Sem conta candidata no plano para a operação.",
            origem="heuristica",
        )
    escolha = candidatas[0]
    return ResultadoClassificacao(
        conta=escolha.codigo,
        confianca=0.3,
        justificativa=(
            "Sem memória nem LLM; escolha heurística pela primeira conta candidata "
            f"({escolha.descricao}). Requer revisão."
        ),
        origem="heuristica",
    )


def _extrair_json(texto: str) -> str:
    inicio = texto.find("{")
    fim = texto.rfind("}")
    return texto[inicio : fim + 1] if inicio != -1 and fim != -1 else texto
