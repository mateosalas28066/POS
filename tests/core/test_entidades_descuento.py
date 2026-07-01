from datetime import datetime
from decimal import Decimal

import pytest

from core.entidades import Cliente, LineaVenta, Venta


def test_cliente_descuento_pct_por_defecto_cero():
    assert Cliente(identificacion="1", nombre="x").descuento_pct == Decimal("0")


def test_cliente_rechaza_descuento_fuera_de_rango():
    with pytest.raises(ValueError):
        Cliente(identificacion="1", nombre="x", descuento_pct=Decimal("1"))


def test_venta_acepta_descuento_pct():
    linea = LineaVenta(producto_id=1, descripcion="p", cantidad_o_peso=Decimal("1"),
                       precio_unit=Decimal("100"), impuesto=Decimal("0"), subtotal=Decimal("100"))
    v = Venta(fecha=datetime.now(), lineas=(linea,), total=Decimal("100"),
              total_impuestos=Decimal("0"), descuento_pct=Decimal("0.1"))
    assert v.descuento_pct == Decimal("0.1")
