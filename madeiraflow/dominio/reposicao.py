"""Strategy: políticas substituíveis para a mesma decisão de compra."""

from decimal import Decimal
from typing import Protocol

from .modelos import Material


class PoliticaReposicao(Protocol):
    def sugerir(self, material: Material) -> Decimal: ...


class ReposicaoMinima:
    def sugerir(self, material: Material) -> Decimal:
        return max(Decimal(0), material.minimo - material.disponivel) if material.estoque_baixo else Decimal(0)


class ReposicaoAlvo:
    def sugerir(self, material: Material) -> Decimal:
        return max(Decimal(0), material.alvo - material.disponivel) if material.estoque_baixo else Decimal(0)
