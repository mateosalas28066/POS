"""Con LOCAL_ID/ALMACEN_ID, la venta del ContextoApp lee el precio de la réplica RO."""
from decimal import Decimal

from sync_pdv.replica import RepositorioReplicaSQLite


def _snap_ampolleta(precio: str):
    return {"productos": [{
        "producto_id": 1, "codigo_barras": "00190", "nombre": "Ampolleta", "unidad": "kg",
        "vendido_por_peso": True, "categoria_id": None, "categoria_nombre": None,
        "impuesto_id": None, "tarifa_impuesto": None, "precio": precio, "costo": "0",
        "actualizado_en": "2026-07-07T10:00:00"}], "promociones": []}


def test_venta_usa_precio_de_replica_cuando_hay_local_id(monkeypatch):
    monkeypatch.setenv("LOCAL_ID", "local-01")
    monkeypatch.setenv("ALMACEN_ID", "1")
    monkeypatch.delenv("SYNC_URL", raising=False)
    from caja.contexto import ContextoApp

    ctx = ContextoApp.crear(":memory:")           # seed demo: Ampolleta 00190 = 30000 local, id=1
    try:
        RepositorioReplicaSQLite(ctx.conn).aplicar_catalogo(_snap_ampolleta("99000"))
        linea = ctx.nueva_venta().agregar("00190", peso_kg=Decimal("2"))
        assert linea.precio_unit == Decimal("99000")   # el de la réplica, no el local (30000)
    finally:
        ctx.conn.close()


def test_venta_cae_al_precio_local_si_replica_vacia(monkeypatch):
    monkeypatch.setenv("LOCAL_ID", "local-01")
    monkeypatch.setenv("ALMACEN_ID", "1")
    monkeypatch.delenv("SYNC_URL", raising=False)
    from caja.contexto import ContextoApp

    ctx = ContextoApp.crear(":memory:")           # réplica vacía (sin sync aún)
    try:
        linea = ctx.nueva_venta().agregar("00190", peso_kg=Decimal("1"))
        assert linea.precio_unit == Decimal("30000")   # offline-first: precio local
    finally:
        ctx.conn.close()


def test_encolar_overlay_pone_evento_cuando_hay_sync(monkeypatch):
    monkeypatch.setenv("LOCAL_ID", "local-01")
    monkeypatch.setenv("ALMACEN_ID", "1")
    monkeypatch.delenv("SYNC_URL", raising=False)
    from caja.contexto import ContextoApp

    ctx = ContextoApp.crear(":memory:")
    try:
        prod = ctx.repo_productos.listar()[0]
        ctx.encolar_overlay(prod)
        overlays = [e for e in ctx.repo_outbox.pendientes() if e.tipo == "catalogo_overlay"]
        assert len(overlays) == 1
        assert overlays[0].payload["producto_id"] == prod.id
        assert overlays[0].payload["precio"] == str(prod.precio)
    finally:
        ctx.conn.close()


def test_encolar_overlay_es_noop_sin_sync(monkeypatch):
    monkeypatch.delenv("LOCAL_ID", raising=False)
    monkeypatch.delenv("ALMACEN_ID", raising=False)
    from caja.contexto import ContextoApp

    ctx = ContextoApp.crear(":memory:")
    try:
        assert ctx.repo_outbox is None
        ctx.encolar_overlay(ctx.repo_productos.listar()[0])   # no debe romper
    finally:
        ctx.conn.close()
