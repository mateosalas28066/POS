from dataclasses import replace
from datetime import datetime
from decimal import Decimal

import pytest

from core.entidades import Devolucion, ItemDevolucion, LineaVenta, Pago, Venta
from core.servicio_venta import (
    ReembolsoDescuadrado, ServicioDevolucion, VentaNoDevolvible, VentaNoEncontrada,
)


def _venta(estado="pagada") -> Venta:
    lineas = (
        LineaVenta(producto_id=1, descripcion="Gaseosa", cantidad_o_peso=Decimal("2"),
                   precio_unit=Decimal("3500"), impuesto=Decimal("1118"),
                   subtotal=Decimal("7000"), venta_id=77, id=10),
    )
    return Venta(fecha=datetime(2026, 6, 25, 10, 0), lineas=lineas,
                 total=Decimal("7000"), total_impuestos=Decimal("1118"), estado=estado, id=77)


class _FakeVentas:
    def __init__(self, venta):
        self._venta = venta
        self.estado_marcado = None
    def por_id(self, id):
        return self._venta if self._venta and self._venta.id == id else None
    def marcar_estado(self, venta_id, estado):
        self.estado_marcado = (venta_id, estado)
        self._venta = replace(self._venta, estado=estado)


class _FakeDevoluciones:
    def __init__(self, ya_devuelto=None):
        self._ya = ya_devuelto or {}
        self.guardada = None
    def guardar(self, devolucion):
        self.guardada = replace(devolucion, id=5)
        return self.guardada
    def devuelto_por_linea(self, venta_id):
        return dict(self._ya)


class _FakeInventario:
    def __init__(self):
        self.movimientos = []
    def registrar(self, m):
        self.movimientos.append(m)
        return m


def test_devolucion_parcial_marca_parcial_y_repone():
    ventas, devs, inv = _FakeVentas(_venta()), _FakeDevoluciones(), _FakeInventario()
    dev = ServicioDevolucion(ventas, devs, inv).devolver(
        77, [ItemDevolucion(venta_linea_id=10, cantidad_o_peso=Decimal("1"))],
        [Pago(medio_pago_id=1, monto=Decimal("3500"))],
        fecha=datetime(2026, 6, 25, 11, 0), caja_sesion_id=1)
    assert dev.id == 5
    assert dev.total == Decimal("3500")
    assert ventas.estado_marcado == (77, "devuelta_parcial")
    assert [m.tipo for m in inv.movimientos] == ["entrada"]
    assert inv.movimientos[0].cantidad == Decimal("1")
    assert inv.movimientos[0].ref == "devolucion:5"


def test_devolucion_total_marca_devuelta():
    ventas, devs, inv = _FakeVentas(_venta()), _FakeDevoluciones(), _FakeInventario()
    ServicioDevolucion(ventas, devs, inv).devolver(
        77, [ItemDevolucion(venta_linea_id=10, cantidad_o_peso=Decimal("2"))],
        [Pago(medio_pago_id=1, monto=Decimal("7000"))],
        fecha=datetime(2026, 6, 25, 11, 0), caja_sesion_id=1)
    assert ventas.estado_marcado == (77, "devuelta")


def test_reembolso_descuadrado_falla_y_no_repone():
    ventas, devs, inv = _FakeVentas(_venta()), _FakeDevoluciones(), _FakeInventario()
    with pytest.raises(ReembolsoDescuadrado):
        ServicioDevolucion(ventas, devs, inv).devolver(
            77, [ItemDevolucion(venta_linea_id=10, cantidad_o_peso=Decimal("1"))],
            [Pago(medio_pago_id=1, monto=Decimal("3000"))],   # debería ser 3500
            fecha=datetime(2026, 6, 25, 11, 0))
    assert inv.movimientos == []
    assert ventas.estado_marcado is None


def test_devolver_venta_inexistente_falla():
    with pytest.raises(VentaNoEncontrada):
        ServicioDevolucion(_FakeVentas(None), _FakeDevoluciones(), _FakeInventario()).devolver(
            999, [], [], fecha=datetime(2026, 6, 25, 11, 0))


def test_devolver_venta_anulada_falla():
    ventas = _FakeVentas(_venta(estado="anulada"))
    with pytest.raises(VentaNoDevolvible):
        ServicioDevolucion(ventas, _FakeDevoluciones(), _FakeInventario()).devolver(
            77, [ItemDevolucion(venta_linea_id=10, cantidad_o_peso=Decimal("1"))],
            [Pago(medio_pago_id=1, monto=Decimal("3500"))],
            fecha=datetime(2026, 6, 25, 11, 0))


def test_devolver_venta_ya_devuelta_falla():
    ventas = _FakeVentas(_venta(estado="devuelta"))
    with pytest.raises(VentaNoDevolvible):
        ServicioDevolucion(ventas, _FakeDevoluciones(), _FakeInventario()).devolver(
            77, [ItemDevolucion(venta_linea_id=10, cantidad_o_peso=Decimal("1"))],
            [Pago(medio_pago_id=1, monto=Decimal("3500"))],
            fecha=datetime(2026, 6, 25, 11, 0))
