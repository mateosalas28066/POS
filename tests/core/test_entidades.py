from datetime import datetime
from decimal import Decimal

import pytest

from core.entidades import Categoria, Impuesto, Producto, MovimientoInventario


def test_producto_valido_se_construye():
    p = Producto(codigo_barras="7701234567890", nombre="Lomo", precio=Decimal("32000"),
                 vendido_por_peso=True, unidad="kg")
    assert p.vendido_por_peso is True
    assert p.id is None


def test_impuesto_tarifa_fuera_de_rango_falla():
    with pytest.raises(ValueError):
        Impuesto(nombre="IVA", tarifa=Decimal("1.5"))


def test_producto_precio_negativo_falla():
    with pytest.raises(ValueError):
        Producto(codigo_barras="x", nombre="malo", precio=Decimal("-1"))


def test_movimiento_cantidad_no_positiva_falla():
    with pytest.raises(ValueError):
        MovimientoInventario(producto_id=1, tipo="entrada", cantidad=Decimal("0"),
                             fecha=datetime(2026, 6, 25))


def test_movimiento_tipo_invalido_falla():
    with pytest.raises(ValueError):
        MovimientoInventario(producto_id=1, tipo="regalo", cantidad=Decimal("1"),
                             fecha=datetime(2026, 6, 25))


def test_categoria_minima():
    assert Categoria(nombre="Carnes").nombre == "Carnes"
