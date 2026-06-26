from datetime import datetime
from decimal import Decimal

import pytest

from core.entidades import (
    Arqueo, CajaSesion, Devolucion, LineaDevolucion, LineaVenta, MovimientoInventario, Pago, Venta,
)
from core.servicio_reportes import ServicioReportes, SesionNoEncontrada

DESDE = datetime(2026, 6, 25, 0, 0)
HASTA = datetime(2026, 6, 26, 0, 0)


def _venta(id, total, impuestos, estado="pagada"):
    linea = LineaVenta(producto_id=1, descripcion="X", cantidad_o_peso=Decimal("1"),
                       precio_unit=total, impuesto=impuestos, subtotal=total, venta_id=id, id=id)
    return Venta(fecha=datetime(2026, 6, 25, 10, 0), lineas=(linea,), total=total,
                 total_impuestos=impuestos, estado=estado, id=id)


class _FakeVentas:
    def __init__(self, ventas, pagos, por_medio=None, ventas_sesion=None):
        self._ventas = ventas
        self._pagos = pagos
        self._por_medio = por_medio or {}
        self._ventas_sesion = ventas_sesion if ventas_sesion is not None else ventas
    def ventas_en(self, desde, hasta):
        return list(self._ventas)
    def pagos_en(self, desde, hasta):
        return list(self._pagos)
    def ventas_de_sesion(self, sesion_id):
        return list(self._ventas_sesion)
    def totales_por_medio(self, sesion_id):
        return dict(self._por_medio)


class _FakeDevoluciones:
    def __init__(self, devs):
        self._devs = devs
    def devoluciones_en(self, desde, hasta):
        return list(self._devs)
    def de_sesion(self, sesion_id):
        return list(self._devs)


class _FakeInventario:
    def __init__(self, movs):
        self._movs = movs
    def movimientos_en(self, desde, hasta):
        return list(self._movs)


class _FakeSesiones:
    def __init__(self, sesion):
        self._sesion = sesion
    def por_id(self, id):
        return self._sesion if self._sesion and self._sesion.id == id else None


def _dev(total, impuestos, reembolsos):
    return Devolucion(
        venta_id=1, fecha=datetime(2026, 6, 25, 12, 0),
        lineas=(LineaDevolucion(producto_id=1, cantidad_o_peso=Decimal("1"),
                                impuesto=impuestos, subtotal=total, venta_linea_id=1),),
        total=total, total_impuestos=impuestos, reembolsos=reembolsos)


def test_reporte_ventas_suma_neto_y_por_medio():
    ventas = [_venta(1, Decimal("7000"), Decimal("1118")),
              _venta(2, Decimal("5000"), Decimal("0"))]
    pagos = [Pago(medio_pago_id=1, monto=Decimal("7000")),
             Pago(medio_pago_id=2, monto=Decimal("5000"))]
    devs = [_dev(Decimal("3500"), Decimal("559"),
                 (Pago(medio_pago_id=1, monto=Decimal("3500")),))]
    svc = ServicioReportes(_FakeVentas(ventas, pagos), _FakeDevoluciones(devs),
                           _FakeInventario([]), _FakeSesiones(None))
    r = svc.ventas(DESDE, HASTA)
    assert r.num_ventas == 2
    assert r.total == Decimal("12000")
    assert r.total_impuestos == Decimal("1118")
    assert r.total_devoluciones == Decimal("3500")
    assert r.total_devoluciones_impuestos == Decimal("559")
    assert r.neto == Decimal("8500")                      # 12000 - 3500
    assert r.por_medio == {1: Decimal("3500"), 2: Decimal("5000")}  # medio 1: 7000-3500


def test_reporte_ventas_ignora_devoluciones_vacias():
    ventas = [_venta(1, Decimal("7000"), Decimal("1118"))]
    pagos = [Pago(medio_pago_id=1, monto=Decimal("7000"))]
    svc = ServicioReportes(_FakeVentas(ventas, pagos), _FakeDevoluciones([]),
                           _FakeInventario([]), _FakeSesiones(None))
    r = svc.ventas(DESDE, HASTA)
    assert r.neto == Decimal("7000")
    assert r.por_medio == {1: Decimal("7000")}


def test_reporte_inventario_agrega_por_producto_y_conserva_detalle():
    movs = [
        MovimientoInventario(producto_id=1, tipo="entrada", cantidad=Decimal("10"),
                             fecha=datetime(2026, 6, 25, 8, 0), ref="compra", id=1),
        MovimientoInventario(producto_id=1, tipo="salida", cantidad=Decimal("3"),
                             fecha=datetime(2026, 6, 25, 9, 0), ref="venta:1", id=2),
        MovimientoInventario(producto_id=2, tipo="entrada", cantidad=Decimal("5"),
                             fecha=datetime(2026, 6, 25, 9, 30), ref="compra", id=3),
    ]
    svc = ServicioReportes(_FakeVentas([], []), _FakeDevoluciones([]),
                           _FakeInventario(movs), _FakeSesiones(None))
    r = svc.inventario(DESDE, HASTA)
    assert [(mp.producto_id, mp.entradas, mp.salidas, mp.neto) for mp in r.por_producto] == [
        (1, Decimal("10"), Decimal("3"), Decimal("7")),
        (2, Decimal("5"), Decimal("0"), Decimal("5")),
    ]
    assert [m.id for m in r.movimientos] == [1, 2, 3]


def test_reporte_cierre_sesion_cerrada_usa_monto_contado():
    sesion = CajaSesion(apertura_fecha=datetime(2026, 6, 25, 9, 0), monto_inicial=Decimal("100"),
                        cierre_fecha=datetime(2026, 6, 25, 20, 0), monto_contado=Decimal("3500"),
                        estado="cerrada", id=42)
    ventas = _FakeVentas([_venta(1, Decimal("7000"), Decimal("1118"))], [],
                         por_medio={1: Decimal("3500")},
                         ventas_sesion=[_venta(1, Decimal("7000"), Decimal("1118"))])
    devs = _FakeDevoluciones([_dev(Decimal("3500"), Decimal("559"),
                                   (Pago(medio_pago_id=1, monto=Decimal("3500")),))])
    svc = ServicioReportes(ventas, devs, _FakeInventario([]), _FakeSesiones(sesion))
    r = svc.cierre(42)
    assert isinstance(r.arqueo, Arqueo)
    assert r.arqueo.esperado == Decimal("3600")           # 100 + 3500 efectivo neto
    assert r.arqueo.contado == Decimal("3500")
    assert r.arqueo.diferencia == Decimal("-100")
    assert r.por_medio == {1: Decimal("3500")}
    assert r.num_ventas == 1
    assert r.total_devoluciones == Decimal("3500")


def test_reporte_cierre_sesion_abierta_usa_esperado_como_contado():
    sesion = CajaSesion(apertura_fecha=datetime(2026, 6, 25, 9, 0), monto_inicial=Decimal("100"),
                        estado="abierta", id=7)
    ventas = _FakeVentas([], [], por_medio={1: Decimal("5000")}, ventas_sesion=[])
    svc = ServicioReportes(ventas, _FakeDevoluciones([]), _FakeInventario([]), _FakeSesiones(sesion))
    r = svc.cierre(7)
    assert r.arqueo.contado == Decimal("5100")            # esperado = 100 + 5000
    assert r.arqueo.diferencia == Decimal("0")


def test_reporte_cierre_sesion_inexistente_falla():
    svc = ServicioReportes(_FakeVentas([], []), _FakeDevoluciones([]),
                           _FakeInventario([]), _FakeSesiones(None))
    with pytest.raises(SesionNoEncontrada):
        svc.cierre(999)
