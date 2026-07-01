# tests/inventario/test_repositorio_promociones.py
from datetime import datetime
from decimal import Decimal

import pytest

from core.entidades import Promocion
from inventario.db import aplicar_migraciones, conectar
from inventario.repositorio_sqlite import RepositorioPromocionesSQLite


@pytest.fixture
def conn():
    c = conectar()
    aplicar_migraciones(c)
    c.execute("INSERT INTO productos (codigo_barras, nombre, precio, costo, "
              "vendido_por_peso, unidad) VALUES ('1','Lomo','20000','0',1,'kg')")
    c.commit()
    yield c
    c.close()


def _promo(**kw):
    base = dict(producto_id=1, tipo_valor="precio_fijo", valor=Decimal("8000"),
                tipo_duracion="manual")
    base.update(kw)
    return Promocion(**base)


def test_guardar_y_por_id_roundtrip(conn):
    repo = RepositorioPromocionesSQLite(conn)
    guardada = repo.guardar(_promo())
    leida = repo.por_id(guardada.id)
    assert leida.valor == Decimal("8000")
    assert leida.tipo_duracion == "manual"
    assert leida.activa is True


def test_tiempo_roundtrip_conserva_fechas(conn):
    repo = RepositorioPromocionesSQLite(conn)
    p = repo.guardar(_promo(tipo_duracion="tiempo",
                            desde=datetime(2026, 7, 1, 8, 0),
                            hasta=datetime(2026, 7, 1, 20, 0)))
    leida = repo.por_id(p.id)
    assert leida.desde == datetime(2026, 7, 1, 8, 0)
    assert leida.hasta == datetime(2026, 7, 1, 20, 0)


def test_activa_por_producto_solo_devuelve_activa(conn):
    repo = RepositorioPromocionesSQLite(conn)
    p = repo.guardar(_promo())
    assert repo.activa_por_producto(1).id == p.id
    repo.actualizar(repo.por_id(p.id).__class__(**{**repo.por_id(p.id).__dict__, "activa": False}))
    assert repo.activa_por_producto(1) is None


def test_unidades_roundtrip(conn):
    repo = RepositorioPromocionesSQLite(conn)
    p = repo.guardar(_promo(tipo_duracion="unidades", unidades_limite=Decimal("5")))
    leida = repo.por_id(p.id)
    assert leida.unidades_limite == Decimal("5")
    assert leida.unidades_restantes == Decimal("5")
