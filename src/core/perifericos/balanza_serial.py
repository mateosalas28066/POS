"""Adaptador LectorPeso sobre balanza serial. pyserial se inyecta, no se importa."""
from __future__ import annotations

import re
from decimal import Decimal
from typing import Callable, Protocol

_NUMERO = re.compile(rb"[-+]?\d+\.\d+")


class _PuertoSerial(Protocol):
    def readline(self) -> bytes: ...


def _parsear_peso(trama: bytes) -> Decimal:
    """Extrae el primer número decimal de la trama (kg). Formato continuo común."""
    m = _NUMERO.search(trama)
    if not m:
        raise ValueError(f"trama de balanza sin peso: {trama!r}")
    return Decimal(m.group().decode())


class BalanzaSerial:
    def __init__(self, puerto: _PuertoSerial,
                 parsear: Callable[[bytes], Decimal] = _parsear_peso) -> None:
        self._puerto = puerto
        self._parsear = parsear

    def leer_peso(self) -> Decimal:
        return self._parsear(self._puerto.readline())
