"""Parser determinístico de NF-e (XML) → ``EventoEconomico``.

Lê os campos essenciais para classificação contábil. Valida a soma dos itens
contra o ``vNF`` (princípio: sempre conferir a extração contra um total).
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from xml.etree import ElementTree as ET

from .modelos import EventoEconomico, ItemNota

# NF-e usa este namespace fixo em todos os elementos.
NS = {"n": "http://www.portalfiscal.inf.br/nfe"}


class ErroExtracao(Exception):
    """Falha de parsing ou de validação contra totais."""


def _texto(elem: ET.Element | None, caminho: str, default: str = "") -> str:
    if elem is None:
        return default
    achado = elem.find(caminho, NS)
    return achado.text.strip() if achado is not None and achado.text else default


def parse_nfe(caminho: str | Path) -> EventoEconomico:
    """Converte um arquivo NF-e XML em ``EventoEconomico`` validado."""
    caminho = Path(caminho)
    conteudo = caminho.read_bytes()
    hash_arquivo = "sha256:" + hashlib.sha256(conteudo).hexdigest()

    raiz = ET.fromstring(conteudo)
    inf = raiz.find(".//n:infNFe", NS)
    if inf is None:
        raise ErroExtracao(f"{caminho.name}: infNFe não encontrado")

    chave = (inf.get("Id") or "").removeprefix("NFe")

    ide = inf.find("n:ide", NS)
    tp_nf = _texto(ide, "n:tpNF")  # 0 = entrada, 1 = saída
    tipo_operacao = "saida" if tp_nf == "1" else "entrada"
    natureza_operacao = _texto(ide, "n:natOp")
    data_emi = _texto(ide, "n:dhEmi")[:10] or _texto(ide, "n:dEmi")[:10]

    emit = inf.find("n:emit", NS)
    dest = inf.find("n:dest", NS)
    # Na entrada (compra), a empresa é o destinatário → contraparte é o emitente.
    # Na saída (venda), a empresa é o emitente → contraparte é o destinatário.
    contraparte = emit if tipo_operacao == "entrada" else dest
    contraparte_cnpj = _texto(contraparte, "n:CNPJ") or _texto(contraparte, "n:CPF")
    contraparte_nome = _texto(contraparte, "n:xNome")

    itens: list[ItemNota] = []
    for det in inf.findall("n:det", NS):
        prod = det.find("n:prod", NS)
        if prod is None:
            continue
        itens.append(
            ItemNota(
                descricao=_texto(prod, "n:xProd"),
                ncm=_texto(prod, "n:NCM"),
                cfop=_texto(prod, "n:CFOP"),
                valor=float(_texto(prod, "n:vProd", "0") or 0),
            )
        )

    v_nf = float(_texto(inf, "n:total/n:ICMSTot/n:vNF", "0") or 0)
    _validar_total(caminho.name, itens, v_nf)

    return EventoEconomico(
        chave_nfe=chave,
        tipo_operacao=tipo_operacao,
        natureza_operacao=natureza_operacao,
        data_competencia=data_emi,
        contraparte_cnpj=contraparte_cnpj,
        contraparte_nome=contraparte_nome,
        valor_total=round(v_nf, 2),
        itens=itens,
        arquivo=caminho.name,
        hash_arquivo=hash_arquivo,
    )


def _validar_total(nome: str, itens: list[ItemNota], v_nf: float) -> None:
    """Confere a soma dos itens contra o vNF, com tolerância de centavos."""
    soma = round(sum(i.valor for i in itens), 2)
    if abs(soma - v_nf) > 0.01:
        raise ErroExtracao(f"{nome}: soma dos itens ({soma}) diverge de vNF ({v_nf})")


def carregar_pasta(pasta: str | Path) -> list[EventoEconomico]:
    """Faz parse de todos os ``*.xml`` da pasta, ignorando os que falham."""
    eventos: list[EventoEconomico] = []
    for arquivo in sorted(Path(pasta).glob("*.xml")):
        eventos.append(parse_nfe(arquivo))
    return eventos
