from datetime import datetime
from decimal import Decimal
from core.entidades import Categoria, Impuesto, MovimientoInventario, Pago, Producto
from core.servicio_caja import ServicioCaja
from core.servicio_venta import ServicioRegistroVenta, ServicioVenta
from inventario.repositorio_sqlite import (
    RepositorioCategoriasSQLite,
    RepositorioImpuestosSQLite,
    RepositorioInventarioSQLite,
    RepositorioProductosSQLite,
)
from ventas.repositorio_sqlite import (
    RepositorioCajaSesionesSQLite,
    RepositorioVentasSQLite,
)

def _seed(conn):
    cat = RepositorioCategoriasSQLite(conn).guardar(Categoria(nombre="Surtido"))
    imp = RepositorioImpuestosSQLite(conn)
    iva = imp.guardar(Impuesto(nombre="IVA", tarifa=Decimal("0.19")))
    excl = imp.guardar(Impuesto(nombre="Excluido", tarifa=Decimal("0")))
    prods = RepositorioProductosSQLite(conn)
    gaseosa = prods.guardar(Producto(codigo_barras="B", nombre="Gaseosa", precio=Decimal("3500"),
                                     categoria_id=cat.id, impuesto_id=iva.id))
    manzana = prods.guardar(Producto(codigo_barras="A", nombre="Manzana", precio=Decimal("4000"),
                                     categoria_id=cat.id, impuesto_id=excl.id,
                                     vendido_por_peso=True, unidad="kg"))
    inv = RepositorioInventarioSQLite(conn)
    inv.registrar(MovimientoInventario(producto_id=gaseosa.id, tipo="entrada",
                                       cantidad=Decimal("10"), fecha=datetime(2026, 6, 25, 8, 0)))
    inv.registrar(MovimientoInventario(producto_id=manzana.id, tipo="entrada",
                                       cantidad=Decimal("5"), fecha=datetime(2026, 6, 25, 8, 0)))
    return gaseosa, manzana, inv

def test_cierre_de_caja_cuadra_efectivo_y_descuenta_inventario(conn):
    gaseosa, manzana, inv = _seed(conn)
    sesiones = RepositorioCajaSesionesSQLite(conn)
    ventas = RepositorioVentasSQLite(conn)
    caja = ServicioCaja(sesiones, ventas)
    registro = ServicioRegistroVenta(ventas, inv)

    sesion = caja.abrir(fecha=datetime(2026, 6, 25, 9, 0), monto_inicial=Decimal("100000"))

    def vender(codigo, *, pago_medio, pago_monto, **kw):
        s = ServicioVenta(RepositorioProductosSQLite(conn), RepositorioImpuestosSQLite(conn))
        s.agregar(codigo, **kw)
        venta = s.confirmar(fecha=datetime(2026, 6, 25, 10, 0), caja_sesion_id=sesion.id)
        registro.registrar(venta, [Pago(medio_pago_id=pago_medio, monto=pago_monto)])

    vender("B", cantidad=2, pago_medio=1, pago_monto=Decimal("7000"))
    vender("A", peso_kg=Decimal("1.5"), pago_medio=1, pago_monto=Decimal("6000"))
    vender("B", cantidad=1, pago_medio=2, pago_monto=Decimal("3500"))

    cerrada, arqueo = caja.cerrar(sesion_id=sesion.id, fecha=datetime(2026, 6, 25, 20, 0),
                                  monto_contado=Decimal("112000"))

    assert arqueo.efectivo_ventas == Decimal("13000")
    assert arqueo.esperado == Decimal("113000")
    assert arqueo.diferencia == Decimal("-1000")
    assert cerrada.estado == "cerrada"
    assert cerrada.monto_contado == Decimal("112000")

    assert ventas.totales_por_medio(sesion.id) == {1: Decimal("13000"), 2: Decimal("3500")}

    assert inv.stock_de(gaseosa.id) == Decimal("7")
    assert inv.stock_de(manzana.id) == Decimal("3.5")
