from decimal import Decimal

from core.entidades import LineaVenta
from caja.pantalla_venta import etiqueta_linea


def _linea(promocion_id):
    return LineaVenta(producto_id=1, descripcion="Lomo", cantidad_o_peso=Decimal("2"),
                      precio_unit=Decimal("15000"), impuesto=Decimal("0"),
                      subtotal=Decimal("30000"), promocion_id=promocion_id)


def test_etiqueta_marca_promo():
    assert "promo" in etiqueta_linea(_linea(3)).lower()


def test_etiqueta_sin_promo_es_solo_descripcion():
    assert etiqueta_linea(_linea(None)) == "Lomo"
