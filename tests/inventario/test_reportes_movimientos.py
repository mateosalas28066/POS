from datetime import datetime
from decimal import Decimal

from core.entidades import Categoria, Impuesto, MovimientoInventario, Producto
from inventario.repositorio_sqlite import (
    RepositorioCategoriasSQLite,
    RepositorioImpuestosSQLite,
    RepositorioInventarioSQLite,
    RepositorioProductosSQLite,
)


def _producto(conn):
    cat = RepositorioCategoriasSQLite(conn).guardar(Categoria(nombre="Carnes"))
    imp = RepositorioImpuestosSQLite(conn).guardar(Impuesto(nombre="IVA", tarifa=Decimal("0.19")))
    return RepositorioProductosSQLite(conn).guardar(
        Producto(codigo_barras="C", nombre="Lomo", precio=Decimal("30000"),
                 categoria_id=cat.id, impuesto_id=imp.id))


def test_movimientos_en_filtra_por_rango(conn):
    prod = _producto(conn)
    repo = RepositorioInventarioSQLite(conn)
    repo.registrar(MovimientoInventario(producto_id=prod.id, tipo="entrada",
                                        cantidad=Decimal("10"), fecha=datetime(2026, 6, 24, 8, 0),
                                        ref="compra"))
    repo.registrar(MovimientoInventario(producto_id=prod.id, tipo="salida",
                                        cantidad=Decimal("2"), fecha=datetime(2026, 6, 25, 9, 0),
                                        ref="venta:1"))
    repo.registrar(MovimientoInventario(producto_id=prod.id, tipo="entrada",
                                        cantidad=Decimal("1"), fecha=datetime(2026, 6, 26, 9, 0),
                                        ref="devolucion:1"))

    # [25, 26) -> solo la salida del 25
    movs = repo.movimientos_en(datetime(2026, 6, 25, 0, 0), datetime(2026, 6, 26, 0, 0))
    assert [m.ref for m in movs] == ["venta:1"]
    assert movs[0].tipo == "salida"
    assert movs[0].cantidad == Decimal("2")
    assert movs[0].producto_id == prod.id


def test_movimientos_en_devuelve_varios_ordenados(conn):
    prod = _producto(conn)
    repo = RepositorioInventarioSQLite(conn)
    repo.registrar(MovimientoInventario(producto_id=prod.id, tipo="entrada",
                                        cantidad=Decimal("10"), fecha=datetime(2026, 6, 25, 8, 0),
                                        ref="compra"))
    repo.registrar(MovimientoInventario(producto_id=prod.id, tipo="salida",
                                        cantidad=Decimal("3"), fecha=datetime(2026, 6, 25, 10, 0),
                                        ref="venta:7"))
    movs = repo.movimientos_en(datetime(2026, 6, 25, 0, 0), datetime(2026, 6, 26, 0, 0))
    assert [m.ref for m in movs] == ["compra", "venta:7"]
    assert all(isinstance(m, MovimientoInventario) for m in movs)
