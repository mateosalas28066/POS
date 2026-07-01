import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from decimal import Decimal  # noqa: E402

from PySide6.QtWidgets import QApplication  # noqa: E402

from core.entidades import Producto  # noqa: E402
from core.servicio_promociones import ServicioPromociones  # noqa: E402
from caja.dialogos.dialogo_promociones import DialogoPromociones  # noqa: E402

PRODS = [Producto(codigo_barras="1", nombre="Lomo", precio=Decimal("20000"),
                  vendido_por_peso=True, unidad="kg", id=1)]


class FakePromos:
    def __init__(self):
        self.items = {}
        self._n = 1

    def guardar(self, promo):
        from dataclasses import replace
        g = replace(promo, id=self._n); self.items[self._n] = g; self._n += 1
        return g

    def actualizar(self, promo):
        self.items[promo.id] = promo

    def por_id(self, id):
        return self.items.get(id)

    def activa_por_producto(self, producto_id):
        return next((p for p in self.items.values()
                     if p.producto_id == producto_id and p.activa), None)

    def listar(self):
        return list(self.items.values())


def _dialogo():
    _app = QApplication.instance() or QApplication([])
    return DialogoPromociones(PRODS, ServicioPromociones(FakePromos()))


def test_construye_promo_precio_fijo():
    d = _dialogo()
    d._producto.setCurrentIndex(0)
    d._tipo_valor.setCurrentText("precio_fijo")
    d._valor.setValue(15000)
    d._tipo_duracion.setCurrentText("manual")
    p = d.promocion()
    assert p.producto_id == 1
    assert p.tipo_valor == "precio_fijo"
    assert p.valor == Decimal("15000")
    assert p.tipo_duracion == "manual"


def test_construye_promo_porcentaje_convierte_a_fraccion():
    d = _dialogo()
    d._producto.setCurrentIndex(0)
    d._tipo_valor.setCurrentText("porcentaje")
    d._valor.setValue(20)
    d._tipo_duracion.setCurrentText("manual")
    p = d.promocion()
    assert p.tipo_valor == "porcentaje"
    assert p.valor == Decimal("0.2")


def test_crear_persiste_via_servicio():
    d = _dialogo()
    d._producto.setCurrentIndex(0)
    d._tipo_valor.setCurrentText("precio_fijo")
    d._valor.setValue(15000)
    d._tipo_duracion.setCurrentText("unidades")
    d._unidades.setValue(50)
    d._crear()
    assert len(d._svc.listar()) == 1
    assert d._svc.listar()[0].unidades_limite == Decimal("50")
