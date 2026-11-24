"""Observer síncrono: reações locais participam da mesma confirmação."""

from dataclasses import dataclass
from typing import Protocol

from madeiraflow.dominio.modelos import EstadoEstoque, RegistroAuditoria


@dataclass(frozen=True)
class EventoDominio:
    acao: str
    detalhe: str
    instante: str


class ObservadorEstoque(Protocol):
    def atualizar(self, evento: EventoDominio, estado: EstadoEstoque) -> None: ...


class PublicadorEventos:
    def __init__(self) -> None:
        self._observadores: list[ObservadorEstoque] = []

    def inscrever(self, observador: ObservadorEstoque) -> None:
        if observador not in self._observadores:
            self._observadores.append(observador)

    def remover(self, observador: ObservadorEstoque) -> None:
        self._observadores.remove(observador)

    def publicar(self, evento: EventoDominio, estado: EstadoEstoque) -> None:
        for observador in tuple(self._observadores):
            observador.atualizar(evento, estado)


class AlertaEstoqueObserver:
    def atualizar(self, evento: EventoDominio, estado: EstadoEstoque) -> None:
        estado.alertas = {m.id for m in estado.materiais.values() if m.estoque_baixo}


class AuditoriaObserver:
    def atualizar(self, evento: EventoDominio, estado: EstadoEstoque) -> None:
        estado.auditoria.append(RegistroAuditoria(evento.instante, evento.acao, evento.detalhe))
