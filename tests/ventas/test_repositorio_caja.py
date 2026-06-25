# tests/ventas/test_repositorio_caja.py
from dataclasses import replace
from datetime import datetime
from decimal import Decimal

from core.entidades import (
    CajaSesion, Categoria, Impuesto, LineaVenta, Pago, Producto, Venta,
)
from inventario.repositorio_sqlite import (
    RepositorioCategoriasSQLite,
    RepositorioImpuestosSQLite,
    RepositorioProductosSQLite,
)
from ventas.repositorio_sqlite import (
    RepositorioCajaSesionesSQLite,
    RepositorioVentasSQLite,
)


def test_caja_sesion_abrir_cerrar_y_abierta(conn):
    repo = RepositorioCajaSesionesSQLite(conn)
    assert repo.abierta() is None

    s = repo.abrir(CajaSesion(apertura_fecha=datetime(2026, 6, 25, 9, 0),
                              monto_inicial=Decimal("100000")))
    assert s.id is not None
    assert repo.abierta().id == s.id

    repo.cerrar(replace(s, cierre_fecha=datetime(2026, 6, 25, 20, 0),
                        monto_contado=Decimal("113000"), estado="cerrada"))
    assert repo.abierta() is None

    leida = repo.por_id(s.id)
    assert leida.estado == "cerrada"
    assert leida.monto_inicial == Decimal("100000")
    assert leida.monto_contado == Decimal("113000")
    assert leida.cierre_fecha == datetime(2026, 6, 25, 20, 0)


def test_por_id_inexistente_es_none(conn):
    assert RepositorioCajaSesionesSQLite(conn).por_id(999) is None


def _venta_en_sesion(conn, sesion_id, pagos, producto_id):
    linea = LineaVenta(producto_id=producto_id, descripcion="Gaseosa",
                       cantidad_o_peso=Decimal("2"), precio_unit=Decimal("3500"),
                       impuesto=Decimal("1118"), subtotal=Decimal("7000"))
    venta = Venta(fecha=datetime(2026, 6, 25, 10, 0), lineas=(linea,),
                  total=Decimal("7000"), total_impuestos=Decimal("1118"),
                  caja_sesion_id=sesion_id)
    RepositorioVentasSQLite(conn).guardar(venta, pagos)


def test_totales_por_medio_suma_pagos_de_la_sesion(conn):
    cat = RepositorioCategoriasSQLite(conn).guardar(Categoria(nombre="Bebidas"))
    imp = RepositorioImpuestosSQLite(conn).guardar(Impuesto(nombre="IVA", tarifa=Decimal("0.19")))
    prod = RepositorioProductosSQLite(conn).guardar(
        Producto(codigo_barras="B", nombre="Gaseosa", precio=Decimal("3500"),
                 categoria_id=cat.id, impuesto_id=imp.id))
    sesion = RepositorioCajaSesionesSQLite(conn).abrir(
        CajaSesion(apertura_fecha=datetime(2026, 6, 25, 9, 0), monto_inicial=Decimal("0")))

    _venta_en_sesion(conn, sesion.id, [Pago(medio_pago_id=1, monto=Decimal("7000"))], prod.id)
    _venta_en_sesion(conn, sesion.id,
                     [Pago(medio_pago_id=1, monto=Decimal("7000")),
                      Pago(medio_pago_id=2, monto=Decimal("3000"))], prod.id)

    totales = RepositorioVentasSQLite(conn).totales_por_medio(sesion.id)
    assert totales == {1: Decimal("14000"), 2: Decimal("3000")}


def test_totales_por_medio_sesion_sin_ventas_es_vacio(conn):
    assert RepositorioVentasSQLite(conn).totales_por_medio(999) == {}
