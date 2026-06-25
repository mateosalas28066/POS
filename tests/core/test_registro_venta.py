from dataclasses import replace
from datetime import datetime
from decimal import Decimal
from core.entidades import LineaVenta, Pago, Venta
from core.servicio_venta import ServicioRegistroVenta, salidas_de_venta

def _venta(id=None) -> Venta:
    lineas = (
        LineaVenta(producto_id=1, descripcion="Gaseosa", cantidad_o_peso=Decimal("2"),
                   precio_unit=Decimal("3500"), impuesto=Decimal("1118"), subtotal=Decimal("7000")),
        LineaVenta(producto_id=2, descripcion="Manzana", cantidad_o_peso=Decimal("1.5"),
                   precio_unit=Decimal("4000"), impuesto=Decimal("0"), subtotal=Decimal("6000")),
    )
    return Venta(fecha=datetime(2026, 6, 25, 10, 0), lineas=lineas,
                 total=Decimal("13000"), total_impuestos=Decimal("1118"), id=id)

class _FakeVentas:
    def __init__(self) -> None:
        self.guardada = None
    def guardar(self, venta: Venta, pagos: list[Pago]) -> Venta:
        self.guardada = replace(venta, id=77)
        self.pagos = pagos
        return self.guardada

class _FakeInventario:
    def __init__(self) -> None:
        self.movimientos = []
    def registrar(self, m):
        self.movimientos.append(m)
        return m

def test_salidas_de_venta_una_por_linea():
    salidas = salidas_de_venta(_venta(id=77))
    assert len(salidas) == 2
    assert all(m.tipo == "salida" for m in salidas)
    assert salidas[0].producto_id == 1
    assert salidas[0].cantidad == Decimal("2")
    assert salidas[1].cantidad == Decimal("1.5")
    assert salidas[0].ref == "venta:77"

def test_registrar_persiste_y_descuenta_inventario():
    ventas, inventario = _FakeVentas(), _FakeInventario()
    servicio = ServicioRegistroVenta(ventas, inventario)
    guardada = servicio.registrar(_venta(), [Pago(medio_pago_id=1, monto=Decimal("13000"))])
    assert guardada.id == 77
    assert [m.producto_id for m in inventario.movimientos] == [1, 2]
    assert [m.cantidad for m in inventario.movimientos] == [Decimal("2"), Decimal("1.5")]
    assert all(m.ref == "venta:77" for m in inventario.movimientos)
