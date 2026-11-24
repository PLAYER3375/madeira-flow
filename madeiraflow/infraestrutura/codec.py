"""JSON explícito e versionado: números decimais são armazenados como texto."""

from dataclasses import asdict
from decimal import Decimal
import json

from madeiraflow.dominio.modelos import (
    Chapa, EstadoEstoque, Insumo, ItemProjeto, Movimentacao, Projeto,
    RegistroAuditoria, StatusProjeto, TipoMovimento, Unidade, exigir, numero,
)

LIMITE_BYTES = 32 * 1024 * 1024


def serializar(estado: EstadoEstoque) -> str:
    estado.validar()
    dados = {
        "formato": 1,
        "materiais": [{**asdict(m), "tipo": "chapa" if isinstance(m, Chapa) else "insumo"}
                      for m in estado.materiais.values()],
        "projetos": [asdict(p) for p in estado.projetos.values()],
        "movimentos": [asdict(m) for m in estado.movimentos],
        "alertas": sorted(estado.alertas),
        "auditoria": [asdict(a) for a in estado.auditoria],
    }

    def converter(valor: object) -> str:
        if isinstance(valor, Decimal):
            return str(valor)
        raise TypeError(f"Tipo não serializável: {type(valor).__name__}")

    conteudo = json.dumps(dados, default=converter, ensure_ascii=False, allow_nan=False)
    exigir(len(conteudo.encode("utf-8")) <= LIMITE_BYTES, "Base excede o limite de 32 MB de conteúdo.")
    return conteudo


def desserializar(conteudo: str) -> EstadoEstoque:
    exigir(len(conteudo.encode("utf-8")) <= LIMITE_BYTES, "Conteúdo da base muito grande.")
    dados = json.loads(conteudo)
    exigir(dados["formato"] == 1, "Versão de conteúdo não suportada.")
    estado = EstadoEstoque()
    for registro in dados["materiais"]:
        registro = dict(registro)
        tipo = registro.pop("tipo")
        exigir(tipo in ("chapa", "insumo"), "Tipo de material desconhecido.")
        registro["unidade"] = Unidade(registro["unidade"])
        classe = Chapa if tipo == "chapa" else Insumo
        material = classe(**registro)
        exigir(material.id not in estado.materiais, "Identificador de material duplicado.")
        estado.guardar_material(material)
    for registro in dados["projetos"]:
        registro = dict(registro)
        registro["status"] = StatusProjeto(registro["status"])
        registro["itens"] = tuple(ItemProjeto(**item) for item in registro["itens"])
        projeto = Projeto(**registro)
        exigir(projeto.id not in estado.projetos, "Identificador de projeto duplicado.")
        estado.guardar_projeto(projeto)
    for registro in dados["movimentos"]:
        registro = dict(registro)
        registro["tipo"] = TipoMovimento(registro["tipo"])
        registro["unidade"] = Unidade(registro["unidade"])
        for atributo in ("quantidade", "custo_unitario", "fisico_apos", "reservado_apos"):
            registro[atributo] = numero(registro[atributo])
        estado.movimentos.append(Movimentacao(**registro))
    estado.alertas = set(dados["alertas"])
    estado.auditoria = [RegistroAuditoria(**a) for a in dados["auditoria"]]
    estado.validar()
    return estado
