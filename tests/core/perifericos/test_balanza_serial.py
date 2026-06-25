"""Test BalanzaSerial adaptador de puerto serial."""
from decimal import Decimal

import pytest

from core.perifericos.balanza_serial import BalanzaSerial


class _SerialFake:
    def __init__(self, trama: bytes) -> None:
        self._trama = trama

    def readline(self) -> bytes:
        return self._trama


def test_lee_peso_de_trama_continua():
    balanza = BalanzaSerial(_SerialFake(b"ST,GS,+001.234kg\r\n"))
    assert balanza.leer_peso() == Decimal("1.234")


def test_trama_sin_peso_falla():
    with pytest.raises(ValueError):
        BalanzaSerial(_SerialFake(b"ST,US,error\r\n")).leer_peso()


def test_parser_personalizado():
    balanza = BalanzaSerial(_SerialFake(b"PESO=2500g"),
                            parsear=lambda t: Decimal(t.split(b"=")[1][:-1].decode()) / 1000)
    assert balanza.leer_peso() == Decimal("2.5")
