# tests/caja/test_conteo.py
from decimal import Decimal

import pytest

from caja.conteo import DENOMINACIONES, total_conteo


def test_denominaciones_colombianas_una_fila_1000():
    assert DENOMINACIONES == (100000, 50000, 20000, 10000, 5000, 2000, 1000, 500, 200, 100, 50)


def test_total_conteo_suma():
    conteo = {50000: 2, 1000: 3, 100: 5}
    assert total_conteo(conteo) == Decimal("103500")


def test_total_conteo_vacio_es_cero():
    assert total_conteo({}) == Decimal("0")


def test_total_conteo_rechaza_cantidad_negativa():
    with pytest.raises(ValueError):
        total_conteo({1000: -1})
