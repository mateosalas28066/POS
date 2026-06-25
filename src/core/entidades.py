"""Entidades de dominio del inventario. Python puro: sin Qt, sin SQLite."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

CERO = Decimal("0")
TIPOS_MOVIMIENTO = ("entrada", "salida")


@dataclass(frozen=True)
class Categoria:
    nombre: str
    id: int | None = None


@dataclass(frozen=True)
class Impuesto:
    nombre: str
    tarifa: Decimal  # fracción: 0.19 = IVA 19%
    id: int | None = None
    codigo_dian: str | None = None  # reservado DIAN, sin uso fiscal hoy

    def __post_init__(self) -> None:
        if not (CERO <= self.tarifa <= Decimal("1")):
            raise ValueError("tarifa debe estar entre 0 y 1")


@dataclass(frozen=True)
class Producto:
    codigo_barras: str
    nombre: str
    precio: Decimal
    vendido_por_peso: bool = False
    unidad: str = "und"  # "und" o "kg"
    costo: Decimal = CERO
    categoria_id: int | None = None
    impuesto_id: int | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        if self.precio < CERO:
            raise ValueError("precio no puede ser negativo")
        if self.costo < CERO:
            raise ValueError("costo no puede ser negativo")


@dataclass(frozen=True)
class MovimientoInventario:
    producto_id: int
    tipo: str  # "entrada" o "salida"; el signo del stock lo da el tipo
    cantidad: Decimal  # siempre positiva
    fecha: datetime
    ref: str | None = None
    lote_id: int | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        if self.tipo not in TIPOS_MOVIMIENTO:
            raise ValueError(f"tipo inválido: {self.tipo!r}")
        if self.cantidad <= CERO:
            raise ValueError("cantidad debe ser positiva")
