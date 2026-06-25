from datetime import datetime
from decimal import Decimal

from core.calculos import calcular_vuelto
from core.entidades import Categoria, Impuesto, Pago, Producto
from core.servicio_venta import ServicioVenta
from inventario.repositorio_sqlite import (
    RepositorioCategoriasSQLite,
    RepositorioImpuestosSQLite,
    RepositorioProductosSQLite,
)
from ventas.repositorio_sqlite import RepositorioVentasSQLite


def _seed(conn):
    cat = RepositorioCategoriasSQLite(conn).guardar(Categoria(nombre="Surtido"))
    imp = RepositorioImpuestosSQLite(conn)
    iva = imp.guardar(Impuesto(nombre="IVA", tarifa=Decimal("0.19")))
    excl = imp.guardar(Impuesto(nombre="Excluido", tarifa=Decimal("0")))
    prod = RepositorioProductosSQLite(conn)
    prod.guardar(Producto(codigo_barras="B", nombre="Gaseosa", precio=Decimal("3500"),
                          categoria_id=cat.id, impuesto_id=iva.id))
    prod.guardar(Producto(codigo_barras="A", nombre="Manzana", precio=Decimal("4000"),
                          categoria_id=cat.id, impuesto_id=excl.id,
                          vendido_por_peso=True, unidad="kg"))


def test_venta_simple_calcula_cobra_y_persiste(conn):
    _seed(conn)
    servicio = ServicioVenta(RepositorioProductosSQLite(conn), RepositorioImpuestosSQLite(conn))

    servicio.agregar("B", cantidad=2)              # 2 x 3500 = 7000, IVA contenido 1118
    servicio.agregar("A", peso_kg=Decimal("1.5"))  # 1.5kg x 4000 = 6000, excluido

    assert servicio.total == Decimal("13000")
    assert servicio.total_impuestos == Decimal("1118")

    venta = servicio.confirmar(fecha=datetime(2026, 6, 25, 11, 0))
    vuelto = calcular_vuelto(venta.total, Decimal("20000"))
    assert vuelto == Decimal("7000")

    repo = RepositorioVentasSQLite(conn)
    guardada = repo.guardar(venta, [Pago(medio_pago_id=1, monto=Decimal("20000"))])

    releida = repo.por_id(guardada.id)
    assert releida.total == Decimal("13000")
    assert releida.total_impuestos == Decimal("1118")
    assert len(releida.lineas) == 2
    assert repo.pagos_de(guardada.id)[0].monto == Decimal("20000")
