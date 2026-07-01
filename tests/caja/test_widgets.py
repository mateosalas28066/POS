import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from decimal import Decimal  # noqa: E402

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from core.entidades import Producto  # noqa: E402
from caja.widgets import SpinMoneda, TarjetaProducto, TarjetaKpi, BotonRail  # noqa: E402
from caja.tema import icono  # noqa: E402


def test_tarjeta_producto_emite_seleccionado():
    _app = QApplication.instance() or QApplication([])
    p = Producto(codigo_barras="B1", nombre="Manzana", precio=Decimal("6500"), id=1)
    tarjeta = TarjetaProducto(p, "Frutas")
    recibido = []
    tarjeta.seleccionado.connect(lambda prod: recibido.append(prod))
    tarjeta._emitir()  # simula click
    assert recibido and recibido[0].id == 1


def test_tarjeta_kpi_set_valor_y_estado():
    _app = QApplication.instance() or QApplication([])
    kpi = TarjetaKpi("Diferencia", "0")
    kpi.set_valor("$ 1.000")
    assert kpi._valor.text() == "$ 1.000"
    kpi.set_estado("alerta")
    assert kpi._valor.objectName() == "alerta"


def test_boton_rail_es_checkable():
    _app = QApplication.instance() or QApplication([])
    b = BotonRail(icono("venta"), "Venta")
    assert b.isCheckable()
    assert b.toolTip() == "Venta"


def test_tarjeta_producto_tamano_fijo():
    _app = QApplication.instance() or QApplication([])
    p = Producto(codigo_barras="B1", nombre="Manzana", precio=Decimal("6500"), id=1)
    tarjeta = TarjetaProducto(p)
    assert tarjeta.minimumSize() == tarjeta.maximumSize()


def test_tarjeta_producto_agotada_no_emite_ni_es_clickeable():
    _app = QApplication.instance() or QApplication([])
    p = Producto(codigo_barras="B1", nombre="Manzana", precio=Decimal("6500"), id=1)
    tarjeta = TarjetaProducto(p, agotado=True)
    recibido = []
    tarjeta.seleccionado.connect(lambda prod: recibido.append(prod))
    tarjeta._emitir()
    assert recibido == []
    assert tarjeta.property("agotado") is True


def test_tarjeta_producto_en_promo_marca_propiedad():
    _app = QApplication.instance() or QApplication([])
    p = Producto(codigo_barras="B1", nombre="Manzana", precio=Decimal("6500"), id=1)
    tarjeta = TarjetaProducto(p, en_promo=True)
    assert tarjeta.property("promo") is True


def test_spin_moneda_click_para_enfocar_selecciona_el_0():
    """El clic real (no solo setFocus) no debe deshacer el selectAll()."""
    app = QApplication.instance() or QApplication([])
    spin = SpinMoneda()
    spin.setValue(0)
    spin.show()
    app.processEvents()

    QTest.mouseClick(spin, Qt.LeftButton)
    app.processEvents()  # deja correr el QTimer.singleShot(0, selectAll)

    assert spin.lineEdit().hasSelectedText()
    QTest.keyClick(spin, Qt.Key_5)
    assert spin.value() == 5
