from dataclasses import replace
from datetime import datetime
from decimal import Decimal
import pytest
from core.entidades import CajaSesion
from core.servicio_caja import (
    CajaNoAbierta, CajaNoEncontrada, CajaYaAbierta, ServicioCaja,
)

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

def _servicio(totales=None) -> ServicioCaja:
    return ServicioCaja(_FakeSesiones(), _FakeVentas(totales))

def test_abrir_devuelve_sesion_con_id():
    s = _servicio().abrir(fecha=datetime(2026, 6, 25, 9, 0), monto_inicial=Decimal("100000"))
    assert s.id is not None
    assert s.estado == "abierta"
    assert s.monto_inicial == Decimal("100000")

def test_abrir_dos_veces_falla():
    serv = _servicio()
    serv.abrir(fecha=datetime(2026, 6, 25, 9, 0), monto_inicial=Decimal("100000"))
    with pytest.raises(CajaYaAbierta):
        serv.abrir(fecha=datetime(2026, 6, 25, 9, 5), monto_inicial=Decimal("0"))

def test_arqueo_usa_solo_efectivo():
    serv = _servicio(totales={1: Decimal("13000"), 2: Decimal("9000")})
    s = serv.abrir(fecha=datetime(2026, 6, 25, 9, 0), monto_inicial=Decimal("100000"))
    a = serv.arqueo(s.id, Decimal("112000"))
    assert a.efectivo_ventas == Decimal("13000")   # ignora tarjeta (medio 2)
    assert a.esperado == Decimal("113000")
    assert a.diferencia == Decimal("-1000")

def test_arqueo_sin_ventas_es_la_base():
    serv = _servicio()
    s = serv.abrir(fecha=datetime(2026, 6, 25, 9, 0), monto_inicial=Decimal("50000"))
    a = serv.arqueo(s.id, Decimal("50000"))
    assert a.efectivo_ventas == Decimal("0")
    assert a.diferencia == Decimal("0")

def test_arqueo_sesion_inexistente_falla():
    with pytest.raises(CajaNoEncontrada):
        _servicio().arqueo(999, Decimal("0"))

def test_cerrar_marca_cerrada_y_devuelve_arqueo():
    serv = _servicio(totales={1: Decimal("13000")})
    s = serv.abrir(fecha=datetime(2026, 6, 25, 9, 0), monto_inicial=Decimal("100000"))
    cerrada, arqueo = serv.cerrar(sesion_id=s.id, fecha=datetime(2026, 6, 25, 20, 0),
                                  monto_contado=Decimal("113000"))
    assert cerrada.estado == "cerrada"
    assert cerrada.cierre_fecha == datetime(2026, 6, 25, 20, 0)
    assert cerrada.monto_contado == Decimal("113000")
    assert arqueo.diferencia == Decimal("0")

def test_cerrar_sesion_ya_cerrada_falla():
    serv = _servicio()
    s = serv.abrir(fecha=datetime(2026, 6, 25, 9, 0), monto_inicial=Decimal("0"))
    serv.cerrar(sesion_id=s.id, fecha=datetime(2026, 6, 25, 20, 0), monto_contado=Decimal("0"))
    with pytest.raises(CajaNoAbierta):
        serv.cerrar(sesion_id=s.id, fecha=datetime(2026, 6, 25, 21, 0), monto_contado=Decimal("0"))
