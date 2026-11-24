from dataclasses import replace
from decimal import Decimal as D
import unittest

from madeiraflow.aplicacao.servicos import DadosMaterial
from madeiraflow.composicao import montar
from madeiraflow.dominio.modelos import ItemProjeto, Unidade
from madeiraflow.infraestrutura.repositorios import MemoriaRepositorio

INSTANTE = "2026-11-13T15:00:00+00:00"


def dados(sku="PAR", unidade=Unidade.UN, **alteracoes):
    return replace(DadosMaterial(sku=sku, nome="Parafuso", unidade=unidade,
                                minimo=D(2), alvo=D(10), descricao="Zincado",
                                comprimento=D(2750), largura=D(1850), espessura=D(18)), **alteracoes)


class Base(unittest.TestCase):
    def setUp(self):
        self.repo = MemoriaRepositorio()
        self.s = montar(self.repo, lambda: INSTANTE)

    def material(self, sku="PAR", saldo="10", unidade=Unidade.UN, **alteracoes):
        id = self.s.cadastro.cadastrar(dados(sku, unidade, **alteracoes))
        if D(saldo):
            self.s.estoque.receber(id, D(saldo), D("2.00"), "NF 1")
        return id

    def projeto(self, *itens):
        return self.s.projetos.criar("Balcão", "Cliente", tuple(ItemProjeto(id, D(q)) for id, q in itens))

    def estado(self):
        return self.s.consulta.consultar()
