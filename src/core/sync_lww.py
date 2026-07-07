"""Regla pura de last-write-wins por fila (base del sync bidireccional de catálogo)."""
from __future__ import annotations

from datetime import datetime


def gana_escritura(entrante: datetime, existente: datetime | None) -> bool:
    """True si la escritura entrante (su actualizado_en) debe sobrescribir a la existente.
    Empate conserva lo existente (no reescribe)."""
    return existente is None or entrante > existente
