"""Modelos de domínio da PoC do escriturador contábil.

Mantidos deliberadamente simples (dataclasses) — a PoC não usa banco nem ORM.
Espelham, em escala reduzida, as entidades descritas no ``CONCEITO.md``.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Conta:
    """Uma conta do plano de contas da empresa."""

    codigo: str
    descricao: str
    natureza: str  # ativo | passivo | receita | despesa | resultado
    aceita_lancamento: bool
    # True para contas que são alvo de classificação (despesas, receitas, estoque);
    # False para contrapartidas fixas (Banco, Clientes, Fornecedores, impostos).
    alvo_classificacao: bool = False
    conta_referencial_sped: str | None = None


@dataclass(frozen=True)
class ItemNota:
    descricao: str
    ncm: str
    cfop: str
    valor: float


@dataclass
class EventoEconomico:
    """Transação normalizada extraída de um documento (aqui, uma NF-e)."""

    chave_nfe: str
    tipo_operacao: str  # entrada | saida
    natureza_operacao: str
    data_competencia: str
    contraparte_cnpj: str
    contraparte_nome: str
    valor_total: float
    itens: list[ItemNota] = field(default_factory=list)
    # rastreabilidade da origem
    arquivo: str = ""
    hash_arquivo: str = ""

    @property
    def cfop_principal(self) -> str:
        """CFOP do item de maior valor — bom proxy da natureza da operação."""
        if not self.itens:
            return ""
        return max(self.itens, key=lambda i: i.valor).cfop

    @property
    def descricao_resumo(self) -> str:
        return "; ".join(i.descricao for i in self.itens) or self.natureza_operacao


@dataclass(frozen=True)
class Partida:
    conta: str
    descricao: str
    debito: float
    credito: float


@dataclass
class LancamentoSugerido:
    """Resultado da PoC: a partida dobrada proposta para um evento."""

    evento: EventoEconomico
    partidas: list[Partida]
    conta_classificada: str  # a conta de receita/despesa/estoque escolhida
    confianca: float
    justificativa: str
    origem_classificacao: str  # memoria | llm | heuristica
    status: str  # rascunho | aguardando_revisao

    def soma_debitos(self) -> float:
        return round(sum(p.debito for p in self.partidas), 2)

    def soma_creditos(self) -> float:
        return round(sum(p.credito for p in self.partidas), 2)

    def balanceado(self) -> bool:
        return self.soma_debitos() == self.soma_creditos()
