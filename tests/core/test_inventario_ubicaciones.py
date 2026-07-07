"""Reglas puras de inventario multi-ubicación: stock por suma de confirmados +
composición de operaciones (traslado, conversión). Python puro, sin BD."""
from datetime import datetime
from decimal import Decimal

from core.servicio_inventario_ubicaciones import (
    plan_conversion, plan_traslado, stock_por_suma)

F = datetime(2026, 7, 7, 12, 0, 0)


def test_stock_suma_confirmados():
    movs = [
        {"tipo": "entrada", "producto_id": 1, "cantidad": Decimal("200"),
         "destino_id": 5, "origen_id": None, "estado": "confirmado"},
        {"tipo": "salida", "producto_id": 1, "cantidad": Decimal("30"),
         "origen_id": 5, "destino_id": None, "estado": "confirmado"},
        {"tipo": "entrada", "producto_id": 1, "cantidad": Decimal("10"),
         "destino_id": 5, "origen_id": None, "estado": "pendiente"},  # no cuenta
    ]
    assert stock_por_suma(movs, 5, 1) == Decimal("170")


def test_stock_ignora_otro_producto_y_otra_ubicacion():
    movs = [
        {"tipo": "entrada", "producto_id": 2, "cantidad": Decimal("99"),
         "destino_id": 5, "origen_id": None, "estado": "confirmado"},   # otro producto
        {"tipo": "entrada", "producto_id": 1, "cantidad": Decimal("99"),
         "destino_id": 8, "origen_id": None, "estado": "confirmado"},   # otra ubicación
    ]
    assert stock_por_suma(movs, 5, 1) == Decimal("0")


def test_plan_traslado_pendiente_en_destino():
    movs = plan_traslado(1, Decimal("50"), origen_id=5, destino_id=8, fecha=F)
    salida = next(m for m in movs if m["tipo"] == "salida")
    entrada = next(m for m in movs if m["tipo"] == "entrada")
    assert salida["origen_id"] == 5 and salida["destino_id"] is None
    assert salida["estado"] == "confirmado"
    assert entrada["destino_id"] == 8 and entrada["origen_id"] is None
    assert entrada["estado"] == "pendiente"
    assert salida["grupo_uuid"] == entrada["grupo_uuid"]
    assert salida["uuid"] != entrada["uuid"]


def test_plan_conversion_solo_cantidades():
    movs = plan_conversion(
        origen_id=5,
        salidas=[(1, Decimal("200"))],
        entradas=[(2, Decimal("120")), (3, Decimal("60"))],  # merma 20, permitida
        fecha=F)
    assert sum(1 for m in movs if m["tipo"] == "salida") == 1
    assert sum(1 for m in movs if m["tipo"] == "entrada") == 2
    assert all(m["origen_id"] == 5 or m["destino_id"] == 5 for m in movs)
    assert all(m["estado"] == "confirmado" for m in movs)
    assert len({m["grupo_uuid"] for m in movs}) == 1
