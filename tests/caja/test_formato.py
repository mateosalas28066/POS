from datetime import datetime
from decimal import Decimal

from caja.formato import formato_moneda, formato_cantidad, formato_fecha


def test_moneda_separador_de_miles():
    assert formato_moneda(Decimal("1234567")) == "$ 1.234.567"
    assert formato_moneda(Decimal("0")) == "$ 0"
    assert formato_moneda(Decimal("-4500")) == "-$ 4.500"


def test_cantidad_unidad_entera_sin_decimales():
    assert formato_cantidad(Decimal("3"), "und") == "3 und"


def test_cantidad_kg_con_decimales():
    assert formato_cantidad(Decimal("1.5"), "kg") == "1,5 kg"


def test_fecha():
    assert formato_fecha(datetime(2026, 6, 25, 14, 32)) == "25/06/2026 14:32"
