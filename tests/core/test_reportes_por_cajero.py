from datetime import datetime
from decimal import Decimal

import pytest

from core.entidades import CajaSesion, Devolucion, LineaDevolucion, LineaVenta, Pago, Venta
from core.servicio_reportes import ReporteCajero, ServicioReportes, SesionNoEncontrada

DESDE = datetime(2026, 6, 25, 0, 0)
HASTA = datetime(2026, 6, 26, 0, 0)


def _venta(id, usuario_id, total, impuestos=Decimal("0"), estado="pagada"):
    linea = LineaVenta(producto_id=1, descripcion="X", cantidad_o_peso=Decimal("1"),
                       precio_unit=total, impuesto=impuestos, subtotal=total, venta_id=id, id=id)
    return Venta(fecha=datetime(2026, 6, 25, 10, 0), lineas=(linea,), total=total,
                 total_impuestos=impuestos, usuario_id=usuario_id, estado=estado, id=id)


def _dev(usuario_id, total, reembolsos=()):
    return Devolucion(
        venta_id=1, fecha=datetime(2026, 6, 25, 12, 0),
        lineas=(LineaDevolucion(producto_id=1, cantidad_o_peso=Decimal("1"),
                                impuesto=Decimal("0"), subtotal=total, venta_linea_id=1),),
        total=total, total_impuestos=Decimal("0"), reembolsos=reembolsos, usuario_id=usuario_id)


class _FakeVentas:
    def __init__(self, ventas, pagos, pagos_por_venta=None):
        self._ventas = ventas
        self._pagos = pagos
        self._ppv = pagos_por_venta or {}
    def ventas_en(self, desde, hasta):
        return list(self._ventas)
    def pagos_en(self, desde, hasta):
        return list(self._pagos)
    def ventas_de_sesion(self, sesion_id):
        return list(self._ventas)
    def pagos_de(self, venta_id):
        return list(self._ppv.get(venta_id, []))


class _FakeDevoluciones:
    def __init__(self, devs):
        self._devs = devs
    def devoluciones_en(self, desde, hasta):
        return list(self._devs)
    def de_sesion(self, sesion_id):
        return list(self._devs)


class _FakeSesiones:
    def __init__(self, sesion):
        self._sesion = sesion
    def por_id(self, id):
        return self._sesion if self._sesion and self._sesion.id == id else None


def test_por_cajero_agrupa_totales_devoluciones_y_por_medio():
    ventas = [_venta(1, 10, Decimal("7000"), Decimal("1118")),
              _venta(2, 10, Decimal("5000")),
              _venta(3, 20, Decimal("3000"))]
    pagos = [Pago(medio_pago_id=1, monto=Decimal("7000"), venta_id=1),
             Pago(medio_pago_id=2, monto=Decimal("5000"), venta_id=2),
             Pago(medio_pago_id=1, monto=Decimal("3000"), venta_id=3)]
    devs = [_dev(10, Decimal("2000"), (Pago(medio_pago_id=1, monto=Decimal("2000")),))]
    svc = ServicioReportes(_FakeVentas(ventas, pagos), _FakeDevoluciones(devs),
                           None, _FakeSesiones(None))
    por = {c.usuario_id: c for c in svc.por_cajero(DESDE, HASTA)}
    assert por[10].num_ventas == 2
    assert por[10].total == Decimal("12000")
    assert por[10].total_impuestos == Decimal("1118")
    assert por[10].total_devoluciones == Decimal("2000")
    assert por[10].neto == Decimal("10000")                       # 12000 - 2000
    assert por[10].por_medio == {1: Decimal("5000"), 2: Decimal("5000")}  # medio1: 7000-2000
    assert por[20].num_ventas == 1
    assert por[20].total == Decimal("3000")
    assert por[20].por_medio == {1: Decimal("3000")}


def test_por_cajero_usuario_nulo_va_al_final():
    ventas = [_venta(1, None, Decimal("1000")), _venta(2, 5, Decimal("2000"))]
    svc = ServicioReportes(_FakeVentas(ventas, []), _FakeDevoluciones([]),
                           None, _FakeSesiones(None))
    assert [c.usuario_id for c in svc.por_cajero(DESDE, HASTA)] == [5, None]


def test_por_cajero_ignora_pago_de_venta_fuera_del_conjunto():
    ventas = [_venta(1, 10, Decimal("7000"))]
    pagos = [Pago(medio_pago_id=1, monto=Decimal("7000"), venta_id=1),
             Pago(medio_pago_id=1, monto=Decimal("9999"), venta_id=99)]  # huérfano
    svc = ServicioReportes(_FakeVentas(ventas, pagos), _FakeDevoluciones([]),
                           None, _FakeSesiones(None))
    por = {c.usuario_id: c for c in svc.por_cajero(DESDE, HASTA)}
    assert por[10].por_medio == {1: Decimal("7000")}
