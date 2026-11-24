"""Composition root: liga contratos e implementações por injeção no construtor."""

from collections.abc import Callable
from datetime import datetime, timezone

from .aplicacao.eventos import AlertaEstoqueObserver, AuditoriaObserver, PublicadorEventos
from .aplicacao.portas import RepositorioEstado
from .aplicacao.servicos import CadastroService, ConsultaService, EstoqueService, ProjetoService, Servicos
from .aplicacao.transacoes import Transacoes


def agora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def montar(repositorio: RepositorioEstado, relogio: Callable[[], str] = agora,
           eventos: PublicadorEventos | None = None) -> Servicos:
    if eventos is None:
        eventos = PublicadorEventos()
        eventos.inscrever(AlertaEstoqueObserver())
        eventos.inscrever(AuditoriaObserver())
    transacoes = Transacoes(repositorio, eventos, relogio)
    return Servicos(CadastroService(transacoes), EstoqueService(transacoes, relogio),
                    ProjetoService(transacoes, relogio), ConsultaService(transacoes))
