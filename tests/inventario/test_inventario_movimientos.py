from datetime import datetime
from decimal import Decimal

from core.entidades import Categoria, MovimientoInventario, Producto
from inventario.repositorio_sqlite import (
    RepositorioCategoriasSQLite,
    RepositorioInventarioSQLite,
    RepositorioProductosSQLite,
)


def _producto(conn) -> Producto:
    cat = RepositorioCategoriasSQLite(conn).guardar(Categoria(nombre="Carnes"))
    return RepositorioProductosSQLite(conn).guardar(
        Producto(codigo_barras="7701", nombre="Lomo", precio=Decimal("32000"),
                 categoria_id=cat.id, vendido_por_peso=True, unidad="kg"))


def test_stock_sin_movimientos_es_cero(conn):
    p = _producto(conn)
    assert RepositorioInventarioSQLite(conn).stock_de(p.id) == Decimal("0")


def test_entrada_suma_y_salida_descuenta_stock(conn):
    p = _producto(conn)
    repo = RepositorioInventarioSQLite(conn)
    repo.registrar(MovimientoInventario(producto_id=p.id, tipo="entrada",
                                        cantidad=Decimal("10.5"), fecha=datetime(2026, 6, 25)))
    repo.registrar(MovimientoInventario(producto_id=p.id, tipo="salida",
                                        cantidad=Decimal("2.250"), fecha=datetime(2026, 6, 25),
                                        ref="venta#1"))
    assert repo.stock_de(p.id) == Decimal("8.250")  # exacto, sin float


def test_registrar_asigna_id(conn):
    p = _producto(conn)
    m = RepositorioInventarioSQLite(conn).registrar(
        MovimientoInventario(producto_id=p.id, tipo="entrada",
                             cantidad=Decimal("1"), fecha=datetime(2026, 6, 25)))
    assert m.id is not None
