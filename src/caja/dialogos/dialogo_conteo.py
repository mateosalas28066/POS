"""Diálogo opcional para contar el efectivo por denominaciones y producir el total."""
from __future__ import annotations

from decimal import Decimal

from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QDialogButtonBox, QDialog, QFormLayout, QLabel, QSpinBox, QVBoxLayout,
)

from caja.conteo import DENOMINACIONES, total_conteo
from caja.formato import formato_moneda


class DialogoConteoEfectivo(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Contar efectivo")
        self._spins: dict[int, QSpinBox] = {}

        form = QFormLayout()
        for denominacion in DENOMINACIONES:
            spin = QSpinBox(); spin.setMaximum(100000)
            spin.valueChanged.connect(self._actualizar_total)
            self._spins[denominacion] = spin
            form.addRow(formato_moneda(Decimal(denominacion)), spin)

        self._lbl_total = QLabel(formato_moneda(Decimal("0")))
        self._lbl_total.setObjectName("kpi-valor")

        botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botones.button(QDialogButtonBox.Ok).setObjectName("primario")
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(QLabel("Total contado"))
        layout.addWidget(self._lbl_total)
        layout.addWidget(botones)

    def total(self) -> Decimal:
        return total_conteo({den: spin.value() for den, spin in self._spins.items()})

    @Slot()
    def _actualizar_total(self) -> None:
        self._lbl_total.setText(formato_moneda(self.total()))
