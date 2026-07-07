"""serializar_movimiento empaqueta un movimiento de inventario multi-ubicación
(salida de plan_traslado/plan_conversion, o el flip de confirmación) para el outbox."""
from datetime import datetime
from decimal import Decimal

from sync_pdv.outbox import serializar_movimiento

F = datetime(2026, 7, 7, 12, 0, 0)


def test_serializar_movimiento_produce_tipo_y_payload():
    mov = {"uuid": "m1", "tipo": "traslado", "producto_id": 1, "cantidad": Decimal("50"),
           "origen_id": 5, "destino_id": 8, "estado": "pendiente", "grupo_uuid": "g1",
           "fecha": F}
    ev = serializar_movimiento(mov, almacen_id=5, local_id="local-01")
    assert ev.tipo == "movimiento_inventario"
    assert ev.local_id == "local-01"
    p = ev.payload
    assert p["uuid"] == "m1"
    assert p["cantidad"] == "50"
    assert p["origen_id"] == 5 and p["destino_id"] == 8
    assert p["estado"] == "pendiente" and p["grupo_uuid"] == "g1"
    assert p["almacen_id"] == 5 and p["local_id"] == "local-01"
    assert p["fecha"] == "2026-07-07T12:00:00"
    assert p["actualizado_en"]   # siempre presente, aunque el mov no lo traiga


def test_serializar_movimiento_respeta_actualizado_en_explicito():
    mov = {"uuid": "m2", "tipo": "entrada", "producto_id": 1, "cantidad": Decimal("1"),
           "origen_id": None, "destino_id": 9, "estado": "confirmado", "grupo_uuid": None,
           "fecha": F, "actualizado_en": "2026-07-07T12:05:00"}
    ev = serializar_movimiento(mov, almacen_id=9, local_id="local-02")
    assert ev.payload["actualizado_en"] == "2026-07-07T12:05:00"
