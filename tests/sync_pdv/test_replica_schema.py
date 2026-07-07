"""La migración 012 crea las tablas de la réplica RO de catálogo + el cursor de sync."""
from inventario.db import aplicar_migraciones, conectar


def test_replica_tablas_existen():
    conn = conectar(":memory:")
    aplicar_migraciones(conn)
    tablas = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"catalogo_replica", "promo_replica", "sync_cursor", "novedades_catalogo"} <= tablas
