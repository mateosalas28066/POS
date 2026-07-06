# tests/core/perifericos/test_gs1.py
from decimal import Decimal

import pytest

from core.perifericos.gs1 import (
    FORMATO_PESO_DEFECTO, CodigoPesoGS1, FormatoGS1, decodificar_gs1, es_peso_variable,
)


def test_decodifica_codigo_y_peso():
    r = decodificar_gs1("2012340012344")
    assert r.codigo_producto == "01234"
    assert r.peso_kg == Decimal("1.234")


def test_decodifica_etiqueta_prefijo_24_de_la_bascula():
    r = decodificar_gs1("2400190008059")
    assert r.codigo_producto == "00190"
    assert r.peso_kg == Decimal("0.805")
    assert r.valor_crudo == 805


def test_decodifica_etiqueta_prefijo_24_pezuna():
    r = decodificar_gs1("2400121004457")
    assert r.codigo_producto == "00121"
    assert r.peso_kg == Decimal("0.445")
    assert r.valor_crudo == 445


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


def test_decodifica_expone_valor_crudo():
    r = decodificar_gs1("2012340012344")
    assert r.valor_crudo == 1234  # dígitos de valor "01234" como entero, sin escalar


def test_formato_por_defecto_es_peso():
    assert FORMATO_PESO_DEFECTO.valor_es_precio is False


def test_es_peso_variable_detecta_prefijo_y_longitud():
    assert es_peso_variable("2012340012344") is True
    assert es_peso_variable("2400190008059") is True
    assert es_peso_variable("7700006") is False        # longitud != 13
    assert es_peso_variable("3012340012344") is False  # prefijo no es "2"
    assert es_peso_variable("20123A0012344") is False   # no son solo dígitos
