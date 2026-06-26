from datetime import datetime
from decimal import Decimal

from core.entidades import (
    CajaSesion, Categoria, Devolucion, Impuesto, LineaDevolucion, LineaVenta, Pago, Producto, Venta,
)
from inventario.repositorio_sqlite import (
    RepositorioCategoriasSQLite,
    RepositorioImpuestosSQLite,
    RepositorioProductosSQLite,
)
from ventas.repositorio_sqlite import (
    RepositorioCajaSesionesSQLite,
    RepositorioDevolucionesSQLite,
    RepositorioVentasSQLite,
)


def _seed_producto(conn):
    cat = RepositorioCategoriasSQLite(conn).guardar(Categoria(nombre="Bebidas"))
    imp = RepositorioImpuestosSQLite(conn).guardar(Impuesto(nombre="IVA", tarifa=Decimal("0.19")))
    return RepositorioProductosSQLite(conn).guardar(
        Producto(codigo_barras="B", nombre="Gaseosa", precio=Decimal("3500"),
                 categoria_id=cat.id, impuesto_id=imp.id))


def _sesion(conn, fecha=datetime(2026, 6, 25, 9, 0)):
    return RepositorioCajaSesionesSQLite(conn).abrir(
        CajaSesion(apertura_fecha=fecha, monto_inicial=Decimal("0")))


def _venta(conn, sesion_id, producto_id, fecha, pagos, estado="pagada"):
    linea = LineaVenta(producto_id=producto_id, descripcion="Gaseosa",
                       cantidad_o_peso=Decimal("2"), precio_unit=Decimal("3500"),
                       impuesto=Decimal("1118"), subtotal=Decimal("7000"))
    venta = Venta(fecha=fecha, lineas=(linea,), total=Decimal("7000"),
                  total_impuestos=Decimal("1118"), caja_sesion_id=sesion_id, estado=estado)
    return RepositorioVentasSQLite(conn).guardar(venta, pagos)


def test_ventas_en_filtra_rango_y_excluye_anuladas(conn):
    prod = _seed_producto(conn)
    s = _sesion(conn)
    _venta(conn, s.id, prod.id, datetime(2026, 6, 24, 10, 0),
           [Pago(medio_pago_id=1, monto=Decimal("7000"))])                       # fuera (24)
    dentro = _venta(conn, s.id, prod.id, datetime(2026, 6, 25, 10, 0),
                    [Pago(medio_pago_id=1, monto=Decimal("7000"))])              # dentro
    _venta(conn, s.id, prod.id, datetime(2026, 6, 25, 11, 0),
           [Pago(medio_pago_id=1, monto=Decimal("7000"))], estado="anulada")

    repo = RepositorioVentasSQLite(conn)
    ventas = repo.ventas_en(datetime(2026, 6, 25, 0, 0), datetime(2026, 6, 26, 0, 0))
    assert [v.id for v in ventas] == [dentro.id]
    assert ventas[0].lineas[0].subtotal == Decimal("7000")   # rehidratada con líneas


def test_pagos_en_de_ventas_no_anuladas(conn):
    prod = _seed_producto(conn)
    s = _sesion(conn)
    _venta(conn, s.id, prod.id, datetime(2026, 6, 25, 10, 0),
           [Pago(medio_pago_id=1, monto=Decimal("4000")),
            Pago(medio_pago_id=2, monto=Decimal("3000"))])
    _venta(conn, s.id, prod.id, datetime(2026, 6, 25, 12, 0),
           [Pago(medio_pago_id=1, monto=Decimal("7000"))], estado="anulada")

    pagos = RepositorioVentasSQLite(conn).pagos_en(
        datetime(2026, 6, 25, 0, 0), datetime(2026, 6, 26, 0, 0))
    assert sorted((p.medio_pago_id, p.monto) for p in pagos) == [
        (1, Decimal("4000")), (2, Decimal("3000"))]


def test_ventas_de_sesion(conn):
    prod = _seed_producto(conn)
    s1 = _sesion(conn)
    v1 = _venta(conn, s1.id, prod.id, datetime(2026, 6, 25, 10, 0),
                [Pago(medio_pago_id=1, monto=Decimal("7000"))])
    repo = RepositorioVentasSQLite(conn)
    assert [v.id for v in repo.ventas_de_sesion(s1.id)] == [v1.id]


def test_devoluciones_en_y_de_sesion(conn):
    prod = _seed_producto(conn)
    s = _sesion(conn)
    venta = _venta(conn, s.id, prod.id, datetime(2026, 6, 25, 10, 0),
                   [Pago(medio_pago_id=1, monto=Decimal("7000"))])
    linea_id = RepositorioVentasSQLite(conn).por_id(venta.id).lineas[0].id
    dev = Devolucion(
        venta_id=venta.id, fecha=datetime(2026, 6, 25, 12, 0),
        lineas=(LineaDevolucion(producto_id=prod.id, cantidad_o_peso=Decimal("1"),
                                impuesto=Decimal("0"), subtotal=Decimal("3500"),
                                venta_linea_id=linea_id),),
        total=Decimal("3500"), total_impuestos=Decimal("0"),
        reembolsos=(Pago(medio_pago_id=1, monto=Decimal("3500")),), caja_sesion_id=s.id)
    RepositorioDevolucionesSQLite(conn).guardar(dev)

    repo = RepositorioDevolucionesSQLite(conn)
    en_rango = repo.devoluciones_en(datetime(2026, 6, 25, 0, 0), datetime(2026, 6, 26, 0, 0))
    assert len(en_rango) == 1
    assert en_rango[0].total == Decimal("3500")
    assert en_rango[0].reembolsos[0].monto == Decimal("3500")   # rehidratada completa
    assert [d.id for d in repo.de_sesion(s.id)] == [en_rango[0].id]
    # fuera de rango
    assert repo.devoluciones_en(datetime(2026, 6, 26, 0, 0), datetime(2026, 6, 27, 0, 0)) == []
