from datetime import datetime
from decimal import Decimal

from core.entidades import CajaSesion
from ventas.repositorio_sqlite import RepositorioCajaSesionesSQLite


def test_listar_devuelve_todas_las_sesiones(conn):
    repo = RepositorioCajaSesionesSQLite(conn)
    repo.abrir(CajaSesion(apertura_fecha=datetime(2026, 6, 1, 8), monto_inicial=Decimal("100")))
    repo.abrir(CajaSesion(apertura_fecha=datetime(2026, 6, 2, 8), monto_inicial=Decimal("200")))
    sesiones = repo.listar()
    assert len(sesiones) == 2
    assert sesiones[0].monto_inicial == Decimal("100")
