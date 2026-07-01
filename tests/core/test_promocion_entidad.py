from datetime import datetime
from decimal import Decimal

import pytest

from core.entidades import LineaVenta, Promocion


def test_promo_precio_fijo_valida():
    p = Promocion(producto_id=1, tipo_valor="precio_fijo", valor=Decimal("8000"),
                  tipo_duracion="manual")
    assert p.activa is True


def test_promo_porcentaje_fuera_de_rango_rechaza():
    with pytest.raises(ValueError):
        Promocion(producto_id=1, tipo_valor="porcentaje", valor=Decimal("1"),
                  tipo_duracion="manual")


def test_promo_tiempo_exige_rango_ordenado():
    with pytest.raises(ValueError):
        Promocion(producto_id=1, tipo_valor="precio_fijo", valor=Decimal("8000"),
                  tipo_duracion="tiempo",
                  desde=datetime(2026, 7, 2), hasta=datetime(2026, 7, 1))


def test_promo_unidades_inicializa_restantes():
    p = Promocion(producto_id=1, tipo_valor="precio_fijo", valor=Decimal("8000"),
                  tipo_duracion="unidades", unidades_limite=Decimal("50"))
    assert p.unidades_restantes == Decimal("50")


def test_tipo_valor_invalido_rechaza():
    with pytest.raises(ValueError):
        Promocion(producto_id=1, tipo_valor="regalo", valor=Decimal("1"),
                  tipo_duracion="manual")


def test_linea_venta_acepta_promocion_id():
    ln = LineaVenta(producto_id=1, descripcion="X", cantidad_o_peso=Decimal("1"),
                    precio_unit=Decimal("8000"), impuesto=Decimal("0"),
                    subtotal=Decimal("8000"), promocion_id=5)
    assert ln.promocion_id == 5
