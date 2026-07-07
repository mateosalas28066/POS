"""Serializadores de eventos de catálogo del POS hacia el outbox (overlay/maestro/promo)."""
from decimal import Decimal

from core.entidades import Producto, Promocion
from sync_pdv.outbox import (
    serializar_overlay, serializar_producto_maestro, serializar_promo,
)

TS = "2026-07-07T11:00:00"


def test_serializar_overlay():
    ev = serializar_overlay("local-01", 1, Decimal("21000"), Decimal("12000"), True, TS)
    assert ev.tipo == "catalogo_overlay" and ev.local_id == "local-01"
    assert ev.payload["producto_id"] == 1
    assert ev.payload["precio"] == "21000" and ev.payload["costo"] == "12000"
    assert ev.payload["activo"] is True and ev.payload["actualizado_en"] == TS
    assert ev.uuid and ev.creado_en                      # con uuid y creado_en


def test_serializar_producto_maestro():
    p = Producto(codigo_barras="0001", nombre="Lomo", precio=Decimal("20000"),
                 vendido_por_peso=True, unidad="kg", costo=Decimal("12000"),
                 categoria_id=10, impuesto_id=5, id=1)
    ev = serializar_producto_maestro(p, "local-01", TS)
    assert ev.tipo == "catalogo_producto"
    assert ev.payload["id"] == 1 and ev.payload["nombre"] == "Lomo"
    assert ev.payload["vendido_por_peso"] is True and ev.payload["unidad"] == "kg"
    assert ev.payload["costo"] == "12000" and ev.payload["actualizado_en"] == TS


def test_serializar_promo():
    promo = Promocion(producto_id=1, tipo_valor="porcentaje", valor=Decimal("0.10"),
                      tipo_duracion="manual", id=7)
    ev = serializar_promo(promo, "local-01", TS)
    assert ev.tipo == "catalogo_promo"
    assert ev.payload["id"] == 7 and ev.payload["producto_id"] == 1
    assert ev.payload["tipo_valor"] == "porcentaje" and ev.payload["valor"] == "0.10"
    assert ev.payload["local_id"] == "local-01" and ev.payload["actualizado_en"] == TS
    assert ev.payload["unidades_limite"] is None       # None se preserva
