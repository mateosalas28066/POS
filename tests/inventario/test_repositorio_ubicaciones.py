"""La migración 013 crea ubicaciones/movimientos_ubicacion; RepositorioMovimientosUbicacionSQLite
implementa el puerto (stock, registrar, confirmar) + extras de sync (aplicar_delta, cursor, pendientes)."""
from datetime import datetime
from decimal import Decimal

from inventario.db import aplicar_migraciones, conectar
from inventario.repositorio_ubicaciones_sqlite import RepositorioMovimientosUbicacionSQLite

F = datetime(2026, 7, 7, 12, 0, 0)


def _repo():
    conn = conectar(":memory:")
    aplicar_migraciones(conn)
    return RepositorioMovimientosUbicacionSQLite(conn)


def test_tablas_existen():
    conn = conectar(":memory:")
    aplicar_migraciones(conn)
    tablas = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"ubicaciones", "movimientos_ubicacion"} <= tablas


def test_registrar_entrada_y_stock():
    repo = _repo()
    repo.registrar({"uuid": "u1", "tipo": "entrada", "producto_id": 1,
                     "cantidad": Decimal("200"), "origen_id": None, "destino_id": 5,
                     "estado": "confirmado", "grupo_uuid": None, "fecha": F})
    assert repo.stock(5, 1) == Decimal("200")


def test_traslado_pendiente_no_cuenta_hasta_confirmar():
    repo = _repo()
    grupo = "g1"
    repo.registrar({"uuid": "s1", "tipo": "salida", "producto_id": 1, "cantidad": Decimal("50"),
                     "origen_id": 5, "destino_id": None, "estado": "confirmado",
                     "grupo_uuid": grupo, "fecha": F})
    repo.registrar({"uuid": "e1", "tipo": "entrada", "producto_id": 1, "cantidad": Decimal("50"),
                     "origen_id": None, "destino_id": 8, "estado": "pendiente",
                     "grupo_uuid": grupo, "fecha": F})
    assert repo.stock(8, 1) == Decimal("0")   # pendiente no cuenta
    repo.confirmar("e1")
    assert repo.stock(8, 1) == Decimal("50")


def test_movimientos_grupo():
    repo = _repo()
    repo.registrar({"uuid": "s2", "tipo": "salida", "producto_id": 1, "cantidad": Decimal("10"),
                     "origen_id": 5, "destino_id": None, "estado": "confirmado",
                     "grupo_uuid": "g2", "fecha": F})
    repo.registrar({"uuid": "e2", "tipo": "entrada", "producto_id": 1, "cantidad": Decimal("10"),
                     "origen_id": None, "destino_id": 8, "estado": "pendiente",
                     "grupo_uuid": "g2", "fecha": F})
    movs = repo.movimientos_grupo("g2")
    assert {m["uuid"] for m in movs} == {"s2", "e2"}


def test_pendientes_lista_entradas_pendientes_del_destino():
    repo = _repo()
    repo.registrar({"uuid": "e3", "tipo": "entrada", "producto_id": 2, "cantidad": Decimal("5"),
                     "origen_id": None, "destino_id": 9, "estado": "pendiente",
                     "grupo_uuid": "g3", "fecha": F})
    pend = repo.pendientes(9)
    assert len(pend) == 1 and pend[0]["uuid"] == "e3"


def test_aplicar_delta_inserta_nuevo_y_hace_flip_sin_reescribir_cantidad():
    repo = _repo()
    # simula el delta bajado de la nube: primero llega pendiente, luego el flip confirmado
    repo.aplicar_delta([{"uuid": "d1", "tipo": "entrada", "producto_id": 3,
                          "cantidad": "77", "origen_id": None, "destino_id": 9,
                          "estado": "pendiente", "grupo_uuid": "g4", "lote_id": None,
                          "ref": None, "fecha": "2026-07-07T12:00:00",
                          "actualizado_en": "2026-07-07T12:00:00"}])
    assert repo.stock(9, 3) == Decimal("0")
    repo.aplicar_delta([{"uuid": "d1", "tipo": "entrada", "producto_id": 3,
                          "cantidad": "999", "origen_id": None, "destino_id": 9,
                          "estado": "confirmado", "grupo_uuid": "g4", "lote_id": None,
                          "ref": None, "fecha": "2026-07-07T12:00:00",
                          "actualizado_en": "2026-07-07T12:05:00"}])
    assert repo.stock(9, 3) == Decimal("77")   # nunca reescribe cantidad (999 se ignora)


def test_cursor_guardar_y_leer():
    repo = _repo()
    assert repo.cursor(9) is None
    repo.guardar_cursor(9, "2026-07-07T12:05:00")
    assert repo.cursor(9) == "2026-07-07T12:05:00"
