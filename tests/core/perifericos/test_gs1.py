# tests/core/perifericos/test_gs1.py
from decimal import Decimal

import pytest

from core.perifericos.gs1 import CodigoPesoGS1, decodificar_gs1


def test_decodifica_codigo_y_peso():
    r = decodificar_gs1("2012340012344")
    assert r.codigo_producto == "01234"
    assert r.peso_kg == Decimal("1.234")


def test_digito_de_control_invalido_falla():
    with pytest.raises(ValueError):
        decodificar_gs1("2012340012340")  # último dígito incorrecto


def test_prefijo_no_de_peso_falla():
    with pytest.raises(ValueError):
        decodificar_gs1("3012340012344")  # no empieza por 2


def test_longitud_invalida_falla():
    with pytest.raises(ValueError):
        decodificar_gs1("20123")


def test_adaptador_cumple_lector_peso():
    lector = CodigoPesoGS1("2012340012344")
    assert lector.leer_peso() == Decimal("1.234")
    assert lector.codigo_producto == "01234"
