"""Demonstração construída pelos mesmos serviços; gravada integralmente uma vez."""

from decimal import Decimal as D

from madeiraflow.aplicacao.portas import RepositorioEstado
from madeiraflow.aplicacao.servicos import DadosMaterial
from madeiraflow.composicao import montar
from madeiraflow.dominio.modelos import ItemProjeto, Unidade, exigir
from .repositorios import MemoriaRepositorio


def preencher(repositorio: RepositorioEstado) -> None:
    anterior = repositorio.carregar()
    exigir(not anterior.estado.materiais and not anterior.estado.projetos
           and not anterior.estado.auditoria, "Demonstração exige uma base nova.")
    memoria = MemoriaRepositorio()
    s = montar(memoria)
    materiais = [
        ("MDF-BR18", "MDF branco TX 18 mm", Unidade.CHAPA, "3", "12", "Branco TX, duas faces", "10", "289.90"),
        ("MDF-CAR15", "MDF carvalho 15 mm", Unidade.CHAPA, "2", "8", "Carvalho natural", "6", "319.00"),
        ("PAR-4X40", "Parafuso 4 × 40 mm", Unidade.UN, "100", "500", "Cabeça chata, zincado", "500", "0.12"),
        ("CAV-8X30", "Cavilha 8 × 30 mm", Unidade.UN, "80", "400", "Madeira estriada", "150", "0.18"),
        ("FITA-BR22", "Fita de borda branca 22 mm", Unidade.M, "25", "100", "PVC 0,45 mm", "80", "2.50"),
        ("COLA-PVA", "Cola PVA extra", Unidade.KG, "2", "10", "Uso interno", "1.5", "28.90"),
    ]
    ids = []
    for sku, nome, unidade, minimo, alvo, descricao, quantidade, custo in materiais:
        id = s.cadastro.cadastrar(DadosMaterial(
            sku=sku, nome=nome, unidade=unidade, minimo=D(minimo), alvo=D(alvo), descricao=descricao,
            comprimento=D(2750), largura=D(1850), espessura=D(18 if sku == "MDF-BR18" else 15)))
        s.estoque.receber(id, D(quantidade), D(custo), "NF demonstrativa · fornecedor exemplo")
        ids.append(id)
    cozinha = s.projetos.criar("Cozinha Aurora", "Marina Oliveira", tuple(
        ItemProjeto(ids[i], D(q)) for i, q in [(0, "4"), (2, "180"), (3, "90"), (4, "32.5")]))
    s.projetos.reservar(cozinha)
    s.projetos.criar("Armário Ipê", "Carlos Santos", tuple(
        ItemProjeto(ids[i], D(q)) for i, q in [(1, "3"), (2, "100"), (3, "40")]))
    repositorio.salvar(s.consulta.consultar(), anterior.revisao)
