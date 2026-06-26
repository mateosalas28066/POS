from decimal import Decimal

from dataclasses import replace

from core.entidades import Categoria, Impuesto, Producto
from inventario.repositorio_sqlite import (
    RepositorioCategoriasSQLite, RepositorioImpuestosSQLite, RepositorioProductosSQLite,
)


def test_categorias_listar_y_por_id(conn):
    repo = RepositorioCategoriasSQLite(conn)
    a = repo.guardar(Categoria(nombre="Carnes"))
    b = repo.guardar(Categoria(nombre="Frutas"))
    nombres = [c.nombre for c in repo.listar()]
    assert nombres == ["Carnes", "Frutas"]
    assert repo.por_id(a.id).nombre == "Carnes"
    assert repo.por_id(999) is None


def test_impuestos_listar(conn):
    repo = RepositorioImpuestosSQLite(conn)
    repo.guardar(Impuesto(nombre="IVA 0", tarifa=Decimal("0")))
    repo.guardar(Impuesto(nombre="IVA 19", tarifa=Decimal("0.19")))
    assert [i.nombre for i in repo.listar()] == ["IVA 0", "IVA 19"]


def test_productos_actualizar(conn):
    repo = RepositorioProductosSQLite(conn)
    p = repo.guardar(Producto(codigo_barras="B1", nombre="Manzana", precio=Decimal("1000")))
    modificado = repo.actualizar(replace(p, nombre="Manzana Roja", precio=Decimal("1200")))
    assert modificado.nombre == "Manzana Roja"
    leido = repo.por_id(p.id)
    assert leido.nombre == "Manzana Roja"
    assert leido.precio == Decimal("1200")
