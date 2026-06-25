from decimal import Decimal
import pytest
from core.calculos import calcular_arqueo

def test_arqueo_cuadrado_diferencia_cero():
    a = calcular_arqueo(Decimal("100000"), Decimal("13000"), Decimal("113000"))
    assert a.esperado == Decimal("113000")
    assert a.diferencia == Decimal("0")

def test_arqueo_faltante_es_negativo():
    a = calcular_arqueo(Decimal("100000"), Decimal("13000"), Decimal("112000"))
    assert a.diferencia == Decimal("-1000")

def test_arqueo_sobrante_es_positivo():
    a = calcular_arqueo(Decimal("100000"), Decimal("13000"), Decimal("114000"))
    assert a.diferencia == Decimal("1000")

def test_arqueo_sin_ventas_solo_base():
    a = calcular_arqueo(Decimal("50000"), Decimal("0"), Decimal("50000"))
    assert a.esperado == Decimal("50000")
    assert a.diferencia == Decimal("0")
    assert a.efectivo_ventas == Decimal("0")

def test_arqueo_monto_negativo_falla():
    with pytest.raises(ValueError):
        calcular_arqueo(Decimal("-1"), Decimal("0"), Decimal("0"))
