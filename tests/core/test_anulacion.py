from datetime import datetime
from decimal import Decimal
import pytest
from dataclasses import replace
from core.entidades import LineaVenta, Venta, MovimientoInventario
from core.servicio_venta import entradas_de_anulacion, ServicioAnulacion, VentaNoEncontrada, VentaYaAnulada


def _venta(id=77) -> Venta:
    lineas = (
        LineaVenta(producto_id=1, descripcion="Gaseosa", cantidad_o_peso=Decimal("2"),
                   precio_unit=Decimal("3500"), impuesto=Decimal("1118"), subtotal=Decimal("7000")),
        LineaVenta(producto_id=2, descripcion="Manzana", cantidad_o_peso=Decimal("1.5"),
                   precio_unit=Decimal("4000"), impuesto=Decimal("0"), subtotal=Decimal("6000")),
    )
    return Venta(fecha=datetime(2026, 6, 25, 10, 0), lineas=lineas,
                 total=Decimal("13000"), total_impuestos=Decimal("1118"), id=id)


def test_entradas_de_anulacion_una_por_linea():
    entradas = entradas_de_anulacion(_venta(id=77))
    assert len(entradas) == 2
    assert all(m.tipo == "entrada" for m in entradas)
    assert entradas[0].producto_id == 1
    assert entradas[0].cantidad == Decimal("2")
    assert entradas[1].cantidad == Decimal("1.5")
    assert all(m.ref == "anulacion:77" for m in entradas)


class _FakeVentas:
    def __init__(self, venta):
        self._venta = venta
        self.anulada_id = None
    def por_id(self, id):
        return self._venta if self._venta and self._venta.id == id else None
    def anular(self, venta_id):
        self.anulada_id = venta_id
        self._venta = replace(self._venta, estado="anulada")


class _FakeInventario:
    def __init__(self):
        self.movimientos = []
    def registrar(self, m):
        self.movimientos.append(m)
        return m


def test_anular_marca_estado_y_repone_inventario():
    ventas = _FakeVentas(_venta(id=77))
    inventario = _FakeInventario()
    anulada = ServicioAnulacion(ventas, inventario).anular(77)
    assert anulada.estado == "anulada"
    assert ventas.anulada_id == 77
    assert [m.tipo for m in inventario.movimientos] == ["entrada", "entrada"]
    assert [m.cantidad for m in inventario.movimientos] == [Decimal("2"), Decimal("1.5")]
    assert all(m.ref == "anulacion:77" for m in inventario.movimientos)


def test_anular_venta_inexistente_falla():
    ventas = _FakeVentas(None)
    with pytest.raises(VentaNoEncontrada):
        ServicioAnulacion(ventas, _FakeInventario()).anular(999)


def test_anular_venta_ya_anulada_falla_y_no_repone():
    ventas = _FakeVentas(replace(_venta(id=77), estado="anulada"))
    inventario = _FakeInventario()
    with pytest.raises(VentaYaAnulada):
        ServicioAnulacion(ventas, inventario).anular(77)
    assert inventario.movimientos == []
