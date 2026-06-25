"""Reglas de cálculo del dominio. Python puro."""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

CERO = Decimal("0")


def subtotal_por_peso(precio_por_kg: Decimal, peso_kg: Decimal) -> Decimal:
    """Subtotal de una línea vendida por peso, redondeado a pesos colombianos (enteros)."""
    if precio_por_kg < CERO or peso_kg < CERO:
        raise ValueError("precio y peso deben ser no negativos")
    return (precio_por_kg * peso_kg).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


_PESO = Decimal("1")  # cuantización a peso colombiano entero


def subtotal_por_unidad(precio_unit: Decimal, cantidad: Decimal) -> Decimal:
    """Subtotal de una línea por unidad, redondeado a pesos colombianos (enteros)."""
    if precio_unit < CERO or cantidad < CERO:
        raise ValueError("precio y cantidad deben ser no negativos")
    return (precio_unit * cantidad).quantize(_PESO, rounding=ROUND_HALF_UP)


def impuesto_incluido(subtotal: Decimal, tarifa: Decimal) -> Decimal:
    """IVA contenido en un subtotal que ya lo incluye: subtotal * tarifa / (1 + tarifa)."""
    if subtotal < CERO or tarifa < CERO:
        raise ValueError("subtotal y tarifa deben ser no negativos")
    return (subtotal * tarifa / (Decimal("1") + tarifa)).quantize(_PESO, rounding=ROUND_HALF_UP)


def calcular_vuelto(total: Decimal, recibido: Decimal) -> Decimal:
    """Vuelto a entregar. Lanza si el dinero recibido no cubre el total."""
    if recibido < total:
        raise ValueError("pago insuficiente")
    return recibido - total
