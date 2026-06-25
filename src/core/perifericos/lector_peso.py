"""Puerto LectorPeso y adaptador manual. Sin hardware, sin Qt."""
from __future__ import annotations

from decimal import Decimal
from typing import Protocol

CERO = Decimal("0")


class LectorPeso(Protocol):
    def leer_peso(self) -> Decimal:
        """Peso en kilogramos del ítem a vender."""
        ...


class IngresoManual:
    """Fallback sin balanza: el cajero teclea el peso."""

    def __init__(self, peso_kg: Decimal) -> None:
        if peso_kg < CERO:
            raise ValueError("peso no puede ser negativo")
        self._peso = peso_kg

    def leer_peso(self) -> Decimal:
        return self._peso
