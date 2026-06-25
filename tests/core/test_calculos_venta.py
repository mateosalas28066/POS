from decimal import Decimal

import pytest

from core.calculos import calcular_vuelto, impuesto_incluido, subtotal_por_unidad


def test_subtotal_por_unidad_basico():
    assert subtotal_por_unidad(Decimal("3500"), Decimal("2")) == Decimal("7000")


def test_subtotal_por_unidad_negativo_falla():
    with pytest.raises(ValueError):
        subtotal_por_unidad(Decimal("3500"), Decimal("-1"))


def test_iva_incluido_19():
    # 11900 con IVA incluido al 19% -> IVA contenido 1900 exacto
    assert impuesto_incluido(Decimal("11900"), Decimal("0.19")) == Decimal("1900")


def test_iva_incluido_redondea_half_up():
    # 7000 * 0.19 / 1.19 = 1117.647... -> 1118
    assert impuesto_incluido(Decimal("7000"), Decimal("0.19")) == Decimal("1118")


def test_iva_incluido_tarifa_cero():
    assert impuesto_incluido(Decimal("6000"), Decimal("0")) == Decimal("0")


def test_vuelto_basico():
    assert calcular_vuelto(Decimal("13000"), Decimal("20000")) == Decimal("7000")


def test_vuelto_pago_insuficiente_falla():
    with pytest.raises(ValueError):
        calcular_vuelto(Decimal("13000"), Decimal("10000"))
