from dataclasses import replace
from datetime import datetime
from decimal import Decimal
import pytest
from core.entidades import CajaSesion, Gasto, MovimientoCaja
from core.servicio_caja import CajaNoAbierta, ServicioCaja
from core.servicio_gastos import ServicioGastos


class _FakeVentas:
    def totales_por_medio(self, caja_sesion_id: int) -> dict[int, Decimal]:
        return {}


class _FakeGastos:
    def __init__(self) -> None:
        self.guardados: list[Gasto] = []
        self._siguiente = 1

    def guardar(self, gasto: Gasto) -> Gasto:
        guardado = replace(gasto, id=self._siguiente)
        self._siguiente += 1
        self.guardados.append(guardado)
        return guardado

    def gastos_en(self, desde: datetime, hasta: datetime) -> list[Gasto]:
        return [g for g in self.guardados if desde <= g.fecha < hasta]


class _FakeCategorias:
    def __init__(self) -> None:
        self.guardadas = []

    def guardar(self, categoria):
        self.guardadas.append(categoria)
        return categoria

    def listar(self):
        return list(self.guardadas)

    def actualizar(self, categoria):
        return categoria


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


def test_gasto_en_efectivo_genera_egreso_de_caja():
    sesiones = _FakeSesiones()
    movimientos = _FakeMovimientos()
    ventas = _FakeVentas()
    caja = ServicioCaja(sesiones, ventas, movimientos=movimientos)
    caja.abrir(fecha=datetime(2026, 7, 1, 9, 0), monto_inicial=Decimal("100000"))
    gastos = _FakeGastos()
    categorias = _FakeCategorias()
    svc = ServicioGastos(gastos, categorias, caja)

    gasto = svc.registrar(categoria_gasto_id=1, monto=Decimal("50000"), medio_pago_id=1,
                           fecha=datetime(2026, 7, 1, 10, 0))

    assert len(movimientos.registrados) == 1
    mov = movimientos.registrados[0]
    assert mov.tipo == "egreso"
    assert mov.monto == Decimal("50000")
    assert gasto.caja_sesion_id is not None
    assert gasto.caja_sesion_id == mov.caja_sesion_id


def test_gasto_no_efectivo_no_toca_caja():
    sesiones = _FakeSesiones()
    movimientos = _FakeMovimientos()
    ventas = _FakeVentas()
    caja = ServicioCaja(sesiones, ventas, movimientos=movimientos)
    caja.abrir(fecha=datetime(2026, 7, 1, 9, 0), monto_inicial=Decimal("100000"))
    gastos = _FakeGastos()
    categorias = _FakeCategorias()
    svc = ServicioGastos(gastos, categorias, caja)

    gasto = svc.registrar(categoria_gasto_id=1, monto=Decimal("50000"), medio_pago_id=2,
                           fecha=datetime(2026, 7, 1, 10, 0))

    assert movimientos.registrados == []
    assert gasto.caja_sesion_id is None


def test_registrar_con_monto_no_positivo_lanza_valueerror():
    sesiones = _FakeSesiones()
    movimientos = _FakeMovimientos()
    ventas = _FakeVentas()
    caja = ServicioCaja(sesiones, ventas, movimientos=movimientos)
    gastos = _FakeGastos()
    categorias = _FakeCategorias()
    svc = ServicioGastos(gastos, categorias, caja)

    with pytest.raises(ValueError):
        svc.registrar(categoria_gasto_id=1, monto=Decimal("0"), medio_pago_id=2,
                       fecha=datetime(2026, 7, 1, 10, 0))


def test_gasto_en_efectivo_sin_caja_abierta_propaga_error():
    sesiones = _FakeSesiones()
    movimientos = _FakeMovimientos()
    ventas = _FakeVentas()
    caja = ServicioCaja(sesiones, ventas, movimientos=movimientos)
    gastos = _FakeGastos()
    categorias = _FakeCategorias()
    svc = ServicioGastos(gastos, categorias, caja)

    with pytest.raises(CajaNoAbierta):
        svc.registrar(categoria_gasto_id=1, monto=Decimal("50000"), medio_pago_id=1,
                       fecha=datetime(2026, 7, 1, 10, 0))
