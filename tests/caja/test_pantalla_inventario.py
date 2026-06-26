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
