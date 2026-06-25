from decimal import Decimal

import pytest

from core.calculos import subtotal_por_peso
from core.perifericos.balanza_serial import BalanzaSerial
from core.perifericos.gs1 import CodigoPesoGS1
from core.perifericos.lector_peso import IngresoManual, LectorPeso


class _SerialFake:
    def readline(self) -> bytes:
        return b"ST,GS,+001.234kg\r\n"


@pytest.mark.parametrize("lector", [
    IngresoManual(Decimal("1.234")),
    CodigoPesoGS1("2012340012344"),
    BalanzaSerial(_SerialFake()),
])
def test_precio_por_peso_es_independiente_del_adaptador(lector: LectorPeso):
    # Mismo peso (1.234 kg) por cualquiera de los tres caminos -> mismo subtotal.
    assert subtotal_por_peso(Decimal("12000"), lector.leer_peso()) == Decimal("14808")
