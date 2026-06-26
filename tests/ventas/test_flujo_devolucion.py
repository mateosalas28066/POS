from datetime import datetime
from decimal import Decimal

from core.entidades import Categoria, Impuesto, ItemDevolucion, MovimientoInventario, Pago, Producto
from core.servicio_caja import ServicioCaja
from core.servicio_venta import ServicioDevolucion, ServicioRegistroVenta, ServicioVenta
from inventario.repositorio_sqlite import (
    RepositorioCategoriasSQLite,
    RepositorioImpuestosSQLite,
    RepositorioInventarioSQLite,
    RepositorioProductosSQLite,
)
from ventas.repositorio_sqlite import (
    RepositorioCajaSesionesSQLite,
    RepositorioDevolucionesSQLite,
    RepositorioVentasSQLite,
)


def _seed(conn):
    cat = RepositorioCategoriasSQLite(conn).guardar(Categoria(nombre="Bebidas"))
    iva = RepositorioImpuestosSQLite(conn).guardar(Impuesto(nombre="IVA", tarifa=Decimal("0.19")))
    gaseosa = RepositorioProductosSQLite(conn).guardar(
        Producto(codigo_barras="B", nombre="Gaseosa", precio=Decimal("3500"),
                 categoria_id=cat.id, impuesto_id=iva.id))
    inv = RepositorioInventarioSQLite(conn)
    inv.registrar(MovimientoInventario(producto_id=gaseosa.id, tipo="entrada",
                                       cantidad=Decimal("10"), fecha=datetime(2026, 6, 25, 8, 0)))
    return gaseosa, inv


def test_devolucion_parcial_y_luego_total(conn):
    gaseosa, inv = _seed(conn)
    ventas = RepositorioVentasSQLite(conn)
    devoluciones = RepositorioDevolucionesSQLite(conn)
    caja = ServicioCaja(RepositorioCajaSesionesSQLite(conn), ventas)
    registro = ServicioRegistroVenta(ventas, inv)
    servicio_dev = ServicioDevolucion(ventas, devoluciones, inv)

    sesion = caja.abrir(fecha=datetime(2026, 6, 25, 9, 0), monto_inicial=Decimal("100000"))

    # Vender 2 gaseosas en efectivo (subtotal 7000)
    s = ServicioVenta(RepositorioProductosSQLite(conn), RepositorioImpuestosSQLite(conn))
    s.agregar("B", cantidad=2)
    venta = s.confirmar(fecha=datetime(2026, 6, 25, 10, 0), caja_sesion_id=sesion.id)
    guardada = registro.registrar(venta, [Pago(medio_pago_id=1, monto=Decimal("7000"))])
    assert inv.stock_de(gaseosa.id) == Decimal("8")

    linea_id = ventas.por_id(guardada.id).lineas[0].id

    # Devolver 1 de 2 (reembolso 3500 efectivo)
    servicio_dev.devolver(
        guardada.id, [ItemDevolucion(venta_linea_id=linea_id, cantidad_o_peso=Decimal("1"))],
        [Pago(medio_pago_id=1, monto=Decimal("3500"))],
        fecha=datetime(2026, 6, 25, 11, 0), caja_sesion_id=sesion.id)

    assert inv.stock_de(gaseosa.id) == Decimal("9")                  # repuesto 1
    assert ventas.por_id(guardada.id).estado == "devuelta_parcial"
    arqueo_parcial = caja.arqueo(sesion.id, Decimal("103500"))
    assert arqueo_parcial.efectivo_ventas == Decimal("3500")        # 7000 - 3500 reembolsado
    assert arqueo_parcial.esperado == Decimal("103500")             # base 100000 + 3500
    assert arqueo_parcial.diferencia == Decimal("0")

    # Devolver el restante 1 (reembolso 3500 efectivo) -> venta devuelta
    servicio_dev.devolver(
        guardada.id, [ItemDevolucion(venta_linea_id=linea_id, cantidad_o_peso=Decimal("1"))],
        [Pago(medio_pago_id=1, monto=Decimal("3500"))],
        fecha=datetime(2026, 6, 25, 11, 30), caja_sesion_id=sesion.id)

    assert inv.stock_de(gaseosa.id) == Decimal("10")                # stock totalmente repuesto
    assert ventas.por_id(guardada.id).estado == "devuelta"
    assert len(devoluciones.de_venta(guardada.id)) == 2

    # Arqueo: efectivo neto de la venta = 0 (7000 cobrado - 7000 reembolsado)
    cerrada, arqueo = caja.cerrar(sesion_id=sesion.id, fecha=datetime(2026, 6, 25, 20, 0),
                                  monto_contado=Decimal("100000"))
    assert arqueo.efectivo_ventas == Decimal("0")
    assert arqueo.esperado == Decimal("100000")
    assert arqueo.diferencia == Decimal("0")
    assert cerrada.estado == "cerrada"
