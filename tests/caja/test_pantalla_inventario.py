import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from decimal import Decimal  # noqa: E402

from PySide6.QtWidgets import QApplication  # noqa: E402

from core.entidades import MovimientoInventario, Producto  # noqa: E402
from caja.contexto import ContextoApp  # noqa: E402
from caja.pantalla_inventario import PantallaInventario  # noqa: E402


def test_lista_productos_con_stock():
    _app = QApplication.instance() or QApplication([])
    ctx = ContextoApp.crear(":memory:")
    win = PantallaInventario(ctx)
    win.al_mostrar()
    assert win._tabla.rowCount() >= 4
    # columna stock (índice 5) muestra número
    assert win._tabla.item(0, 5) is not None


def test_guardar_producto_nuevo_agrega_fila():
    _app = QApplication.instance() or QApplication([])
    ctx = ContextoApp.crear(":memory:")
    win = PantallaInventario(ctx)
    win.al_mostrar()
    antes = win._tabla.rowCount()
    nuevo = Producto(codigo_barras="555", nombre="Cerdo", precio=Decimal("19000"),
                     categoria_id=1, impuesto_id=1, unidad="kg", vendido_por_peso=True)
    win._guardar_producto(nuevo)
    win.al_mostrar()
    assert win._tabla.rowCount() == antes + 1


def test_aplicar_movimiento_cambia_stock():
    _app = QApplication.instance() or QApplication([])
    ctx = ContextoApp.crear(":memory:")
    win = PantallaInventario(ctx)
    win.al_mostrar()
    prod = ctx.repo_productos.listar()[0]
    stock_antes = ctx.repo_inventario.stock_de(prod.id)
    win._aplicar_movimiento(MovimientoInventario(
        producto_id=prod.id, tipo="entrada", cantidad=Decimal("5"),
        fecha=__import__("datetime").datetime.now()))
    assert ctx.repo_inventario.stock_de(prod.id) == stock_antes + Decimal("5")


def test_botones_multiubicacion_ocultos_sin_sync():
    _app = QApplication.instance() or QApplication([])
    ctx = ContextoApp.crear(":memory:")
    win = PantallaInventario(ctx)
    assert win._boton_traslado.isVisible() is False
    assert win._boton_pendientes.isVisible() is False


def test_aplicar_traslado_registra_salida_confirmada_y_entrada_pendiente(monkeypatch):
    monkeypatch.setenv("LOCAL_ID", "local-01")
    monkeypatch.setenv("ALMACEN_ID", "1")
    monkeypatch.delenv("SYNC_URL", raising=False)
    ctx = ContextoApp.crear(":memory:")
    _app = QApplication.instance() or QApplication([])
    win = PantallaInventario(ctx)
    prod = ctx.repo_productos.listar()[0]

    win._aplicar_traslado(prod.id, Decimal("10"), 8, "ref-demo")

    assert ctx.repo_movimientos_ubicacion.stock(8, prod.id) == Decimal("0")   # pendiente
    eventos = [e for e in ctx.repo_outbox.pendientes() if e.tipo == "movimiento_inventario"]
    assert len(eventos) == 2
    tipos = {e.payload["tipo"] for e in eventos}
    assert tipos == {"salida", "entrada"}


def test_confirmar_pendiente_desde_bandeja_flip_y_encola(monkeypatch):
    monkeypatch.setenv("LOCAL_ID", "local-02")
    monkeypatch.setenv("ALMACEN_ID", "8")
    monkeypatch.delenv("SYNC_URL", raising=False)
    ctx = ContextoApp.crear(":memory:")
    _app = QApplication.instance() or QApplication([])
    prod_id = ctx.repo_productos.listar()[0].id
    ctx.repo_movimientos_ubicacion.registrar({
        "uuid": "e-pend", "tipo": "entrada", "producto_id": prod_id, "cantidad": Decimal("10"),
        "origen_id": 1, "destino_id": 8, "estado": "pendiente", "grupo_uuid": "g1",
        "fecha": __import__("datetime").datetime.now()})

    from caja.dialogos.dialogo_bandeja_pendientes import DialogoBandejaPendientes
    dlg = DialogoBandejaPendientes(ctx)
    assert dlg._tabla.rowCount() == 1
    dlg._tabla.selectRow(0)
    dlg._confirmar_seleccionado()

    assert ctx.repo_movimientos_ubicacion.stock(8, prod_id) == Decimal("10")
    assert dlg._tabla.rowCount() == 0   # ya no está pendiente
    eventos = [e for e in ctx.repo_outbox.pendientes() if e.tipo == "movimiento_inventario"]
    assert len(eventos) == 1 and eventos[0].payload["estado"] == "confirmado"


def test_bandeja_muestra_traslado_entrante_cuando_origen_none(monkeypatch):
    # Entrada pendiente tal como llega del sync cross-local: origen_id=None (la salida
    # vive en el origen y no se sincroniza al destino). La columna "Desde" no debe decir "None".
    monkeypatch.setenv("LOCAL_ID", "local-02")
    monkeypatch.setenv("ALMACEN_ID", "8")
    monkeypatch.delenv("SYNC_URL", raising=False)
    ctx = ContextoApp.crear(":memory:")
    _app = QApplication.instance() or QApplication([])
    prod_id = ctx.repo_productos.listar()[0].id
    ctx.repo_movimientos_ubicacion.registrar({
        "uuid": "e-x", "tipo": "entrada", "producto_id": prod_id, "cantidad": Decimal("10"),
        "origen_id": None, "destino_id": 8, "estado": "pendiente", "grupo_uuid": "g9",
        "fecha": __import__("datetime").datetime.now()})

    from caja.dialogos.dialogo_bandeja_pendientes import DialogoBandejaPendientes
    dlg = DialogoBandejaPendientes(ctx)
    assert dlg._tabla.rowCount() == 1
    assert dlg._tabla.item(0, 2).text() == "Traslado entrante"


def test_bandeja_muestra_nombre_del_origen_enriquecido(monkeypatch):
    # el delta de la nube trae origen_nombre (resuelto por el grupo); la bandeja lo muestra
    monkeypatch.setenv("LOCAL_ID", "local-02")
    monkeypatch.setenv("ALMACEN_ID", "8")
    monkeypatch.delenv("SYNC_URL", raising=False)
    ctx = ContextoApp.crear(":memory:")
    _app = QApplication.instance() or QApplication([])
    prod_id = ctx.repo_productos.listar()[0].id
    ctx.repo_movimientos_ubicacion.aplicar_delta([{
        "uuid": "e-y", "tipo": "entrada", "producto_id": prod_id, "cantidad": "10",
        "origen_id": None, "destino_id": 8, "estado": "pendiente", "grupo_uuid": "g2",
        "origen_nombre": "Bodega Central",
        "fecha": "2026-07-07T10:00:00+00:00", "actualizado_en": "2026-07-07T10:00:00+00:00"}])

    from caja.dialogos.dialogo_bandeja_pendientes import DialogoBandejaPendientes
    dlg = DialogoBandejaPendientes(ctx)
    assert dlg._tabla.rowCount() == 1
    assert dlg._tabla.item(0, 2).text() == "Bodega Central"
