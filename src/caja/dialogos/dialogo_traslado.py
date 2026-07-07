"""Diálogo de traslado de inventario multi-ubicación (cross-local): cantidad + destino."""
from __future__ import annotations

from decimal import Decimal

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QVBoxLayout

from caja.widgets import DecimalSpinBoxPos


class DialogoTraslado(QDialog):
    def __init__(self, producto_id: int, parent=None) -> None:
        super().__init__(parent)
        self._producto_id = producto_id
        self.setWindowTitle("Traslado a otra ubicación")

        self._cantidad = DecimalSpinBoxPos()
        self._cantidad.setMaximum(99_999_999)
        self._cantidad.setDecimals(3)
        self._cantidad.setMinimum(0.001)
        self._destino_id = QLineEdit()
        self._destino_id.setPlaceholderText("ID de la ubicación destino")
        self._ref = QLineEdit()
        self._ref.setPlaceholderText("Referencia (opcional)")

        form = QFormLayout()
        form.addRow("Cantidad", self._cantidad)
        form.addRow("Destino (ubicación)", self._destino_id)
        form.addRow("Referencia", self._ref)

        botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botones.button(QDialogButtonBox.Ok).setObjectName("primario")
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(botones)

    @property
    def producto_id(self) -> int:
        return self._producto_id

    def cantidad(self) -> Decimal:
        return Decimal(str(self._cantidad.value()))

    def destino_id(self) -> int | None:
        texto = self._destino_id.text().strip()
        return int(texto) if texto.isdigit() else None

    def ref(self) -> str | None:
        return self._ref.text().strip() or None
