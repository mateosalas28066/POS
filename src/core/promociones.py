"""Reglas de dominio de promociones por producto. Python puro."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from decimal import Decimal

from core.entidades import Promocion

CERO = Decimal("0")


def promo_vigente(promo: Promocion, ahora: datetime) -> bool:
    """True si la promo aplica ahora: activa y dentro de su duración."""
    if not promo.activa:
        return False
    if promo.tipo_duracion == "tiempo":
        return promo.desde <= ahora <= promo.hasta
    if promo.tipo_duracion == "unidades":
        return (promo.unidades_restantes or CERO) > CERO
    return True  # manual


def precio_con_promo(precio_base: Decimal, promo: Promocion) -> Decimal:
    """Precio efectivo del producto bajo la promo (sin cuantizar; el subtotal cuantiza)."""
    if promo.tipo_valor == "precio_fijo":
        return promo.valor
    return precio_base * (Decimal("1") - promo.valor)


def consumir_unidades(promo: Promocion, cantidad: Decimal) -> Promocion:
    """Descuenta `cantidad` de las unidades restantes; desactiva la promo si llega a <= 0."""
    restantes = (promo.unidades_restantes or CERO) - cantidad
    return replace(promo, unidades_restantes=restantes, activa=restantes > CERO)
