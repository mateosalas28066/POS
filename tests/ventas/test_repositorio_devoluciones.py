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


def _venta_guardada(conn, sesion_id, producto_id, pagos):
    linea = LineaVenta(producto_id=producto_id, descripcion="Gaseosa",
                       cantidad_o_peso=Decimal("2"), precio_unit=Decimal("3500"),
                       impuesto=Decimal("1118"), subtotal=Decimal("7000"))
    venta = Venta(fecha=datetime(2026, 6, 25, 10, 0), lineas=(linea,),
                  total=Decimal("7000"), total_impuestos=Decimal("1118"), caja_sesion_id=sesion_id)
    return RepositorioVentasSQLite(conn).guardar(venta, pagos)


def _devolucion(conn, venta_id, venta_linea_id, producto_id, sesion_id, cantidad, monto):
    linea = LineaDevolucion(producto_id=producto_id, cantidad_o_peso=cantidad,
                            impuesto=Decimal("0"), subtotal=monto, venta_linea_id=venta_linea_id)
    dev = Devolucion(venta_id=venta_id, fecha=datetime(2026, 6, 25, 12, 0), lineas=(linea,),
                     total=monto, total_impuestos=Decimal("0"),
                     reembolsos=(Pago(medio_pago_id=1, monto=monto),), caja_sesion_id=sesion_id)
    return RepositorioDevolucionesSQLite(conn).guardar(dev)


def test_guardar_y_leer_devolucion(conn):
    prod = _seed_producto(conn)
    sesion = RepositorioCajaSesionesSQLite(conn).abrir(
        CajaSesion(apertura_fecha=datetime(2026, 6, 25, 9, 0), monto_inicial=Decimal("0")))
    venta = _venta_guardada(conn, sesion.id, prod.id, [Pago(medio_pago_id=1, monto=Decimal("7000"))])
    linea_id = RepositorioVentasSQLite(conn).por_id(venta.id).lineas[0].id

    guardada = _devolucion(conn, venta.id, linea_id, prod.id, sesion.id, Decimal("1"), Decimal("3500"))
    assert guardada.id is not None

    leida = RepositorioDevolucionesSQLite(conn).por_id(guardada.id)
    assert leida.venta_id == venta.id
    assert leida.total == Decimal("3500")
    assert leida.lineas[0].cantidad_o_peso == Decimal("1")
    assert leida.reembolsos[0].monto == Decimal("3500")
    assert leida.caja_sesion_id == sesion.id


def test_de_venta_y_devuelto_por_linea(conn):
    prod = _seed_producto(conn)
    sesion = RepositorioCajaSesionesSQLite(conn).abrir(
        CajaSesion(apertura_fecha=datetime(2026, 6, 25, 9, 0), monto_inicial=Decimal("0")))
    venta = _venta_guardada(conn, sesion.id, prod.id, [Pago(medio_pago_id=1, monto=Decimal("7000"))])
    linea_id = RepositorioVentasSQLite(conn).por_id(venta.id).lineas[0].id
    _devolucion(conn, venta.id, linea_id, prod.id, sesion.id, Decimal("1"), Decimal("3500"))

    repo = RepositorioDevolucionesSQLite(conn)
    assert len(repo.de_venta(venta.id)) == 1
    assert repo.devuelto_por_linea(venta.id) == {linea_id: Decimal("1")}


def test_totales_por_medio_netea_reembolso_misma_sesion(conn):
    prod = _seed_producto(conn)
    sesion = RepositorioCajaSesionesSQLite(conn).abrir(
        CajaSesion(apertura_fecha=datetime(2026, 6, 25, 9, 0), monto_inicial=Decimal("0")))
    venta = _venta_guardada(conn, sesion.id, prod.id, [Pago(medio_pago_id=1, monto=Decimal("7000"))])
    linea_id = RepositorioVentasSQLite(conn).por_id(venta.id).lineas[0].id
    _devolucion(conn, venta.id, linea_id, prod.id, sesion.id, Decimal("1"), Decimal("3500"))

    # ingreso 7000 efectivo - reembolso 3500 efectivo = 3500 neto
    assert RepositorioVentasSQLite(conn).totales_por_medio(sesion.id) == {1: Decimal("3500")}


def test_reembolso_afecta_la_sesion_del_reembolso_no_la_de_la_venta(conn):
    from dataclasses import replace
    prod = _seed_producto(conn)
    sesiones = RepositorioCajaSesionesSQLite(conn)
    s1 = sesiones.abrir(CajaSesion(apertura_fecha=datetime(2026, 6, 25, 9, 0),
                                   monto_inicial=Decimal("0")))
    venta = _venta_guardada(conn, s1.id, prod.id, [Pago(medio_pago_id=1, monto=Decimal("7000"))])
    linea_id = RepositorioVentasSQLite(conn).por_id(venta.id).lineas[0].id
    # se cierra s1 y se abre s2; el reembolso ocurre en s2
    sesiones.cerrar(replace(
        s1, cierre_fecha=datetime(2026, 6, 25, 20, 0), monto_contado=Decimal("7000"), estado="cerrada"))
    s2 = sesiones.abrir(CajaSesion(apertura_fecha=datetime(2026, 6, 26, 9, 0),
                                   monto_inicial=Decimal("0")))
    _devolucion(conn, venta.id, linea_id, prod.id, s2.id, Decimal("1"), Decimal("3500"))

    ventas = RepositorioVentasSQLite(conn)
    assert ventas.totales_por_medio(s1.id) == {1: Decimal("7000")}   # venta intacta en s1
    assert ventas.totales_por_medio(s2.id) == {1: Decimal("-3500")}  # egreso en s2


def test_marcar_estado_actualiza_la_venta(conn):
    prod = _seed_producto(conn)
    sesion = RepositorioCajaSesionesSQLite(conn).abrir(
        CajaSesion(apertura_fecha=datetime(2026, 6, 25, 9, 0), monto_inicial=Decimal("0")))
    venta = _venta_guardada(conn, sesion.id, prod.id, [Pago(medio_pago_id=1, monto=Decimal("7000"))])
    repo = RepositorioVentasSQLite(conn)
    repo.marcar_estado(venta.id, "devuelta_parcial")
    assert repo.por_id(venta.id).estado == "devuelta_parcial"
