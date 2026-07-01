"""Diálogo de login. Autentica contra ServicioUsuarios; el login es el gate real."""
from __future__ import annotations

from PySide6.QtWidgets import QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout

from core.entidades import Usuario
from core.servicio_usuarios import ServicioUsuarios


class DialogoLogin(QDialog):
    def __init__(self, servicio: ServicioUsuarios, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Ingreso")
        self._servicio = servicio
        self.usuario: Usuario | None = None

        self._nombre = QLineEdit()
        self._nombre.setPlaceholderText("Usuario")
        self._password = QLineEdit()
        self._password.setPlaceholderText("Contraseña")
        self._password.setEchoMode(QLineEdit.Password)
        self._password.returnPressed.connect(self._intentar)
        self._estado = QLabel("")
        self._estado.setObjectName("error")
        boton = QPushButton("Ingresar")
        boton.setObjectName("primario")
        boton.clicked.connect(self._intentar)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("POS — Carnes y Frutas"))
        layout.addWidget(self._nombre)
        layout.addWidget(self._password)
        layout.addWidget(self._estado)
        layout.addWidget(boton)

    def _intentar(self) -> None:
        usuario = self._servicio.autenticar(
            self._nombre.text().strip(), self._password.text())
        if usuario is None:
            self._estado.setText("Usuario o contraseña incorrectos")
            return
        self.usuario = usuario
        self.accept()
