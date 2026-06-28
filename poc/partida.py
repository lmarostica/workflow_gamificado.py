"""Montagem da partida dobrada a partir do evento + classificação.

Regra determinística (a parte "fácil"):
- entrada (compra): D conta classificada (despesa/estoque)  /  C Fornecedores
- saída (venda):    D Clientes                              /  C conta classificada (receita)

A contrapartida financeira/operacional é resolvida no plano da empresa por palavra-chave.
"""

from __future__ import annotations

from .classificador import LIMIAR_REVISAO, ResultadoClassificacao
from .modelos import EventoEconomico, LancamentoSugerido, Partida
from .plano_contas import PlanoDeContas


class ErroPartida(Exception):
    pass


def _resolver(plano: PlanoDeContas, natureza: str, *palavras: str) -> str:
    """Acha no plano uma conta da natureza dada cujo nome contenha a palavra-chave."""
    for conta in plano.contas:
        if not conta.aceita_lancamento or conta.natureza != natureza:
            continue
        desc = conta.descricao.lower()
        if any(p in desc for p in palavras):
            return conta.codigo
    raise ErroPartida(f"Plano sem conta {natureza} para contrapartida ({', '.join(palavras)}).")


def montar(
    evento: EventoEconomico,
    resultado: ResultadoClassificacao,
    plano: PlanoDeContas,
) -> LancamentoSugerido:
    valor = evento.valor_total
    conta = resultado.conta

    if evento.tipo_operacao == "entrada":
        contrapartida = _resolver(plano, "passivo", "fornecedor")
        partidas = [
            Partida(conta, _desc(plano, conta), valor, 0.0),
            Partida(contrapartida, _desc(plano, contrapartida), 0.0, valor),
        ]
    else:  # saida
        contrapartida = _resolver(plano, "ativo", "cliente")
        partidas = [
            Partida(contrapartida, _desc(plano, contrapartida), valor, 0.0),
            Partida(conta, _desc(plano, conta), 0.0, valor),
        ]

    status = (
        "rascunho"
        if plano.existe(conta) and resultado.confianca >= LIMIAR_REVISAO
        else "aguardando_revisao"
    )

    lanc = LancamentoSugerido(
        evento=evento,
        partidas=partidas,
        conta_classificada=conta,
        confianca=resultado.confianca,
        justificativa=resultado.justificativa,
        origem_classificacao=resultado.origem,
        status=status,
    )
    if not lanc.balanceado():
        raise ErroPartida(
            f"Partida não balanceada: D {lanc.soma_debitos()} x C {lanc.soma_creditos()}"
        )
    return lanc


def _desc(plano: PlanoDeContas, codigo: str) -> str:
    conta = plano.obter(codigo)
    return conta.descricao if conta else codigo
