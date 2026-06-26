from datetime import datetime
from decimal import Decimal

import pytest

from core.entidades import Devolucion, ItemDevolucion, LineaDevolucion, Pago, Venta


def test_item_devolucion_cantidad_no_positiva_falla():
    with pytest.raises(ValueError):
        ItemDevolucion(venta_linea_id=1, cantidad_o_peso=Decimal("0"))


def test_linea_devolucion_minima():
    l = LineaDevolucion(producto_id=1, cantidad_o_peso=Decimal("1.5"),
                        impuesto=Decimal("0"), subtotal=Decimal("6000"))
    assert l.devolucion_id is None
    assert l.id is None


def test_linea_devolucion_valores_negativos_fallan():
    with pytest.raises(ValueError):
        LineaDevolucion(producto_id=1, cantidad_o_peso=Decimal("1"),
                        impuesto=Decimal("0"), subtotal=Decimal("-1"))
    with pytest.raises(ValueError):
        LineaDevolucion(producto_id=1, cantidad_o_peso=Decimal("0"),
                        impuesto=Decimal("0"), subtotal=Decimal("0"))


def test_devolucion_minima_estado_emitida():
    d = Devolucion(
        venta_id=77, fecha=datetime(2026, 6, 25, 11, 0),
        lineas=(LineaDevolucion(producto_id=1, cantidad_o_peso=Decimal("1"),
                                impuesto=Decimal("0"), subtotal=Decimal("3500")),),
        total=Decimal("3500"), total_impuestos=Decimal("0"),
        reembolsos=(Pago(medio_pago_id=1, monto=Decimal("3500")),))
    assert d.estado == "emitida"
    assert d.caja_sesion_id is None
    assert d.id is None


def test_devolucion_estado_invalido_falla():
    with pytest.raises(ValueError):
        Devolucion(venta_id=77, fecha=datetime(2026, 6, 25, 11, 0), lineas=(),
                   total=Decimal("0"), total_impuestos=Decimal("0"),
                   reembolsos=(), estado="pendiente")


def test_venta_admite_estados_de_devolucion():
    from core.entidades import LineaVenta
    linea = LineaVenta(producto_id=1, descripcion="Gaseosa", cantidad_o_peso=Decimal("2"),
                       precio_unit=Decimal("3500"), impuesto=Decimal("1118"), subtotal=Decimal("7000"))
    for estado in ("devuelta_parcial", "devuelta"):
        v = Venta(fecha=datetime(2026, 6, 25, 10, 0), lineas=(linea,),
                  total=Decimal("7000"), total_impuestos=Decimal("1118"), estado=estado)
        assert v.estado == estado
