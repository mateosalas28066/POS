"""Reglas de cálculo del dominio. Python puro."""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

CERO = Decimal("0")


def subtotal_por_peso(precio_por_kg: Decimal, peso_kg: Decimal) -> Decimal:
    """Subtotal de una línea vendida por peso, redondeado a pesos colombianos (enteros)."""
    if precio_por_kg < CERO or peso_kg < CERO:
        raise ValueError("precio y peso deben ser no negativos")
    return (precio_por_kg * peso_kg).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
