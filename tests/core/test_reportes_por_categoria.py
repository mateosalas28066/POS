"""Reporte de ventas por categoría (Res, Pollo, Cerdo, Fruver, ...)."""
from datetime import datetime
from decimal import Decimal

import pytest

from core.entidades import Devolucion, LineaDevolucion, LineaVenta, Producto, Venta
from core.servicio_reportes import ServicioReportes

DESDE = datetime(2026, 7, 1, 0, 0)
HASTA = datetime(2026, 7, 2, 0, 0)


def _linea(producto_id, subtotal, impuesto=Decimal("0")):
    return LineaVenta(producto_id=producto_id, descripcion=f"P{producto_id}",
                      cantidad_o_peso=Decimal("1"), precio_unit=subtotal,
                      impuesto=impuesto, subtotal=subtotal)


def _venta(id, lineas):
    total = sum((ln.subtotal for ln in lineas), Decimal("0"))
    imp = sum((ln.impuesto for ln in lineas), Decimal("0"))
    return Venta(fecha=datetime(2026, 7, 1, 10, 0), lineas=tuple(lineas),
                 total=total, total_impuestos=imp, id=id)


class _FakeVentas:
    def __init__(self, ventas):
        self._ventas = ventas

    def ventas_en(self, desde, hasta):
        return list(self._ventas)


class _FakeDevoluciones:
    def __init__(self, devs=()):
        self._devs = list(devs)

    def devoluciones_en(self, desde, hasta):
        return list(self._devs)


class _FakeProductos:
    def __init__(self, productos):
        self._productos = productos

    def listar(self):
        return list(self._productos)


def _svc(ventas, devs=(), productos=()):
    return ServicioReportes(_FakeVentas(ventas), _FakeDevoluciones(devs),
                            None, None, productos=_FakeProductos(productos))


PRODUCTOS = [
    Producto(codigo_barras="1", nombre="Lomo", precio=Decimal("100"), categoria_id=1, id=1),
    Producto(codigo_barras="2", nombre="Pechuga", precio=Decimal("100"), categoria_id=2, id=2),
    Producto(codigo_barras="3", nombre="Bolsa", precio=Decimal("100"), id=3),  # sin categoría
]


def test_agrupa_lineas_por_categoria():
    ventas = [
        _venta(1, [_linea(1, Decimal("10000"), Decimal("1597")), _linea(2, Decimal("5000"))]),
        _venta(2, [_linea(1, Decimal("2000"))]),
    ]
    r = _svc(ventas, productos=PRODUCTOS).por_categoria(DESDE, HASTA)
    assert [rc.categoria_id for rc in r] == [1, 2]
    res = r[0]
    assert res.total == Decimal("12000")
    assert res.total_impuestos == Decimal("1597")
    assert r[1].total == Decimal("5000")


def test_producto_sin_categoria_va_al_final():
    ventas = [_venta(1, [_linea(3, Decimal("1000")), _linea(1, Decimal("2000"))])]
    r = _svc(ventas, productos=PRODUCTOS).por_categoria(DESDE, HASTA)
    assert [rc.categoria_id for rc in r] == [1, None]
    assert r[1].total == Decimal("1000")


def test_devoluciones_netean_su_categoria():
    ventas = [_venta(1, [_linea(1, Decimal("10000"))])]
    dev = Devolucion(
        venta_id=1, fecha=datetime(2026, 7, 1, 12, 0),
        lineas=(LineaDevolucion(producto_id=1, cantidad_o_peso=Decimal("1"),
                                impuesto=Decimal("0"), subtotal=Decimal("4000")),),
        total=Decimal("4000"), total_impuestos=Decimal("0"), reembolsos=())
    r = _svc(ventas, devs=[dev], productos=PRODUCTOS).por_categoria(DESDE, HASTA)
    assert r[0].total_devoluciones == Decimal("4000")
    assert r[0].neto == Decimal("6000")


def test_sin_ventas_devuelve_vacio():
    assert _svc([], productos=PRODUCTOS).por_categoria(DESDE, HASTA) == ()


def test_sin_repo_productos_falla():
    svc = ServicioReportes(_FakeVentas([]), _FakeDevoluciones(), None, None)
    with pytest.raises(RuntimeError):
        svc.por_categoria(DESDE, HASTA)
