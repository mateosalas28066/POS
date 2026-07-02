from dataclasses import replace
from datetime import datetime
from decimal import Decimal
import pytest
from core.entidades import CajaSesion, MovimientoCaja, PagoProveedor
from core.servicio_caja import CajaNoAbierta, ServicioCaja
from core.servicio_cuentas_pagar import ServicioCuentasPagar


class _FakeCompras:
    def __init__(self, credito: dict[int, Decimal] | None = None) -> None:
        self._credito = credito or {}

    def credito_por_proveedor(self) -> dict[int, Decimal]:
        return dict(self._credito)


class _FakeVentas:
    def totales_por_medio(self, caja_sesion_id: int) -> dict[int, Decimal]:
        return {}


class _FakeCuentas:
    def __init__(self, pagos: dict[int, Decimal] | None = None) -> None:
        self._pagos = dict(pagos or {})
        self.guardados: list[PagoProveedor] = []
        self._siguiente = 1

    def guardar(self, pago: PagoProveedor) -> PagoProveedor:
        guardado = replace(pago, id=self._siguiente)
        self._siguiente += 1
        self.guardados.append(guardado)
        self._pagos[pago.proveedor_id] = self._pagos.get(pago.proveedor_id, Decimal("0")) + pago.monto
        return guardado

    def pagos_por_proveedor(self) -> dict[int, Decimal]:
        return dict(self._pagos)


class _FakeSesiones:
    def __init__(self) -> None:
        self._por_id: dict[int, CajaSesion] = {}
        self._siguiente = 1

    def abrir(self, sesion: CajaSesion) -> CajaSesion:
        guardada = replace(sesion, id=self._siguiente)
        self._por_id[self._siguiente] = guardada
        self._siguiente += 1
        return guardada

    def cerrar(self, sesion: CajaSesion) -> CajaSesion:
        self._por_id[sesion.id] = sesion
        return sesion

    def por_id(self, id: int):
        return self._por_id.get(id)

    def abierta(self):
        return next((s for s in self._por_id.values() if s.estado == "abierta"), None)


class _FakeMovimientos:
    def __init__(self) -> None:
        self.registrados: list[MovimientoCaja] = []
        self._siguiente = 1

    def registrar(self, movimiento: MovimientoCaja) -> MovimientoCaja:
        guardado = replace(movimiento, id=self._siguiente)
        self._siguiente += 1
        self.registrados.append(guardado)
        return guardado

    def de_sesion(self, caja_sesion_id: int) -> list[MovimientoCaja]:
        return [m for m in self.registrados if m.caja_sesion_id == caja_sesion_id]


def test_saldo_es_credito_menos_pagos():
    compras = _FakeCompras(credito={3: Decimal("100000")})
    cuentas = _FakeCuentas(pagos={3: Decimal("40000")})
    caja = ServicioCaja(_FakeSesiones(), _FakeVentas(), movimientos=_FakeMovimientos())
    svc = ServicioCuentasPagar(cuentas, compras, caja)

    assert svc.saldo(3) == Decimal("60000")


def test_pendientes_solo_incluye_saldo_positivo():
    compras = _FakeCompras(credito={3: Decimal("100000"), 8: Decimal("10000")})
    cuentas = _FakeCuentas(pagos={3: Decimal("40000"), 8: Decimal("10000")})
    caja = ServicioCaja(_FakeSesiones(), _FakeVentas(), movimientos=_FakeMovimientos())
    svc = ServicioCuentasPagar(cuentas, compras, caja)

    pendientes = svc.pendientes()

    assert pendientes == {3: Decimal("60000")}


def test_pago_en_efectivo_genera_egreso_de_caja():
    sesiones = _FakeSesiones()
    movimientos = _FakeMovimientos()
    ventas = _FakeVentas()
    caja = ServicioCaja(sesiones, ventas, movimientos=movimientos)
    caja.abrir(fecha=datetime(2026, 7, 1, 9, 0), monto_inicial=Decimal("100000"))
    compras = _FakeCompras(credito={3: Decimal("100000")})
    cuentas = _FakeCuentas()
    svc = ServicioCuentasPagar(cuentas, compras, caja)

    pago = svc.pagar(proveedor_id=3, monto=Decimal("40000"), medio_pago_id=1,
                      fecha=datetime(2026, 7, 1, 10, 0))

    assert len(movimientos.registrados) == 1
    mov = movimientos.registrados[0]
    assert mov.tipo == "egreso"
    assert mov.monto == Decimal("40000")
    assert pago.caja_sesion_id is not None
    assert pago.caja_sesion_id == mov.caja_sesion_id


def test_pago_no_efectivo_no_toca_caja():
    sesiones = _FakeSesiones()
    movimientos = _FakeMovimientos()
    ventas = _FakeVentas()
    caja = ServicioCaja(sesiones, ventas, movimientos=movimientos)
    caja.abrir(fecha=datetime(2026, 7, 1, 9, 0), monto_inicial=Decimal("100000"))
    compras = _FakeCompras(credito={3: Decimal("100000")})
    cuentas = _FakeCuentas()
    svc = ServicioCuentasPagar(cuentas, compras, caja)

    pago = svc.pagar(proveedor_id=3, monto=Decimal("40000"), medio_pago_id=2,
                      fecha=datetime(2026, 7, 1, 10, 0))

    assert movimientos.registrados == []
    assert pago.caja_sesion_id is None


def test_pago_en_efectivo_sin_caja_abierta_propaga_error():
    sesiones = _FakeSesiones()
    movimientos = _FakeMovimientos()
    ventas = _FakeVentas()
    caja = ServicioCaja(sesiones, ventas, movimientos=movimientos)
    compras = _FakeCompras(credito={3: Decimal("100000")})
    cuentas = _FakeCuentas()
    svc = ServicioCuentasPagar(cuentas, compras, caja)

    with pytest.raises(CajaNoAbierta):
        svc.pagar(proveedor_id=3, monto=Decimal("40000"), medio_pago_id=1,
                  fecha=datetime(2026, 7, 1, 10, 0))
