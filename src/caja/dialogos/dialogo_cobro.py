"""Diálogo de cobro (venta) y reembolso (devolución): selección multi-medio."""
from __future__ import annotations

from decimal import Decimal

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLabel, QVBoxLayout

from caja.formato import formato_moneda
from caja.widgets import SpinMoneda
from core.entidades import MedioPago, Pago

CERO = Decimal("0")


class DialogoCobro(QDialog):
    def __init__(self, total: Decimal, medios: list[MedioPago], *, modo: str = "cobro",
                 efectivo_id: int, parent=None) -> None:
        super().__init__(parent)
        self._total = total
        self._modo = modo
        self._efectivo_id = efectivo_id
        titulo = "Cobrar" if modo == "cobro" else "Reembolsar"
        self.setWindowTitle(titulo)

        self._montos: dict[int, SpinMoneda] = {}
        form = QFormLayout()
        for m in medios:
            spin = SpinMoneda()
            spin.valueChanged.connect(self._refrescar)
            self._montos[m.id] = spin
            form.addRow(m.nombre, spin)

        self._lbl_total = QLabel(f"{titulo} total: {formato_moneda(total)}")
        self._lbl_total.setObjectName("kpi-valor")
        self._lbl_vuelto = QLabel("")
        self._lbl_vuelto.setObjectName("secundario")
        self._lbl_error = QLabel("")
        self._lbl_error.setObjectName("error")

        self._botones = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self._botones.button(QDialogButtonBox.Ok).setObjectName("primario")
        self._botones.accepted.connect(self._al_aceptar)
        self._botones.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self._lbl_total)
        layout.addLayout(form)
        layout.addWidget(self._lbl_vuelto)
        layout.addWidget(self._lbl_error)
        layout.addWidget(self._botones)
        self._refrescar()

    def _recibido(self) -> Decimal:
        return sum((Decimal(str(int(s.value()))) for s in self._montos.values()), CERO)

    def vuelto(self) -> Decimal:
        if self._modo != "cobro":
            return CERO
        return max(self._recibido() - self._total, CERO)

    def _validar(self) -> str | None:
        recibido = self._recibido()
        if recibido <= CERO:
            return "Ingresa al menos un monto"
        if self._modo == "cobro" and recibido < self._total:
            return f"Faltan {formato_moneda(self._total - recibido)}"
        if self._modo == "reembolso" and recibido != self._total:
            return f"El reembolso debe sumar exactamente {formato_moneda(self._total)}"
        return None

    def _refrescar(self) -> None:
        error = self._validar()
        self._lbl_error.setText(error or "")
        self._lbl_vuelto.setText(
            f"Vuelto: {formato_moneda(self.vuelto())}" if self._modo == "cobro" else "")
        self._botones.button(QDialogButtonBox.Ok).setEnabled(error is None)

    def pagos(self) -> list[Pago]:
        """Cobro: ajusta el efectivo para que la suma == total. Reembolso: montos tal cual."""
        crudos = {mid: Decimal(str(int(s.value()))) for mid, s in self._montos.items()}
        if self._modo == "reembolso":
            return [Pago(medio_pago_id=mid, monto=m) for mid, m in crudos.items() if m > CERO]
        no_efectivo = sum((m for mid, m in crudos.items() if mid != self._efectivo_id), CERO)
        efectivo_registrado = self._total - no_efectivo
        pagos: list[Pago] = []
        for mid, m in crudos.items():
            monto = efectivo_registrado if mid == self._efectivo_id else m
            if monto > CERO:
                pagos.append(Pago(medio_pago_id=mid, monto=monto))
        return pagos

    def _al_aceptar(self) -> None:
        if self._validar() is None:
            self.accept()
