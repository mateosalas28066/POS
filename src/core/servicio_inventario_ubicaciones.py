"""Reglas puras de inventario multi-ubicación: stock por suma de confirmados y
composición de operaciones (traslado, conversión). Python puro, sin BD ni costeo."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

CERO = Decimal("0")


def stock_por_suma(movs: list[dict], ubicacion_id: int, producto_id: int) -> Decimal:
    """Σ entradas confirmadas a la ubicación − Σ salidas confirmadas desde la ubicación."""
    total = CERO
    for m in movs:
        if m["producto_id"] != producto_id or m["estado"] != "confirmado":
            continue
        if m.get("destino_id") == ubicacion_id:
            total += m["cantidad"]
        if m.get("origen_id") == ubicacion_id:
            total -= m["cantidad"]
    return total


def _mov(tipo: str, producto_id: int, cantidad: Decimal, *, origen_id, destino_id,
         estado: str, grupo: str, fecha: datetime) -> dict:
    return {"uuid": str(uuid4()), "tipo": tipo, "producto_id": producto_id,
            "cantidad": cantidad, "origen_id": origen_id, "destino_id": destino_id,
            "estado": estado, "grupo_uuid": grupo, "fecha": fecha}


def plan_traslado(producto_id: int, cantidad: Decimal, *, origen_id: int,
                  destino_id: int, fecha: datetime) -> list[dict]:
    """1 salida confirmada en origen + 1 entrada pendiente en destino (mismo grupo)."""
    grupo = str(uuid4())
    return [
        _mov("salida", producto_id, cantidad, origen_id=origen_id, destino_id=None,
             estado="confirmado", grupo=grupo, fecha=fecha),
        _mov("entrada", producto_id, cantidad, origen_id=None, destino_id=destino_id,
             estado="pendiente", grupo=grupo, fecha=fecha),
    ]


def plan_conversion(*, origen_id: int, salidas: list[tuple[int, Decimal]],
                    entradas: list[tuple[int, Decimal]], fecha: datetime) -> list[dict]:
    """1 salida por insumo + N entradas en la misma ubicación (merma permitida, sin costeo)."""
    grupo = str(uuid4())
    movs = []
    for pid, cant in salidas:
        movs.append(_mov("salida", pid, cant, origen_id=origen_id, destino_id=None,
                         estado="confirmado", grupo=grupo, fecha=fecha))
    for pid, cant in entradas:
        movs.append(_mov("entrada", pid, cant, origen_id=None, destino_id=origen_id,
                         estado="confirmado", grupo=grupo, fecha=fecha))
    return movs
