"""Carga del tema QSS global y rutas de iconos."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QApplication

_DIR = Path(__file__).resolve().parent
RUTA_QSS = _DIR / "tema.qss"
RUTA_ICONOS = _DIR / "recursos" / "iconos"


def carga_tema(app: QApplication) -> None:
    app.setStyleSheet(RUTA_QSS.read_text(encoding="utf-8"))


def icono(nombre: str) -> str:
    return str(RUTA_ICONOS / f"{nombre}.svg")
