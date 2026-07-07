"""Con LOCAL_ID/ALMACEN_ID, ContextoApp expone repo_movimientos_ubicacion y encola
eventos de movimiento (traslado/confirmación) al outbox."""
from datetime import datetime
from decimal import Decimal

from inventario.repositorio_ubicaciones_sqlite import RepositorioMovimientosUbicacionSQLite


def test_repo_movimientos_ubicacion_presente_con_sync(monkeypatch):
    monkeypatch.setenv("LOCAL_ID", "local-01")
    monkeypatch.setenv("ALMACEN_ID", "1")
    monkeypatch.delenv("SYNC_URL", raising=False)
    from caja.contexto import ContextoApp

    ctx = ContextoApp.crear(":memory:")
    try:
        assert isinstance(ctx.repo_movimientos_ubicacion, RepositorioMovimientosUbicacionSQLite)
        assert ctx.almacen_id == "1"
    finally:
        ctx.conn.close()


def test_repo_movimientos_ubicacion_ausente_sin_sync(monkeypatch):
    monkeypatch.delenv("LOCAL_ID", raising=False)
    monkeypatch.delenv("ALMACEN_ID", raising=False)
    from caja.contexto import ContextoApp

    ctx = ContextoApp.crear(":memory:")
    try:
        assert ctx.repo_movimientos_ubicacion is None
    finally:
        ctx.conn.close()


def test_encolar_movimiento_pone_evento_cuando_hay_sync(monkeypatch):
    monkeypatch.setenv("LOCAL_ID", "local-01")
    monkeypatch.setenv("ALMACEN_ID", "1")
    monkeypatch.delenv("SYNC_URL", raising=False)
    from caja.contexto import ContextoApp

    ctx = ContextoApp.crear(":memory:")
    try:
        mov = {"uuid": "m1", "tipo": "salida", "producto_id": 1, "cantidad": Decimal("5"),
               "origen_id": 1, "destino_id": None, "estado": "confirmado", "grupo_uuid": "g1",
               "fecha": datetime(2026, 7, 7, 12, 0, 0)}
        ctx.encolar_movimiento(mov)
        eventos = [e for e in ctx.repo_outbox.pendientes() if e.tipo == "movimiento_inventario"]
        assert len(eventos) == 1
        assert eventos[0].payload["uuid"] == "m1"
        assert eventos[0].payload["almacen_id"] == 1
    finally:
        ctx.conn.close()


def test_encolar_movimiento_es_noop_sin_sync(monkeypatch):
    monkeypatch.delenv("LOCAL_ID", raising=False)
    monkeypatch.delenv("ALMACEN_ID", raising=False)
    from caja.contexto import ContextoApp

    ctx = ContextoApp.crear(":memory:")
    try:
        assert ctx.repo_outbox is None
        ctx.encolar_movimiento({"uuid": "m1", "tipo": "salida", "producto_id": 1,
                                 "cantidad": Decimal("5"), "origen_id": 1, "destino_id": None,
                                 "estado": "confirmado", "grupo_uuid": None,
                                 "fecha": datetime(2026, 7, 7, 12, 0, 0)})   # no debe romper
    finally:
        ctx.conn.close()
