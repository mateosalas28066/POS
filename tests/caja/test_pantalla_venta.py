# tests/caja/test_pantalla_venta.py
import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from decimal import Decimal  # noqa: E402

from PySide6.QtWidgets import QApplication  # noqa: E402

from core.entidades import Impuesto, Producto  # noqa: E402
from core.servicio_venta import ServicioVenta  # noqa: E402
from caja.pantalla_venta import PantallaVenta  # noqa: E402


class _FakeProductos:
    def por_codigo(self, codigo_barras: str):
        return Producto(codigo_barras="B", nombre="Gaseosa", precio=Decimal("3500"),
                        impuesto_id=10, id=1)


class _FakeImpuestos:
    def por_id(self, id: int):
        return Impuesto(nombre="IVA", tarifa=Decimal("0.19"), id=10)


def test_pantalla_agrega_linea_y_actualiza_total():
    _app = QApplication.instance() or QApplication([])
    win = PantallaVenta(ServicioVenta(_FakeProductos(), _FakeImpuestos()))
    win._codigo.setText("B")
    win._al_agregar()
    assert win._tabla.rowCount() == 1
    assert "3500" in win._total.text()
