from datetime import datetime
from decimal import Decimal

from madeiraflow.dominio.modelos import dinheiro


def quantidade(valor: Decimal) -> str:
    return format(valor, "f").rstrip("0").rstrip(".").replace(".", ",") if "." in format(valor, "f") else str(valor)


def moeda(valor: Decimal) -> str:
    return "R$ " + f"{dinheiro(valor):,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def horario(instante: str) -> str:
    return datetime.fromisoformat(instante).astimezone().strftime("%d/%m/%Y %H:%M:%S")
