from decimal import Decimal

import pytest

from core.calculos import aplicar_descuento, subtotal_por_peso


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


def test_aplicar_descuento_porcentual():
    assert aplicar_descuento(Decimal("1000"), Decimal("0.1")) == Decimal("900")


def test_aplicar_descuento_cero_no_cambia():
    assert aplicar_descuento(Decimal("2500"), Decimal("0")) == Decimal("2500")


def test_aplicar_descuento_redondea_half_up_a_peso():
    # 999 * (1 - 0.075) = 924.075 -> 924
    assert aplicar_descuento(Decimal("999"), Decimal("0.075")) == Decimal("924")


def test_aplicar_descuento_rechaza_pct_fuera_de_rango():
    with pytest.raises(ValueError):
        aplicar_descuento(Decimal("1000"), Decimal("1"))
