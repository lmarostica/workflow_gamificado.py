"""CLI da PoC do escriturador.

Comandos:
  processar <pasta>  → gera lançamentos sugeridos (CSV + JSON)
  backtest  <pasta>  → mede acurácia: conta sugerida × conta real (gabarito.csv)

Convenção de arquivos dentro da <pasta>:
  plano_de_contas.csv, lancamentos_historicos.csv, *.xml e (no backtest) gabarito.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

from .base_conhecimento import BaseConhecimento
from .classificador import classificar
from .modelos import LancamentoSugerido
from .nfe import ErroExtracao, carregar_pasta
from .partida import ErroPartida, montar
from .plano_contas import PlanoDeContas


def _carregar_contexto(pasta: Path) -> tuple[PlanoDeContas, BaseConhecimento]:
    plano = PlanoDeContas.carregar(pasta / "plano_de_contas.csv")
    base = BaseConhecimento.carregar(pasta / "lancamentos_historicos.csv")
    return plano, base


def _gerar(pasta: Path) -> list[LancamentoSugerido]:
    plano, base = _carregar_contexto(pasta)
    lancamentos: list[LancamentoSugerido] = []
    for evento in carregar_pasta(pasta):
        resultado = classificar(evento, plano, base)
        try:
            lancamentos.append(montar(evento, resultado, plano))
        except ErroPartida as e:
            print(f"  ! {evento.arquivo}: {e}", file=sys.stderr)
    return lancamentos


def _para_dict(lanc: LancamentoSugerido) -> dict:
    e = lanc.evento
    return {
        "chave_nfe": e.chave_nfe,
        "data_competencia": e.data_competencia,
        "status": lanc.status,
        "confianca": lanc.confianca,
        "origem_classificacao": lanc.origem_classificacao,
        "conta_classificada": lanc.conta_classificada,
        "justificativa": lanc.justificativa,
        "partidas": [
            {"conta": p.conta, "descricao": p.descricao, "debito": p.debito, "credito": p.credito}
            for p in lanc.partidas
        ],
        "rastreabilidade": {
            "arquivo": e.arquivo,
            "hash": e.hash_arquivo,
            "chave_nfe": e.chave_nfe,
            "campo": "total/ICMSTot/vNF",
        },
    }


def cmd_processar(pasta: Path) -> int:
    lancamentos = _gerar(pasta)
    if not lancamentos:
        print("Nenhum lançamento gerado.", file=sys.stderr)
        return 1

    json_path = pasta / "saida_lancamentos.json"
    json_path.write_text(
        json.dumps([_para_dict(x) for x in lancamentos], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    csv_path = pasta / "saida_lancamentos.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(
            [
                "chave_nfe",
                "data",
                "status",
                "confianca",
                "origem",
                "conta",
                "valor",
                "justificativa",
            ]
        )
        for x in lancamentos:
            w.writerow(
                [
                    x.evento.chave_nfe,
                    x.evento.data_competencia,
                    x.status,
                    x.confianca,
                    x.origem_classificacao,
                    x.conta_classificada,
                    x.evento.valor_total,
                    x.justificativa,
                ]
            )

    print(f"{len(lancamentos)} lançamento(s) gerado(s).")
    print(f"  → {csv_path}")
    print(f"  → {json_path}")
    em_revisao = sum(1 for x in lancamentos if x.status == "aguardando_revisao")
    print(f"  {em_revisao} em revisão, {len(lancamentos) - em_revisao} em rascunho.")
    return 0


def cmd_backtest(pasta: Path) -> int:
    gabarito_path = pasta / "gabarito.csv"
    if not gabarito_path.exists():
        print("backtest exige gabarito.csv (chave_nfe,conta_real).", file=sys.stderr)
        return 1
    gabarito: dict[str, str] = {}
    with gabarito_path.open(encoding="utf-8") as fh:
        for linha in csv.DictReader(fh):
            gabarito[linha["chave_nfe"].strip()] = linha["conta_real"].strip()

    lancamentos = _gerar(pasta)
    avaliados = [x for x in lancamentos if x.evento.chave_nfe in gabarito]
    if not avaliados:
        print("Nenhuma nota do gabarito foi processada.", file=sys.stderr)
        return 1

    acertos = 0
    por_origem: Counter[str] = Counter()
    por_origem_acerto: Counter[str] = Counter()
    erros: list[str] = []
    for x in avaliados:
        esperado = gabarito[x.evento.chave_nfe]
        ok = x.conta_classificada == esperado
        acertos += ok
        por_origem[x.origem_classificacao] += 1
        por_origem_acerto[x.origem_classificacao] += ok
        if not ok:
            erros.append(
                f"  {x.evento.chave_nfe[:8]}… {x.evento.contraparte_nome}: "
                f"sugerido {x.conta_classificada} ≠ real {esperado} "
                f"(origem {x.origem_classificacao}, conf {x.confianca})"
            )

    total = len(avaliados)
    print("=" * 56)
    print(f"BACKTEST — {total} nota(s) avaliada(s)")
    print(f"Acurácia geral: {acertos}/{total} = {acertos / total:.0%}")
    print("-" * 56)
    print("Por origem da classificação:")
    for origem, qtd in por_origem.most_common():
        print(
            f"  {origem:>10}: {por_origem_acerto[origem]}/{qtd} = "
            f"{por_origem_acerto[origem] / qtd:.0%}"
        )
    if erros:
        print("-" * 56)
        print("Erros:")
        print("\n".join(erros))
    print("=" * 56)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PoC escriturador contábil (NF-e).")
    sub = parser.add_subparsers(dest="comando", required=True)
    for nome in ("processar", "backtest"):
        p = sub.add_parser(nome)
        p.add_argument("pasta", type=Path, help="pasta com XMLs, plano e histórico")

    args = parser.parse_args(argv)
    try:
        if args.comando == "processar":
            return cmd_processar(args.pasta)
        return cmd_backtest(args.pasta)
    except (ErroExtracao, FileNotFoundError) as e:
        print(f"Erro: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
