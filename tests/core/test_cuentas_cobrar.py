from dataclasses import replace
from datetime import datetime
from decimal import Decimal
import pytest
from core.entidades import AbonoCliente, CajaSesion, MovimientoCaja
from core.servicio_caja import CajaNoAbierta, ServicioCaja
from core.servicio_cuentas_cobrar import ServicioCuentasCobrar


class _FakeVentas:
    def __init__(self, fiado: dict[int, Decimal] | None = None) -> None:
        self._fiado = fiado or {}

    def fiado_por_cliente(self, medio_fiado_id: int) -> dict[int, Decimal]:
        return dict(self._fiado)

    def totales_por_medio(self, caja_sesion_id: int) -> dict[int, Decimal]:
        return {}


class _FakeCuentas:
    def __init__(self, abonos: dict[int, Decimal] | None = None) -> None:
        self._abonos = dict(abonos or {})
        self.guardados: list[AbonoCliente] = []
        self._siguiente = 1

    def guardar(self, abono: AbonoCliente) -> AbonoCliente:
        guardado = replace(abono, id=self._siguiente)
        self._siguiente += 1
        self.guardados.append(guardado)
        self._abonos[abono.cliente_id] = self._abonos.get(abono.cliente_id, Decimal("0")) + abono.monto
        return guardado

    def abonos_por_cliente(self) -> dict[int, Decimal]:
        return dict(self._abonos)


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


def test_saldo_es_fiado_menos_abonos():
    ventas = _FakeVentas(fiado={7: Decimal("50000")})
    cuentas = _FakeCuentas(abonos={7: Decimal("20000")})
    caja = ServicioCaja(_FakeSesiones(), _FakeVentas(), movimientos=_FakeMovimientos())
    svc = ServicioCuentasCobrar(cuentas, ventas, caja)

    assert svc.saldo(7) == Decimal("30000")


def test_pendientes_solo_incluye_saldo_positivo():
    ventas = _FakeVentas(fiado={7: Decimal("50000"), 8: Decimal("10000")})
    cuentas = _FakeCuentas(abonos={7: Decimal("20000"), 8: Decimal("10000")})
    caja = ServicioCaja(_FakeSesiones(), _FakeVentas(), movimientos=_FakeMovimientos())
    svc = ServicioCuentasCobrar(cuentas, ventas, caja)

    pendientes = svc.pendientes()

    assert pendientes == {7: Decimal("30000")}


def test_abono_en_efectivo_genera_ingreso_de_caja():
    sesiones = _FakeSesiones()
    movimientos = _FakeMovimientos()
    ventas = _FakeVentas(fiado={7: Decimal("50000")})
    caja = ServicioCaja(sesiones, ventas, movimientos=movimientos)
    caja.abrir(fecha=datetime(2026, 7, 1, 9, 0), monto_inicial=Decimal("100000"))
    cuentas = _FakeCuentas()
    svc = ServicioCuentasCobrar(cuentas, ventas, caja)

    abono = svc.abonar(cliente_id=7, monto=Decimal("20000"), medio_pago_id=1,
                        fecha=datetime(2026, 7, 1, 10, 0))

    assert len(movimientos.registrados) == 1
    mov = movimientos.registrados[0]
    assert mov.tipo == "ingreso"
    assert mov.monto == Decimal("20000")
    assert abono.caja_sesion_id is not None
    assert abono.caja_sesion_id == mov.caja_sesion_id


def test_abono_no_efectivo_no_toca_caja():
    sesiones = _FakeSesiones()
    movimientos = _FakeMovimientos()
    ventas = _FakeVentas(fiado={7: Decimal("50000")})
    caja = ServicioCaja(sesiones, ventas, movimientos=movimientos)
    caja.abrir(fecha=datetime(2026, 7, 1, 9, 0), monto_inicial=Decimal("100000"))
    cuentas = _FakeCuentas()
    svc = ServicioCuentasCobrar(cuentas, ventas, caja)

    abono = svc.abonar(cliente_id=7, monto=Decimal("20000"), medio_pago_id=2,
                        fecha=datetime(2026, 7, 1, 10, 0))

    assert movimientos.registrados == []
    assert abono.caja_sesion_id is None


def test_abono_en_efectivo_sin_caja_abierta_propaga_error():
    sesiones = _FakeSesiones()
    movimientos = _FakeMovimientos()
    ventas = _FakeVentas(fiado={7: Decimal("50000")})
    caja = ServicioCaja(sesiones, ventas, movimientos=movimientos)
    cuentas = _FakeCuentas()
    svc = ServicioCuentasCobrar(cuentas, ventas, caja)

    with pytest.raises(CajaNoAbierta):
        svc.abonar(cliente_id=7, monto=Decimal("20000"), medio_pago_id=1,
                   fecha=datetime(2026, 7, 1, 10, 0))
