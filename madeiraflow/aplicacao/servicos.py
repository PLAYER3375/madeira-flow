from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from decimal import Decimal
from uuid import uuid4

from madeiraflow.dominio.modelos import (
    Chapa, EstadoEstoque, Insumo, ItemProjeto, Material, Movimentacao, Projeto,
    StatusProjeto, TipoMovimento, Unidade, exigir, texto,
)
from madeiraflow.dominio.reposicao import PoliticaReposicao
from .transacoes import Transacoes


@dataclass(frozen=True, kw_only=True)
class DadosMaterial:
    sku: str
    nome: str
    unidade: Unidade
    minimo: Decimal
    alvo: Decimal
    descricao: str
    comprimento: Decimal = Decimal(0)
    largura: Decimal = Decimal(0)
    espessura: Decimal = Decimal(0)

    def construir(self, id: str | None = None) -> Material:
        comuns = dict(sku=self.sku, nome=self.nome, unidade=self.unidade,
                      minimo=self.minimo, alvo=self.alvo)
        if id is not None:
            comuns["id"] = id
        if self.unidade is Unidade.CHAPA:
            return Chapa(**comuns, comprimento=self.comprimento, largura=self.largura,
                         espessura=self.espessura, acabamento=self.descricao)
        return Insumo(**comuns, especificacao=self.descricao)


class CadastroService:
    def __init__(self, transacoes: Transacoes) -> None:
        self.transacoes = transacoes

    def cadastrar(self, dados: DadosMaterial) -> str:
        material = dados.construir()

        def operacao(estado: EstadoEstoque) -> str:
            estado.guardar_material(material)
            return material.id

        return self.transacoes.executar("MATERIAL_CADASTRADO", material.sku, operacao)

    def editar(self, id: str, dados: DadosMaterial) -> None:
        def operacao(estado: EstadoEstoque) -> None:
            anterior = estado.material(id)
            exigir(anterior.unidade is dados.unidade, "Tipo e unidade não podem mudar após o cadastro.")
            novo = dados.construir(id)
            estado.guardar_material(replace(novo, fisico=anterior.fisico, reservado=anterior.reservado,
                                            custo_medio=anterior.custo_medio))

        self.transacoes.executar("MATERIAL_EDITADO", id, operacao)

    def excluir(self, id: str) -> None:
        self.transacoes.executar("MATERIAL_EXCLUIDO", id, lambda estado: estado.excluir_material(id))


def registrar(estado: EstadoEstoque, material: Material, tipo: TipoMovimento,
              quantidade: Decimal, custo: Decimal, referencia: str, instante: str,
              projeto_id: str | None = None) -> None:
    estado.movimentos.append(Movimentacao(
        str(uuid4()), instante, tipo, material.id, material.sku, material.nome, material.unidade,
        quantidade, custo, material.fisico, material.reservado, referencia, projeto_id))


class EstoqueService:
    def __init__(self, transacoes: Transacoes, relogio: Callable[[], str]) -> None:
        self.transacoes = transacoes
        self.relogio = relogio

    def receber(self, id: str, quantidade: Decimal, custo: Decimal, referencia: str) -> None:
        referencia = texto(referencia, "Referência do recebimento", 500)

        def operacao(estado: EstadoEstoque) -> None:
            material = estado.material(id).receber(quantidade, custo)
            estado.guardar_material(material)
            registrar(estado, material, TipoMovimento.ENTRADA, material.unidade.validar(quantidade),
                      custo, referencia, self.relogio())

        self.transacoes.executar("MATERIAL_RECEBIDO", referencia, operacao)

    def contar(self, id: str, contado: Decimal, justificativa: str) -> None:
        justificativa = texto(justificativa, "Justificativa", 500)

        def operacao(estado: EstadoEstoque) -> None:
            material, diferenca = estado.material(id).contar(contado)
            estado.guardar_material(material)
            registrar(estado, material, TipoMovimento.AJUSTE, diferenca, material.custo_medio,
                      justificativa, self.relogio())

        self.transacoes.executar("INVENTARIO_CONFERIDO", justificativa, operacao)


class ProjetoService:
    def __init__(self, transacoes: Transacoes, relogio: Callable[[], str]) -> None:
        self.transacoes = transacoes
        self.relogio = relogio

    def criar(self, nome: str, cliente: str, itens: tuple[ItemProjeto, ...]) -> str:
        projeto = Projeto(nome=nome, cliente=cliente, itens=itens)

        def operacao(estado: EstadoEstoque) -> str:
            estado.guardar_projeto(projeto)
            return projeto.id

        return self.transacoes.executar("PROJETO_CRIADO", nome, operacao)

    def editar(self, id: str, nome: str, cliente: str, itens: tuple[ItemProjeto, ...]) -> None:
        def operacao(estado: EstadoEstoque) -> None:
            estado.guardar_projeto(estado.projeto(id).editar(nome, cliente, itens))

        self.transacoes.executar("PROJETO_EDITADO", id, operacao)

    def reservar(self, id: str) -> None:
        def operacao(estado: EstadoEstoque) -> None:
            projeto = estado.projeto(id)
            projeto.exigir_planejado()
            for item in projeto.itens:  # Valida todos antes de alterar o primeiro.
                estado.material(item.material_id).validar_reserva(item.quantidade)
            for item in projeto.itens:
                material = estado.material(item.material_id).reservar(item.quantidade)
                self._registrar(estado, projeto, item, material, TipoMovimento.RESERVA)
            estado.guardar_projeto(projeto.reservar())

        self.transacoes.executar("PROJETO_RESERVADO", id, operacao)

    def concluir(self, id: str) -> None:
        def operacao(estado: EstadoEstoque) -> None:
            projeto = estado.projeto(id)
            novo = projeto.concluir()  # Guarda de estado antes de consumir.
            for item in projeto.itens:
                material = estado.material(item.material_id).consumir_reserva(item.quantidade)
                self._registrar(estado, projeto, item, material, TipoMovimento.CONSUMO)
            estado.guardar_projeto(novo)

        self.transacoes.executar("PRODUCAO_CONCLUIDA", id, operacao)

    def cancelar(self, id: str) -> None:
        def operacao(estado: EstadoEstoque) -> None:
            projeto = estado.projeto(id)
            novo = projeto.cancelar()
            if projeto.status is StatusProjeto.RESERVADO:
                for item in projeto.itens:
                    material = estado.material(item.material_id).liberar(item.quantidade)
                    self._registrar(estado, projeto, item, material, TipoMovimento.LIBERACAO)
            estado.guardar_projeto(novo)

        self.transacoes.executar("PROJETO_CANCELADO", id, operacao)

    def _registrar(self, estado: EstadoEstoque, projeto: Projeto, item: ItemProjeto,
                   material: Material, tipo: TipoMovimento) -> None:
        estado.guardar_material(material)
        registrar(estado, material, tipo, item.quantidade, material.custo_medio,
                  f"{projeto.nome} · {projeto.cliente}", self.relogio(), projeto.id)


@dataclass(frozen=True)
class SugestaoCompra:
    material: Material
    quantidade: Decimal

    @property
    def estimativa(self) -> Decimal:
        return self.quantidade * self.material.custo_medio


class ConsultaService:
    def __init__(self, transacoes: Transacoes) -> None:
        self.transacoes = transacoes

    def consultar(self) -> EstadoEstoque:
        return self.transacoes.repositorio.carregar().estado

    def pesquisar(self, busca: str = "") -> list[Material]:
        termo = busca.strip().casefold()
        return [m for m in self.consultar().materiais.values()
                if termo in f"{m.sku} {m.nome}".casefold()]

    def sugerir_compras(self, politica: PoliticaReposicao) -> list[SugestaoCompra]:
        return [SugestaoCompra(m, politica.sugerir(m)) for m in self.consultar().materiais.values()
                if m.estoque_baixo]


@dataclass(frozen=True)
class Servicos:
    cadastro: CadastroService
    estoque: EstoqueService
    projetos: ProjetoService
    consulta: ConsultaService
