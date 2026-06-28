"""Carrega o plano de contas da empresa (CSV) — o espaço fechado da classificação."""

from __future__ import annotations

import csv
from pathlib import Path

from .modelos import Conta

_VERDADEIRO = {"sim", "true", "1", "s", "verdadeiro"}


class PlanoDeContas:
    def __init__(self, contas: list[Conta]):
        self.contas = contas
        self._por_codigo = {c.codigo: c for c in contas}

    @classmethod
    def carregar(cls, caminho: str | Path) -> PlanoDeContas:
        contas: list[Conta] = []
        with Path(caminho).open(encoding="utf-8") as fh:
            for linha in csv.DictReader(fh):
                contas.append(
                    Conta(
                        codigo=linha["codigo"].strip(),
                        descricao=linha["descricao"].strip(),
                        natureza=linha["natureza"].strip().lower(),
                        aceita_lancamento=linha["aceita_lancamento"].strip().lower() in _VERDADEIRO,
                        alvo_classificacao=(linha.get("alvo_classificacao") or "").strip().lower()
                        in _VERDADEIRO,
                        conta_referencial_sped=(linha.get("conta_referencial_sped") or "").strip()
                        or None,
                    )
                )
        return cls(contas)

    def existe(self, codigo: str) -> bool:
        c = self._por_codigo.get(codigo)
        return c is not None and c.aceita_lancamento

    def obter(self, codigo: str) -> Conta | None:
        return self._por_codigo.get(codigo)

    def classificaveis(self, naturezas: set[str]) -> list[Conta]:
        """Contas que são alvo de classificação e cuja natureza casa com a operação."""
        return [
            c
            for c in self.contas
            if c.aceita_lancamento and c.alvo_classificacao and c.natureza in naturezas
        ]
