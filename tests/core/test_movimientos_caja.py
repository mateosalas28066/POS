"""Movimientos manuales de efectivo: entidad, arqueo extendido y ServicioCaja."""
from dataclasses import replace
from datetime import datetime
from decimal import Decimal

import pytest

from core.calculos import calcular_arqueo
from core.entidades import CajaSesion, MovimientoCaja
from core.servicio_caja import CajaNoAbierta, EfectivoInsuficiente, ServicioCaja

FECHA = datetime(2026, 7, 1, 10, 0)


def _mov(**kwargs) -> MovimientoCaja:
    base = dict(caja_sesion_id=1, tipo="ingreso", monto=Decimal("1000"),
                motivo="base extra", fecha=FECHA)
    base.update(kwargs)
    return MovimientoCaja(**base)


def test_movimiento_valido():
    m = _mov(tipo="egreso", motivo="retiro a bóveda")
    assert m.tipo == "egreso"
    assert m.monto == Decimal("1000")


def test_movimiento_tipo_invalido_falla():
    with pytest.raises(ValueError):
        _mov(tipo="ajuste")


def test_movimiento_monto_no_positivo_falla():
    with pytest.raises(ValueError):
        _mov(monto=Decimal("0"))


def test_movimiento_sin_motivo_falla():
    with pytest.raises(ValueError):
        _mov(motivo="   ")


def test_arqueo_suma_ingresos_y_resta_egresos():
    a = calcular_arqueo(Decimal("100000"), Decimal("50000"), Decimal("130000"),
                        Decimal("20000"), Decimal("40000"))
    assert a.esperado == Decimal("130000")
    assert a.diferencia == Decimal("0")
    assert a.otros_ingresos == Decimal("20000")
    assert a.otros_egresos == Decimal("40000")


def test_arqueo_movimientos_negativos_falla():
    with pytest.raises(ValueError):
        calcular_arqueo(Decimal("0"), Decimal("0"), Decimal("0"),
                        Decimal("-1"), Decimal("0"))


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


class _FakeVentas:
    def __init__(self, totales: dict[int, Decimal] | None = None) -> None:
        self._totales = totales or {}

    def totales_por_medio(self, caja_sesion_id: int) -> dict[int, Decimal]:
        return dict(self._totales)


class _FakeMovimientos:
    def __init__(self) -> None:
        self._items: list[MovimientoCaja] = []

    def registrar(self, m: MovimientoCaja) -> MovimientoCaja:
        guardado = replace(m, id=len(self._items) + 1)
        self._items.append(guardado)
        return guardado

    def de_sesion(self, caja_sesion_id: int) -> list[MovimientoCaja]:
        return [m for m in self._items if m.caja_sesion_id == caja_sesion_id]


def _servicio(totales=None) -> ServicioCaja:
    return ServicioCaja(_FakeSesiones(), _FakeVentas(totales), movimientos=_FakeMovimientos())


def test_registrar_movimiento_sin_caja_abierta_falla():
    with pytest.raises(CajaNoAbierta):
        _servicio().registrar_movimiento(
            tipo="ingreso", monto=Decimal("1000"), motivo="base", fecha=FECHA)


def test_registrar_movimiento_asigna_sesion_e_id():
    serv = _servicio()
    s = serv.abrir(fecha=FECHA, monto_inicial=Decimal("100000"))
    m = serv.registrar_movimiento(
        tipo="ingreso", monto=Decimal("5000"), motivo="base extra", fecha=FECHA, usuario_id=7)
    assert m.id is not None
    assert m.caja_sesion_id == s.id
    assert m.usuario_id == 7


def test_arqueo_incluye_movimientos():
    serv = _servicio(totales={1: Decimal("50000")})
    s = serv.abrir(fecha=FECHA, monto_inicial=Decimal("100000"))
    serv.registrar_movimiento(tipo="ingreso", monto=Decimal("20000"), motivo="base", fecha=FECHA)
    serv.registrar_movimiento(tipo="egreso", monto=Decimal("40000"), motivo="retiro", fecha=FECHA)
    a = serv.arqueo(s.id, Decimal("130000"))
    assert a.esperado == Decimal("130000")   # 100000 + 50000 + 20000 − 40000
    assert a.diferencia == Decimal("0")


def test_egreso_mayor_al_efectivo_esperado_falla():
    serv = _servicio(totales={1: Decimal("10000")})
    serv.abrir(fecha=FECHA, monto_inicial=Decimal("5000"))
    with pytest.raises(EfectivoInsuficiente):
        serv.registrar_movimiento(
            tipo="egreso", monto=Decimal("15001"), motivo="retiro", fecha=FECHA)


def test_servicio_sin_repo_movimientos_arqueo_ignora():
    serv = ServicioCaja(_FakeSesiones(), _FakeVentas({1: Decimal("10000")}))
    s = serv.abrir(fecha=FECHA, monto_inicial=Decimal("5000"))
    assert serv.arqueo(s.id, Decimal("15000")).diferencia == Decimal("0")
