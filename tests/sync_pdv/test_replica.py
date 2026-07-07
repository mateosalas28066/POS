"""RepositorioReplicaSQLite: aplica el snapshot de catálogo y lo lee para la venta."""
from decimal import Decimal

from core.entidades import Producto
from inventario.db import aplicar_migraciones, conectar
from inventario.repositorio_sqlite import RepositorioProductosSQLite
from sync_pdv.replica import RepositorioProductosConReplica, RepositorioReplicaSQLite

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


# --- RepositorioProductosConReplica: precio de venta réplica -> fallback local -----

def _productos_y_replica():
    conn = conectar(":memory:")
    aplicar_migraciones(conn)
    productos = RepositorioProductosSQLite(conn)
    productos.guardar(Producto(codigo_barras="0001", nombre="Lomo", precio=Decimal("10000"),
                               vendido_por_peso=True, unidad="kg"))   # id=1, precio LOCAL 10000
    productos.guardar(Producto(codigo_barras="0002", nombre="Banano", precio=Decimal("3000")))
    return RepositorioProductosSQLite(conn), RepositorioReplicaSQLite(conn)


def test_precio_de_venta_sale_de_la_replica():
    productos, replica = _productos_y_replica()
    replica.aplicar_catalogo({"productos": [{
        "producto_id": 1, "codigo_barras": "0001", "nombre": "Lomo", "unidad": "kg",
        "vendido_por_peso": True, "categoria_id": None, "categoria_nombre": None,
        "impuesto_id": None, "tarifa_impuesto": None, "precio": "20000", "costo": "12000",
        "actualizado_en": "2026-07-07T10:00:00"}], "promociones": []})
    repo = RepositorioProductosConReplica(productos, replica)
    assert repo.por_codigo("0001").precio == Decimal("20000")   # gana la réplica
    assert repo.por_id(1).precio == Decimal("20000")


def test_fallback_al_precio_local_si_replica_no_tiene_el_producto():
    productos, replica = _productos_y_replica()   # réplica vacía
    repo = RepositorioProductosConReplica(productos, replica)
    assert repo.por_codigo("0002").precio == Decimal("3000")    # cae al local
    assert repo.por_codigo("9999") is None                      # inexistente sigue None


def test_delega_metodos_no_sobreescritos():
    productos, replica = _productos_y_replica()
    repo = RepositorioProductosConReplica(productos, replica)
    assert len(repo.listar()) == 2               # listar() se delega al repo interno
