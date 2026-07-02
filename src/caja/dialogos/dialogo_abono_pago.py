"""Diálogo de abono (cliente) / pago (proveedor) de cuentas. Mirror de DialogoMovimientoCaja."""
from __future__ import annotations

from decimal import Decimal

from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFormLayout

from caja.widgets import SpinMoneda
from core.entidades import MedioPago


class DialogoAbonoPago(QDialog):
    def __init__(self, titulo: str, medios: list[MedioPago], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(titulo)
        self._monto = SpinMoneda()
        self._combo = QComboBox()
        for m in medios:
            self._combo.addItem(m.nombre, m.id)

        form = QFormLayout(self)
        form.addRow("Monto", self._monto)
        form.addRow("Medio de pago", self._combo)

        botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botones.button(QDialogButtonBox.Ok).setObjectName("primario")
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)
        form.addRow(botones)

    def monto(self) -> Decimal:
        return Decimal(str(int(self._monto.value())))

    def medio_pago_id(self) -> int:
        return self._combo.currentData()
