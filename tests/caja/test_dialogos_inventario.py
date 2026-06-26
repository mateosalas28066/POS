import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from decimal import Decimal  # noqa: E402

from PySide6.QtWidgets import QApplication  # noqa: E402

from core.entidades import Categoria, Impuesto, Producto  # noqa: E402
from caja.dialogos.dialogo_producto import DialogoProducto  # noqa: E402
from caja.dialogos.dialogo_movimiento import DialogoMovimiento  # noqa: E402

CATS = [Categoria(nombre="Carnes", id=1), Categoria(nombre="Frutas", id=2)]
IMPS = [Impuesto(nombre="IVA 0%", tarifa=Decimal("0"), id=1)]


def test_dialogo_producto_construye_nuevo():
    _app = QApplication.instance() or QApplication([])
    d = DialogoProducto(CATS, IMPS)
    d._codigo.setText("999")
    d._nombre.setText("Lomo")
    d._precio.setValue(25000)
    p = d.producto()
    assert p.codigo_barras == "999"
    assert p.nombre == "Lomo"
    assert p.precio == Decimal("25000")
    assert p.id is None


def test_dialogo_producto_conserva_id_en_edicion():
    _app = QApplication.instance() or QApplication([])
    existente = Producto(codigo_barras="1", nombre="X", precio=Decimal("100"),
                         categoria_id=1, impuesto_id=1, id=7)
    d = DialogoProducto(CATS, IMPS, producto=existente)
    d._nombre.setText("X editado")
    p = d.producto()
    assert p.id == 7
    assert p.nombre == "X editado"


def test_dialogo_movimiento_construye():
    _app = QApplication.instance() or QApplication([])
    d = DialogoMovimiento(producto_id=3)
    d._tipo.setCurrentText("entrada")
    d._cantidad.setValue(10)
    m = d.movimiento()
    assert m.producto_id == 3
    assert m.tipo == "entrada"
    assert m.cantidad == Decimal("10")
