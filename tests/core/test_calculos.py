from decimal import Decimal

import pytest

from core.calculos import subtotal_por_peso


def test_precio_por_peso_basico():
    assert subtotal_por_peso(Decimal("12000"), Decimal("1.234")) == Decimal("14808")


def test_redondea_a_pesos_enteros_half_up():
    # 1000 * 0.3335 = 333.5 -> 334
    assert subtotal_por_peso(Decimal("1000"), Decimal("0.3335")) == Decimal("334")


def test_peso_cero_da_cero():
    assert subtotal_por_peso(Decimal("32000"), Decimal("0")) == Decimal("0")


def test_negativos_fallan():
    with pytest.raises(ValueError):
        subtotal_por_peso(Decimal("-1"), Decimal("1"))
