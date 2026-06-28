"""Base de conhecimento: os lançamentos anteriores da empresa.

Duas funções para a classificação (espelham o §7 do CONCEITO.md):
1. memória determinística por contraparte (CNPJ → conta mais usada);
2. recuperação de lançamentos semelhantes para servir de exemplo (few-shot) ao LLM.
"""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LancamentoHistorico:
    data: str
    tipo_operacao: str
    contraparte_cnpj: str
    contraparte_nome: str
    cfop: str
    descricao: str
    conta: str


@dataclass(frozen=True)
class PalpiteMemoria:
    conta: str
    ocorrencias: int
    total: int

    @property
    def proporcao(self) -> float:
        return self.ocorrencias / self.total if self.total else 0.0


class BaseConhecimento:
    def __init__(self, historico: list[LancamentoHistorico]):
        self.historico = historico
        self._por_contraparte: dict[str, Counter[str]] = defaultdict(Counter)
        for h in historico:
            if h.contraparte_cnpj:
                self._por_contraparte[h.contraparte_cnpj][h.conta] += 1

    @classmethod
    def carregar(cls, caminho: str | Path) -> BaseConhecimento:
        registros: list[LancamentoHistorico] = []
        with Path(caminho).open(encoding="utf-8") as fh:
            for linha in csv.DictReader(fh):
                registros.append(
                    LancamentoHistorico(
                        data=linha.get("data", "").strip(),
                        tipo_operacao=linha.get("tipo_operacao", "").strip().lower(),
                        contraparte_cnpj=linha.get("contraparte_cnpj", "").strip(),
                        contraparte_nome=linha.get("contraparte_nome", "").strip(),
                        cfop=linha.get("cfop", "").strip(),
                        descricao=linha.get("descricao", "").strip(),
                        conta=linha.get("conta", "").strip(),
                    )
                )
        return cls(registros)

    def palpite_por_contraparte(self, cnpj: str) -> PalpiteMemoria | None:
        """Conta mais usada historicamente para uma contraparte."""
        contador = self._por_contraparte.get(cnpj)
        if not contador:
            return None
        conta, ocorrencias = contador.most_common(1)[0]
        return PalpiteMemoria(conta, ocorrencias, sum(contador.values()))

    def semelhantes(
        self, cfop: str, tipo_operacao: str, limite: int = 5
    ) -> list[LancamentoHistorico]:
        """Lançamentos parecidos (mesmo CFOP/tipo) para usar como exemplos no LLM."""
        mesmos_cfop = [
            h for h in self.historico if h.cfop == cfop and h.tipo_operacao == tipo_operacao
        ]
        if mesmos_cfop:
            return mesmos_cfop[:limite]
        return [h for h in self.historico if h.tipo_operacao == tipo_operacao][:limite]
