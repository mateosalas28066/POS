from decimal import Decimal

import pytest

from core.calculos import subtotal_por_peso
from core.perifericos.lector_peso import IngresoManual, LectorPeso


def test_ingreso_manual_devuelve_el_peso():
    lector: LectorPeso = IngresoManual(Decimal("1.234"))
    assert lector.leer_peso() == Decimal("1.234")


def test_ingreso_manual_rechaza_negativo():
    with pytest.raises(ValueError):
        IngresoManual(Decimal("-0.5"))


def test_subtotal_con_lector_manual():
    lector = IngresoManual(Decimal("2.5"))
    assert subtotal_por_peso(Decimal("32000"), lector.leer_peso()) == Decimal("80000")
