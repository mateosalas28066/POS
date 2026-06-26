"""Helpers de presentación: dinero, cantidades y fechas. Solo stdlib."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal


def formato_moneda(v: Decimal) -> str:
    """Pesos colombianos sin decimales, separador de miles con punto."""
    entero = int(v.to_integral_value())
    signo = "-" if entero < 0 else ""
    miles = f"{abs(entero):,}".replace(",", ".")
    return f"{signo}$ {miles}"


def formato_cantidad(v: Decimal, unidad: str) -> str:
    """Entero sin decimales; fraccionario con coma decimal (es-CO)."""
    if v == v.to_integral_value():
        texto = str(int(v))
    else:
        texto = format(v.normalize(), "f").replace(".", ",")
    return f"{texto} {unidad}"


def formato_fecha(dt: datetime) -> str:
    return dt.strftime("%d/%m/%Y %H:%M")
