# tests/inventario/test_repositorio_catalogo.py
from decimal import Decimal

import pytest

from core.entidades import Categoria, Impuesto, Producto
from inventario.repositorio_sqlite import (
    RepositorioCategoriasSQLite,
    RepositorioImpuestosSQLite,
    RepositorioProductosSQLite,
)


def _seed_producto(conn, **extra) -> Producto:
    cat = RepositorioCategoriasSQLite(conn).guardar(Categoria(nombre="Carnes"))
    imp = RepositorioImpuestosSQLite(conn).guardar(Impuesto(nombre="IVA", tarifa=Decimal("0.19")))
    base = dict(codigo_barras="7701234567890", nombre="Lomo", precio=Decimal("32000"),
                costo=Decimal("21000"), categoria_id=cat.id, impuesto_id=imp.id,
                vendido_por_peso=True, unidad="kg")
    base.update(extra)
    return RepositorioProductosSQLite(conn).guardar(Producto(**base))


def test_alta_de_producto_asigna_id(conn):
    p = _seed_producto(conn)
    assert p.id is not None


def test_consulta_por_id_devuelve_decimales_exactos(conn):
    guardado = _seed_producto(conn)
    repo = RepositorioProductosSQLite(conn)
    leido = repo.por_id(guardado.id)
    assert leido.precio == Decimal("32000")
    assert leido.vendido_por_peso is True
    assert leido.unidad == "kg"


def test_consulta_por_codigo_de_barras(conn):
    _seed_producto(conn)
    repo = RepositorioProductosSQLite(conn)
    assert repo.por_codigo("7701234567890").nombre == "Lomo"
    assert repo.por_codigo("noexiste") is None


def test_listar_devuelve_todos(conn):
    cat = RepositorioCategoriasSQLite(conn).guardar(Categoria(nombre="Carnes"))
    imp = RepositorioImpuestosSQLite(conn).guardar(Impuesto(nombre="IVA", tarifa=Decimal("0.19")))
    repo = RepositorioProductosSQLite(conn)
    repo.guardar(Producto(codigo_barras="7701234567890", nombre="Lomo",
                          precio=Decimal("32000"), costo=Decimal("21000"),
                          categoria_id=cat.id, impuesto_id=imp.id,
                          vendido_por_peso=True, unidad="kg"))
    repo.guardar(Producto(codigo_barras="7700000000001", nombre="Manzana",
                          precio=Decimal("32000"), costo=Decimal("21000"),
                          categoria_id=cat.id, impuesto_id=imp.id,
                          vendido_por_peso=True, unidad="kg"))
    assert len(repo.listar()) == 2


def test_fk_invalida_es_rechazada(conn):
    import sqlite3
    with pytest.raises(sqlite3.IntegrityError):
        RepositorioProductosSQLite(conn).guardar(
            Producto(codigo_barras="x", nombre="huerfano", precio=Decimal("1"),
                     categoria_id=999))
