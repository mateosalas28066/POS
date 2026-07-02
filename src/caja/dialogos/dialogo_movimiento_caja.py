"""Diálogo de movimiento manual de efectivo (ingreso/egreso) de la caja abierta."""
from __future__ import annotations

from decimal import Decimal

from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLineEdit

from caja.widgets import SpinMoneda


class DialogoMovimientoCaja(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Movimiento de efectivo")
        self._tipo = QComboBox()
        self._tipo.addItem("Ingreso", "ingreso")
        self._tipo.addItem("Egreso", "egreso")
        self._monto = SpinMoneda()
        self._motivo = QLineEdit()
        self._motivo.setPlaceholderText("Motivo (obligatorio)")

        form = QFormLayout(self)
        form.addRow("Tipo", self._tipo)
        form.addRow("Monto", self._monto)
        form.addRow("Motivo", self._motivo)

        botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botones.button(QDialogButtonBox.Ok).setObjectName("primario")
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)
        form.addRow(botones)

    def tipo(self) -> str:
        return self._tipo.currentData()

    def monto(self) -> Decimal:
        return Decimal(str(int(self._monto.value())))

    def motivo(self) -> str:
        return self._motivo.text().strip()
