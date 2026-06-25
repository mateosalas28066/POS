from datetime import datetime
from decimal import Decimal
from core.entidades import LineaVenta, Venta
from core.servicio_venta import entradas_de_anulacion


def _venta(id=77) -> Venta:
    lineas = (
        LineaVenta(producto_id=1, descripcion="Gaseosa", cantidad_o_peso=Decimal("2"),
                   precio_unit=Decimal("3500"), impuesto=Decimal("1118"), subtotal=Decimal("7000")),
        LineaVenta(producto_id=2, descripcion="Manzana", cantidad_o_peso=Decimal("1.5"),
                   precio_unit=Decimal("4000"), impuesto=Decimal("0"), subtotal=Decimal("6000")),
    )
    return Venta(fecha=datetime(2026, 6, 25, 10, 0), lineas=lineas,
                 total=Decimal("13000"), total_impuestos=Decimal("1118"), id=id)


def test_entradas_de_anulacion_una_por_linea():
    entradas = entradas_de_anulacion(_venta(id=77))
    assert len(entradas) == 2
    assert all(m.tipo == "entrada" for m in entradas)
    assert entradas[0].producto_id == 1
    assert entradas[0].cantidad == Decimal("2")
    assert entradas[1].cantidad == Decimal("1.5")
    assert all(m.ref == "anulacion:77" for m in entradas)
