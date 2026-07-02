"""Integración SQLite del repositorio de movimientos de caja (migración 007)."""
from datetime import datetime
from decimal import Decimal

from core.entidades import CajaSesion, MovimientoCaja
from ventas.repositorio_sqlite import RepositorioCajaSesionesSQLite, RepositorioMovimientosCajaSQLite

FECHA = datetime(2026, 7, 1, 10, 30)


def _sesion(conn) -> CajaSesion:
    return RepositorioCajaSesionesSQLite(conn).abrir(
        CajaSesion(apertura_fecha=FECHA, monto_inicial=Decimal("100000")))


def test_registrar_y_leer_por_sesion(conn):
    sesion = _sesion(conn)
    repo = RepositorioMovimientosCajaSQLite(conn)
    repo.registrar(MovimientoCaja(
        caja_sesion_id=sesion.id, tipo="ingreso", monto=Decimal("20000"),
        motivo="base extra", fecha=FECHA, usuario_id=None))
    repo.registrar(MovimientoCaja(
        caja_sesion_id=sesion.id, tipo="egreso", monto=Decimal("5000"),
        motivo="pago domicilio", fecha=FECHA))
    movs = repo.de_sesion(sesion.id)
    assert [m.tipo for m in movs] == ["ingreso", "egreso"]
    assert movs[0].monto == Decimal("20000")
    assert movs[1].motivo == "pago domicilio"
    assert movs[0].fecha == FECHA


def test_de_sesion_vacia_devuelve_lista_vacia(conn):
    sesion = _sesion(conn)
    assert RepositorioMovimientosCajaSQLite(conn).de_sesion(sesion.id) == []


def test_movimientos_no_se_mezclan_entre_sesiones(conn):
    repo_sesiones = RepositorioCajaSesionesSQLite(conn)
    s1 = _sesion(conn)
    repo_sesiones.cerrar(CajaSesion(
        apertura_fecha=FECHA, monto_inicial=Decimal("0"), cierre_fecha=FECHA,
        monto_contado=Decimal("0"), estado="cerrada", id=s1.id))
    s2 = _sesion(conn)
    repo = RepositorioMovimientosCajaSQLite(conn)
    repo.registrar(MovimientoCaja(caja_sesion_id=s1.id, tipo="ingreso",
                                  monto=Decimal("1"), motivo="a", fecha=FECHA))
    repo.registrar(MovimientoCaja(caja_sesion_id=s2.id, tipo="egreso",
                                  monto=Decimal("2"), motivo="b", fecha=FECHA))
    assert len(repo.de_sesion(s1.id)) == 1
    assert repo.de_sesion(s2.id)[0].tipo == "egreso"
