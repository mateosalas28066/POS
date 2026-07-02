"""Diálogo autoservicio para que el usuario logueado cambie su propia contraseña."""
from __future__ import annotations

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit

from core.servicio_usuarios import CredencialInvalida, ServicioUsuarios


class DialogoCambioPassword(QDialog):
    def __init__(self, servicio: ServicioUsuarios, nombre_usuario: str, parent=None) -> None:
        super().__init__(parent)
        self._servicio = servicio
        self._nombre = nombre_usuario
        self.setWindowTitle(f"Cambiar contraseña — {nombre_usuario}")

        self._actual = QLineEdit(); self._actual.setEchoMode(QLineEdit.Password)
        self._nueva = QLineEdit(); self._nueva.setEchoMode(QLineEdit.Password)
        self._confirmacion = QLineEdit(); self._confirmacion.setEchoMode(QLineEdit.Password)
        self._estado = QLabel(""); self._estado.setObjectName("error")

        form = QFormLayout(self)
        form.addRow("Contraseña actual", self._actual)
        form.addRow("Contraseña nueva", self._nueva)
        form.addRow("Confirmar nueva", self._confirmacion)
        form.addRow(self._estado)

        botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botones.button(QDialogButtonBox.Ok).setObjectName("primario")
        botones.accepted.connect(self._al_aceptar)
        botones.rejected.connect(self.reject)
        form.addRow(botones)

    def _al_aceptar(self) -> None:
        if self._nueva.text() != self._confirmacion.text():
            self._estado.setText("Error: la confirmación no coincide")
            return
        try:
            self._servicio.cambiar_password(
                self._nombre, self._actual.text(), self._nueva.text())
        except (CredencialInvalida, ValueError) as exc:
            self._estado.setText(f"Error: {exc}")
            return
        self.accept()
