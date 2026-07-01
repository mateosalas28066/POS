"""Ayudante de conteo de efectivo por denominaciones (COP). Cálculo puro, sin Qt."""
from __future__ import annotations

from decimal import Decimal

# Denominaciones colombianas de mayor a menor; 1000 como una sola fila (moneda+billete).
DENOMINACIONES: tuple[int, ...] = (
    100000, 50000, 20000, 10000, 5000, 2000, 1000, 500, 200, 100, 50)


def total_conteo(conteo: dict[int, int]) -> Decimal:
    """Σ denominación × cantidad. Ignora ceros; rechaza cantidades negativas."""
    total = Decimal("0")
    for denominacion, cantidad in conteo.items():
        if cantidad < 0:
            raise ValueError("la cantidad de una denominación no puede ser negativa")
        total += Decimal(denominacion) * cantidad
    return total
