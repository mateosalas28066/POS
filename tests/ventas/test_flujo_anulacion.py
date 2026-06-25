from datetime import datetime
from decimal import Decimal
from core.entidades import Categoria, Impuesto, MovimientoInventario, Pago, Producto
from core.servicio_venta import ServicioAnulacion, ServicioRegistroVenta, ServicioVenta
from inventario.repositorio_sqlite import (
    RepositorioCategoriasSQLite,
    RepositorioImpuestosSQLite,
    RepositorioInventarioSQLite,
    RepositorioProductosSQLite,
)
from ventas.repositorio_sqlite import RepositorioVentasSQLite


def _seed(conn):
    cat = RepositorioCategoriasSQLite(conn).guardar(Categoria(nombre="Surtido"))
    iva = RepositorioImpuestosSQLite(conn).guardar(Impuesto(nombre="IVA", tarifa=Decimal("0.19")))
    prods = RepositorioProductosSQLite(conn)
    gaseosa = prods.guardar(Producto(codigo_barras="B", nombre="Gaseosa", precio=Decimal("3500"),
                                     categoria_id=cat.id, impuesto_id=iva.id))
    inv = RepositorioInventarioSQLite(conn)
    inv.registrar(MovimientoInventario(producto_id=gaseosa.id, tipo="entrada",
                                       cantidad=Decimal("10"), fecha=datetime(2026, 6, 25, 8, 0)))
    # Crear sesión de caja para las ventas
    conn.execute(
        "INSERT INTO caja_sesiones (id, apertura_fecha, monto_inicial, estado) "
        "VALUES (?, ?, ?, ?)",
        (1, datetime(2026, 6, 25, 9, 0).isoformat(), Decimal("100000"), "abierta")
    )
    conn.commit()
    return gaseosa, inv


def test_anular_repone_stock_y_sale_del_arqueo(conn):
    gaseosa, inv = _seed(conn)
    ventas = RepositorioVentasSQLite(conn)
    registro = ServicioRegistroVenta(ventas, inv)

    s = ServicioVenta(RepositorioProductosSQLite(conn), RepositorioImpuestosSQLite(conn))
    s.agregar("B", cantidad=2)
    venta = s.confirmar(fecha=datetime(2026, 6, 25, 10, 0), caja_sesion_id=1)
    guardada = registro.registrar(venta, [Pago(medio_pago_id=1, monto=Decimal("7000"))])

    assert inv.stock_de(gaseosa.id) == Decimal("8")
    assert ventas.totales_por_medio(1) == {1: Decimal("7000")}

    anulada = ServicioAnulacion(ventas, inv).anular(guardada.id)

    assert anulada.estado == "anulada"
    assert inv.stock_de(gaseosa.id) == Decimal("10")   # stock repuesto
    assert ventas.totales_por_medio(1) == {}           # ya no cuenta en el arqueo
