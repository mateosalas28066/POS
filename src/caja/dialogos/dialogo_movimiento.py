"""Diálogo de movimiento de inventario (entrada/salida). Construye la entidad."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QLineEdit, QVBoxLayout,
)

from core.entidades import MovimientoInventario


class DialogoMovimiento(QDialog):
    def __init__(self, producto_id: int, parent=None) -> None:
        super().__init__(parent)
        self._producto_id = producto_id
        self.setWindowTitle("Movimiento de inventario")

        self._tipo = QComboBox()
        self._tipo.addItems(["entrada", "salida"])
        self._cantidad = QDoubleSpinBox()
        self._cantidad.setMaximum(99_999_999)
        self._cantidad.setDecimals(3)
        self._cantidad.setMinimum(0.001)
        self._ref = QLineEdit()
        self._ref.setPlaceholderText("Referencia (opcional)")

        form = QFormLayout()
        form.addRow("Tipo", self._tipo)
        form.addRow("Cantidad", self._cantidad)
        form.addRow("Referencia", self._ref)

        botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botones.button(QDialogButtonBox.Ok).setObjectName("primario")
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(botones)

    def movimiento(self) -> MovimientoInventario:
        return MovimientoInventario(
            producto_id=self._producto_id,
            tipo=self._tipo.currentText(),
            cantidad=Decimal(str(self._cantidad.value())),
            fecha=datetime.now(),
            ref=self._ref.text().strip() or None,
        )
