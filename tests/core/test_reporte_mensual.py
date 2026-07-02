from datetime import datetime
from decimal import Decimal

import pytest

from core.entidades import Compra, Gasto, LineaCompra, LineaVenta, Venta
from core.servicio_reportes import ServicioReportes

ANIO = 2026
MES = 6


def _en_rango(fecha, desde, hasta):
    return desde <= fecha < hasta


def _venta(fecha, total):
    linea = LineaVenta(producto_id=1, descripcion="X", cantidad_o_peso=Decimal("1"),
                       precio_unit=total, impuesto=Decimal("0"), subtotal=total, id=1)
    return Venta(fecha=fecha, lineas=(linea,), total=total,
                 total_impuestos=Decimal("0"), estado="pagada", id=1)


def _compra(fecha, total):
    linea = LineaCompra(producto_id=1, descripcion="X", cantidad=Decimal("1"),
                        costo_unit=total, subtotal=total)
    return Compra(proveedor_id=1, fecha=fecha, lineas=(linea,), total=total, id=1)


def _gasto(fecha, monto):
    return Gasto(fecha=fecha, categoria_gasto_id=1, monto=monto)


class _FakeVentasRepo:
    def __init__(self, ventas):
        self._ventas = ventas
    def ventas_en(self, desde, hasta):
        return [v for v in self._ventas if _en_rango(v.fecha, desde, hasta)]
    def pagos_en(self, desde, hasta):
        return []


class _FakeDevolucionesRepo:
    def devoluciones_en(self, desde, hasta):
        return []


class _FakeInventarioRepo:
    def movimientos_en(self, desde, hasta):
        return []


class _FakeSesionesRepo:
    def por_id(self, id):
        return None


class _FakeComprasRepo:
    def __init__(self, compras):
        self._compras = compras
    def compras_en(self, desde, hasta):
        return [c for c in self._compras if _en_rango(c.fecha, desde, hasta)]


class _FakeGastosRepo:
    def __init__(self, gastos):
        self._gastos = gastos
    def gastos_en(self, desde, hasta):
        return [g for g in self._gastos if _en_rango(g.fecha, desde, hasta)]


class _FakeCuentas:
    """Duck-typed fake para ServicioCuentasCobrar/ServicioCuentasPagar: solo pendientes()."""
    def __init__(self, saldos):
        self._saldos = saldos
    def pendientes(self):
        return dict(self._saldos)


def _servicio(ventas, compras, gastos, saldos_cxc, saldos_cxp):
    return ServicioReportes(
        _FakeVentasRepo(ventas), _FakeDevolucionesRepo(), _FakeInventarioRepo(),
        _FakeSesionesRepo(),
        compras=_FakeComprasRepo(compras),
        gastos=_FakeGastosRepo(gastos),
        cxc=_FakeCuentas(saldos_cxc),
        cxp=_FakeCuentas(saldos_cxp),
    )


def test_mensual_consolida_ventas_compras_gastos_saldos():
    ventas = [_venta(datetime(ANIO, MES, 15), Decimal("100000"))]
    compras = [_compra(datetime(ANIO, MES, 10), Decimal("40000"))]
    gastos = [_gasto(datetime(ANIO, MES, 5), Decimal("30000")),
              _gasto(datetime(ANIO, MES, 20), Decimal("5000"))]
    svc = _servicio(ventas, compras, gastos, {1: Decimal("20000")}, {2: Decimal("15000")})

    r = svc.mensual(ANIO, MES)

    assert r.anio == ANIO
    assert r.mes == MES
    assert r.ventas == Decimal("100000")
    assert r.compras == Decimal("40000")
    assert r.gastos == Decimal("35000")
    assert r.saldo_cxc == Decimal("20000")
    assert r.saldo_cxp == Decimal("15000")


def test_mensual_excluye_movimientos_fuera_del_mes():
    ventas = [_venta(datetime(ANIO, MES, 15), Decimal("100000")),
              _venta(datetime(ANIO, MES + 1, 1), Decimal("999999"))]
    compras = [_compra(datetime(ANIO, MES, 10), Decimal("40000")),
               _compra(datetime(ANIO, MES - 1, 28), Decimal("777777"))]
    gastos = [_gasto(datetime(ANIO, MES, 5), Decimal("30000")),
              _gasto(datetime(ANIO, MES, 20), Decimal("5000")),
              _gasto(datetime(ANIO, MES + 1, 2), Decimal("888888"))]
    svc = _servicio(ventas, compras, gastos, {}, {})

    r = svc.mensual(ANIO, MES)

    assert r.ventas == Decimal("100000")
    assert r.compras == Decimal("40000")
    assert r.gastos == Decimal("35000")


def test_mensual_sin_dependencias_lanza_runtime_error():
    svc = ServicioReportes(
        _FakeVentasRepo([]), _FakeDevolucionesRepo(), _FakeInventarioRepo(),
        _FakeSesionesRepo())
    with pytest.raises(RuntimeError):
        svc.mensual(ANIO, MES)
