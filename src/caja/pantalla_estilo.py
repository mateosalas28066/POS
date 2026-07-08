"""Referencia viva del Sistema de Diseño en el POS (ventana dev)."""
from __future__ import annotations

import sys

from PySide6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from caja.efectos import aplica_glow
from caja.tema import carga_tema

_TOKENS = [
    ("carbon", "#0B0E14"), ("superficie", "#151A25"), ("superficie-2", "#1E2330"),
    ("marca", "#E01E26"), ("verde", "#22C55E"), ("ambar", "#F59E0B"),
]


class VentanaEstilo(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Estilo · Carnes y Fruver RL")
        raiz = QVBoxLayout(self)

        raiz.addWidget(QLabel("Sistema de Diseño — moderna premium"))

        fila = QHBoxLayout()
        for nombre, hex_ in _TOKENS:
            chip = QLabel(f"{nombre}\n{hex_}")
            chip.setStyleSheet(f"background:{hex_}; color:#F0F2F5; padding:16px; border-radius:10px;")
            fila.addWidget(chip)
        raiz.addLayout(fila)

        kpi = QLabel("$ 1.234.567")
        kpi.setObjectName("kpi-valor")
        raiz.addWidget(kpi)

        card = QFrame()
        card.setObjectName("card")
        card_l = QVBoxLayout(card)
        card_l.addWidget(QLabel("Tarjeta de superficie (card)"))
        raiz.addWidget(card)

        primario = QPushButton("Cobrar")
        primario.setObjectName("primario")
        aplica_glow(primario)
        raiz.addWidget(primario)


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    carga_tema(app)
    v = VentanaEstilo()
    v.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
