"""Entidades imutáveis: cada operação válida devolve um novo estado da entidade."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, replace
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
from enum import Enum
import re
from uuid import uuid4


class RegraNegocio(ValueError):
    """Rejeição esperada, que pode ser apresentada ao operador."""


def exigir(condicao: bool, mensagem: str) -> None:
    if not condicao:
        raise RegraNegocio(mensagem)


def texto(valor: str, campo: str, limite: int = 160) -> str:
    exigir(isinstance(valor, str) and bool(valor.strip()), f"{campo} é obrigatório.")
    valor = valor.strip()
    exigir(len(valor) <= limite, f"{campo} admite até {limite} caracteres.")
    return valor


def numero(valor: Decimal | str | int) -> Decimal:
    """Aceita vírgula OU ponto, sem milhares; nunca converte float implicitamente."""
    exigir(not isinstance(valor, (float, bool)), "Informe o número como texto ou Decimal.")
    try:
        resultado = Decimal(str(valor).strip().replace(",", "."))
    except (InvalidOperation, ValueError):
        raise RegraNegocio("Número inválido. Use 12,5 ou 12.5, sem separador de milhar.") from None
    exigir(resultado.is_finite(), "O número precisa ser finito.")
    exigir(abs(resultado) <= Decimal("1000000000000"), "Número acima do limite de 1 trilhão.")
    exigir(resultado == 0 or resultado.as_tuple().exponent >= -12, "Número com precisão excessiva.")
    return resultado


def casas(valor: Decimal) -> int:
    return max(0, -valor.normalize().as_tuple().exponent)


def dinheiro(valor: Decimal) -> Decimal:
    return valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class Unidade(str, Enum):
    CHAPA = "CHAPA"
    UN = "UN"
    M = "M"
    L = "L"
    KG = "KG"

    def validar(self, valor: Decimal | str | int, zero: bool = False) -> Decimal:
        valor = numero(valor)
        exigir(valor >= 0 if zero else valor > 0,
               "Quantidade deve ser não negativa." if zero else "Quantidade deve ser positiva.")
        limite = 0 if self in (Unidade.CHAPA, Unidade.UN) else 3
        exigir(casas(valor) <= limite,
               f"{self.value} exige inteiro." if limite == 0 else f"{self.value} admite até três casas decimais.")
        return valor


class StatusProjeto(str, Enum):
    PLANEJADO = "PLANEJADO"
    RESERVADO = "RESERVADO"
    CONCLUIDO = "CONCLUIDO"
    CANCELADO = "CANCELADO"


class TipoMovimento(str, Enum):
    ENTRADA = "ENTRADA"
    RESERVA = "RESERVA"
    LIBERACAO = "LIBERACAO"
    CONSUMO = "CONSUMO"
    AJUSTE = "AJUSTE"


@dataclass(frozen=True, kw_only=True)
class Material(ABC):
    sku: str
    nome: str
    unidade: Unidade
    minimo: Decimal
    alvo: Decimal
    id: str = field(default_factory=lambda: str(uuid4()))
    fisico: Decimal = Decimal(0)
    reservado: Decimal = Decimal(0)
    custo_medio: Decimal = Decimal(0)

    def __post_init__(self) -> None:
        sku = texto(self.sku, "SKU", 30).upper()
        exigir(bool(re.fullmatch(r"[A-Z0-9][A-Z0-9._-]{0,29}", sku)),
               "SKU aceita letras sem acento, números, ponto, hífen e sublinhado.")
        object.__setattr__(self, "sku", sku)
        object.__setattr__(self, "nome", texto(self.nome, "Nome"))
        texto(self.id, "Identificador")
        exigir(isinstance(self.unidade, Unidade), "Unidade inválida.")
        for atributo in ("minimo", "alvo", "fisico", "reservado"):
            object.__setattr__(self, atributo, self.unidade.validar(getattr(self, atributo), zero=True))
        custo = numero(self.custo_medio)
        exigir(custo >= 0 and casas(custo) <= 4, "Custo médio inválido.")
        object.__setattr__(self, "custo_medio", custo)
        exigir(self.alvo > self.minimo, "Alvo precisa ser maior que o mínimo.")
        exigir(self.reservado <= self.fisico, "Reservado não pode superar o estoque físico.")

    @property
    def disponivel(self) -> Decimal:
        return self.fisico - self.reservado

    @property
    def valor_estoque(self) -> Decimal:
        return self.fisico * self.custo_medio

    @property
    def estoque_baixo(self) -> bool:
        return self.disponivel <= self.minimo

    @property
    @abstractmethod
    def caracteristicas(self) -> str:
        """Descrição específica de cada espécie de material."""

    def receber(self, quantidade: Decimal, custo: Decimal) -> Material:
        quantidade = self.unidade.validar(quantidade)
        custo = numero(custo)
        exigir(custo > 0 and casas(custo) <= 2, "Custo deve ser positivo, com até duas casas.")
        saldo = self.fisico + quantidade
        with localcontext() as contexto:
            contexto.prec = 40
            medio = ((self.valor_estoque + quantidade * custo) / saldo).quantize(
                Decimal("0.0001"), rounding=ROUND_HALF_UP)
        return replace(self, fisico=saldo, custo_medio=medio)

    def validar_reserva(self, quantidade: Decimal) -> Decimal:
        quantidade = self.unidade.validar(quantidade)
        exigir(quantidade <= self.disponivel,
               f"Estoque insuficiente: {self.sku}. Disponível {self.disponivel} {self.unidade.value}; solicitado {quantidade}.")
        return quantidade

    def reservar(self, quantidade: Decimal) -> Material:
        return replace(self, reservado=self.reservado + self.validar_reserva(quantidade))

    def _validar_reservado(self, quantidade: Decimal) -> Decimal:
        quantidade = self.unidade.validar(quantidade)
        exigir(quantidade <= self.reservado, "Quantidade supera o reservado.")
        return quantidade

    def liberar(self, quantidade: Decimal) -> Material:
        return replace(self, reservado=self.reservado - self._validar_reservado(quantidade))

    def consumir_reserva(self, quantidade: Decimal) -> Material:
        quantidade = self._validar_reservado(quantidade)
        return replace(self, fisico=self.fisico - quantidade, reservado=self.reservado - quantidade)

    def contar(self, contado: Decimal) -> tuple[Material, Decimal]:
        contado = self.unidade.validar(contado, zero=True)
        exigir(contado >= self.reservado, f"Contagem não pode ficar abaixo do reservado ({self.reservado}).")
        return replace(self, fisico=contado), contado - self.fisico


@dataclass(frozen=True, kw_only=True)
class Chapa(Material):
    comprimento: Decimal
    largura: Decimal
    espessura: Decimal
    acabamento: str

    def __post_init__(self) -> None:
        super().__post_init__()
        exigir(self.unidade is Unidade.CHAPA, "Chapa exige unidade CHAPA.")
        for atributo in ("comprimento", "largura", "espessura"):
            valor = numero(getattr(self, atributo))
            exigir(valor > 0, "Dimensões em mm precisam ser positivas.")
            object.__setattr__(self, atributo, valor)
        object.__setattr__(self, "acabamento", texto(self.acabamento, "Acabamento"))

    @property
    def caracteristicas(self) -> str:
        return f"{self.comprimento} × {self.largura} × {self.espessura} mm · {self.acabamento}"


@dataclass(frozen=True, kw_only=True)
class Insumo(Material):
    especificacao: str

    def __post_init__(self) -> None:
        super().__post_init__()
        exigir(self.unidade is not Unidade.CHAPA, "Insumo não pode usar unidade CHAPA.")
        object.__setattr__(self, "especificacao", texto(self.especificacao, "Especificação"))

    @property
    def caracteristicas(self) -> str:
        return self.especificacao


@dataclass(frozen=True)
class ItemProjeto:
    material_id: str
    quantidade: Decimal

    def __post_init__(self) -> None:
        texto(self.material_id, "Material")
        quantidade = numero(self.quantidade)
        exigir(quantidade > 0, "Item exige quantidade positiva.")
        object.__setattr__(self, "quantidade", quantidade)


@dataclass(frozen=True, kw_only=True)
class Projeto:
    nome: str
    cliente: str
    itens: tuple[ItemProjeto, ...]
    id: str = field(default_factory=lambda: str(uuid4()))
    status: StatusProjeto = StatusProjeto.PLANEJADO

    def __post_init__(self) -> None:
        texto(self.id, "Identificador")
        object.__setattr__(self, "nome", texto(self.nome, "Nome do projeto"))
        object.__setattr__(self, "cliente", texto(self.cliente, "Cliente"))
        object.__setattr__(self, "itens", tuple(self.itens))
        exigir(isinstance(self.status, StatusProjeto), "Estado de projeto inválido.")
        exigir(bool(self.itens) and all(isinstance(i, ItemProjeto) for i in self.itens),
               "Projeto precisa de pelo menos um item válido.")
        exigir(len({i.material_id for i in self.itens}) == len(self.itens), "Material duplicado no projeto.")

    def exigir_planejado(self) -> None:
        exigir(self.status is StatusProjeto.PLANEJADO, "Somente projeto PLANEJADO pode ser editado ou reservado.")

    def editar(self, nome: str, cliente: str, itens: tuple[ItemProjeto, ...]) -> Projeto:
        self.exigir_planejado()
        return replace(self, nome=nome, cliente=cliente, itens=itens)

    def reservar(self) -> Projeto:
        self.exigir_planejado()
        return replace(self, status=StatusProjeto.RESERVADO)

    def concluir(self) -> Projeto:
        exigir(self.status is StatusProjeto.RESERVADO, "Somente projeto RESERVADO pode ser concluído.")
        return replace(self, status=StatusProjeto.CONCLUIDO)

    def cancelar(self) -> Projeto:
        exigir(self.status in (StatusProjeto.PLANEJADO, StatusProjeto.RESERVADO),
               "Projeto concluído ou cancelado não pode ser cancelado.")
        return replace(self, status=StatusProjeto.CANCELADO)


@dataclass(frozen=True)
class Movimentacao:
    id: str
    instante: str
    tipo: TipoMovimento
    material_id: str
    sku: str
    nome: str
    unidade: Unidade
    quantidade: Decimal
    custo_unitario: Decimal
    fisico_apos: Decimal
    reservado_apos: Decimal
    referencia: str
    projeto_id: str | None = None


@dataclass(frozen=True)
class RegistroAuditoria:
    instante: str
    acao: str
    detalhe: str


@dataclass
class EstadoEstoque:
    materiais: dict[str, Material] = field(default_factory=dict)
    projetos: dict[str, Projeto] = field(default_factory=dict)
    movimentos: list[Movimentacao] = field(default_factory=list)
    alertas: set[str] = field(default_factory=set)
    auditoria: list[RegistroAuditoria] = field(default_factory=list)

    def material(self, id: str) -> Material:
        exigir(id in self.materiais, "Material não encontrado.")
        return self.materiais[id]

    def projeto(self, id: str) -> Projeto:
        exigir(id in self.projetos, "Projeto não encontrado.")
        return self.projetos[id]

    def guardar_material(self, material: Material) -> None:
        exigir(all(m.id == material.id or m.sku != material.sku for m in self.materiais.values()),
               f"SKU já cadastrado: {material.sku}.")
        self.materiais[material.id] = material

    def guardar_projeto(self, projeto: Projeto) -> None:
        for item in projeto.itens:
            self.material(item.material_id).unidade.validar(item.quantidade)
        self.projetos[projeto.id] = projeto

    def excluir_material(self, id: str) -> None:
        material = self.material(id)
        exigir(material.fisico == material.reservado == 0, "Material com saldo não pode ser excluído.")
        exigir(not any(m.material_id == id for m in self.movimentos)
               and not any(i.material_id == id for p in self.projetos.values() for i in p.itens),
               "Material possui histórico ou projeto e deve ser preservado.")
        del self.materiais[id]

    def validar(self) -> None:
        """Confere também relações entre agregados antes de confirmar ou restaurar."""
        exigir(all(k == m.id for k, m in self.materiais.items()), "Identificador de material inconsistente.")
        exigir(all(k == p.id for k, p in self.projetos.items()), "Identificador de projeto inconsistente.")
        exigir(len({m.sku for m in self.materiais.values()}) == len(self.materiais), "SKU duplicado na base.")
        reservas = {id: Decimal(0) for id in self.materiais}
        for projeto in self.projetos.values():
            for item in projeto.itens:
                self.material(item.material_id).unidade.validar(item.quantidade)
                if projeto.status is StatusProjeto.RESERVADO:
                    reservas[item.material_id] += item.quantidade
        exigir(all(m.reservado == reservas[m.id] for m in self.materiais.values()),
               "Reservas não correspondem aos projetos reservados.")
        exigir(self.alertas == {m.id for m in self.materiais.values() if m.estoque_baixo},
               "Alertas inconsistentes com os saldos.")
        exigir(len({m.id for m in self.movimentos}) == len(self.movimentos), "Movimento duplicado.")
        for movimento in self.movimentos:
            self.material(movimento.material_id)
            if movimento.projeto_id is not None:
                self.projeto(movimento.projeto_id)
            exigir(0 <= movimento.reservado_apos <= movimento.fisico_apos,
                   "Saldo histórico inválido.")
            exigir(isinstance(movimento.tipo, TipoMovimento), "Tipo de movimento inválido.")
            movimento.unidade.validar(abs(movimento.quantidade), zero=movimento.tipo is TipoMovimento.AJUSTE)
            exigir(movimento.tipo is TipoMovimento.AJUSTE or movimento.quantidade > 0, "Movimento inválido.")
            exigir(numero(movimento.custo_unitario) >= 0, "Custo histórico inválido.")
