from dataclasses import dataclass
from typing import Protocol

from madeiraflow.dominio.modelos import EstadoEstoque


class ErroPersistencia(RuntimeError):
    """Falha técnica tratada pela fronteira de interação."""


class ConflitoDeVersao(ErroPersistencia):
    """Outro processo confirmou uma alteração desde a leitura."""


@dataclass(frozen=True)
class Snapshot:
    estado: EstadoEstoque
    revisao: int


class RepositorioEstado(Protocol):
    def carregar(self) -> Snapshot: ...
    def salvar(self, estado: EstadoEstoque, revisao: int) -> None: ...
