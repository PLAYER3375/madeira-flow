from collections.abc import Callable
from typing import TypeVar

from madeiraflow.dominio.modelos import EstadoEstoque
from .eventos import EventoDominio, PublicadorEventos
from .portas import RepositorioEstado

T = TypeVar("T")


class Transacoes:
    def __init__(self, repositorio: RepositorioEstado, eventos: PublicadorEventos,
                 relogio: Callable[[], str]) -> None:
        self.repositorio = repositorio
        self.eventos = eventos
        self.relogio = relogio

    def executar(self, acao: str, detalhe: str, operacao: Callable[[EstadoEstoque], T]) -> T:
        snapshot = self.repositorio.carregar()  # Sempre uma cópia isolada.
        resultado = operacao(snapshot.estado)
        self.eventos.publicar(EventoDominio(acao, detalhe, self.relogio()), snapshot.estado)
        snapshot.estado.validar()
        self.repositorio.salvar(snapshot.estado, snapshot.revisao)
        return resultado  # Só retorna sucesso depois do commit.
