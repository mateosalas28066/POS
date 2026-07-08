"""Carga del tema: qt-material con la paleta de marca + fuentes + overlay."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication
from qt_material import apply_stylesheet

_DIR = Path(__file__).resolve().parent
RUTA_TEMA = _DIR / "recursos" / "temas" / "carnes_fruver.xml"
RUTA_OVERLAY = _DIR / "marca.qss"          # llega en MARCA.5
RUTA_FUENTES = _DIR / "recursos" / "fuentes"
RUTA_ICONOS = _DIR / "recursos" / "iconos"


def carga_fuentes() -> list[str]:
    """Registra las TTF de marca. Devuelve las familias cargadas."""
    familias: list[str] = []
    for ttf in sorted(RUTA_FUENTES.glob("*.ttf")):
        idx = QFontDatabase.addApplicationFont(str(ttf))
        familias += QFontDatabase.applicationFontFamilies(idx)
    return familias


def carga_tema(app: QApplication) -> None:
    carga_fuentes()
    apply_stylesheet(app, theme=str(RUTA_TEMA), invert_secondary=False)
    overlay = RUTA_OVERLAY.read_text(encoding="utf-8") if RUTA_OVERLAY.exists() else ""
    if overlay:
        app.setStyleSheet(app.styleSheet() + "\n" + overlay)


def icono(nombre: str) -> str:
    return str(RUTA_ICONOS / f"{nombre}.svg")
