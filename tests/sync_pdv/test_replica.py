"""RepositorioReplicaSQLite: aplica el snapshot de catálogo y lo lee para la venta."""
from decimal import Decimal

from inventario.db import aplicar_migraciones, conectar
from sync_pdv.replica import RepositorioReplicaSQLite

SNAP = {"productos": [{
    "producto_id": 1, "codigo_barras": "0001", "nombre": "Lomo", "unidad": "kg",
    "vendido_por_peso": True, "categoria_id": 10, "categoria_nombre": "Carnes",
    "impuesto_id": 5, "tarifa_impuesto": "0.19", "precio": "20000", "costo": "12000",
    "actualizado_en": "2026-07-07T10:00:00"}], "promociones": []}


def _repo():
    conn = conectar(":memory:")
    aplicar_migraciones(conn)
    return RepositorioReplicaSQLite(conn)


def test_aplicar_y_leer_precio():
    repo = _repo()
    repo.aplicar_catalogo(SNAP)
    assert repo.precio_de(1) == Decimal("20000")
    assert repo.listar()[0]["nombre"] == "Lomo"


def test_precio_de_inexistente_es_none():
    assert _repo().precio_de(999) is None


def test_reemplaza_no_acumula():
    repo = _repo()
    repo.aplicar_catalogo(SNAP)
    repo.aplicar_catalogo({"productos": [], "promociones": []})
    assert repo.listar() == []            # snapshot vacío => réplica vacía (RO reemplazable)


def test_guarda_cursor_catalogo():
    repo = _repo()
    repo.aplicar_catalogo(SNAP)
    fila = repo._conn.execute(
        "SELECT valor FROM sync_cursor WHERE clave='catalogo'").fetchone()
    assert fila["valor"] == "2026-07-07T10:00:00"


def test_aplica_promos():
    repo = _repo()
    snap = {"productos": SNAP["productos"], "promociones": [{
        "id": 7, "producto_id": 1, "tipo_valor": "porcentaje", "valor": "0.10",
        "tipo_duracion": "manual", "activa": True, "desde": None, "hasta": None,
        "unidades_limite": None, "unidades_restantes": None,
        "actualizado_en": "2026-07-07T10:00:00"}]}
    repo.aplicar_catalogo(snap)
    fila = repo._conn.execute("SELECT tipo_valor, valor FROM promo_replica WHERE id=7").fetchone()
    assert fila["tipo_valor"] == "porcentaje" and fila["valor"] == Decimal("0.10")
