"""Efecto glow neón de marca para widgets clave (nav activo, botón primario, total)."""
from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QWidget

_GLOW = QColor(224, 30, 38, 115)  # rgba(224,30,38,.45)


def aplica_glow(widget: QWidget, radio: int = 24) -> None:
    efecto = QGraphicsDropShadowEffect(widget)
    efecto.setBlurRadius(radio)
    efecto.setColor(_GLOW)
    efecto.setOffset(0, 0)
    widget.setGraphicsEffect(efecto)
