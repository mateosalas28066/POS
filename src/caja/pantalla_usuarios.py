"""Pantalla CRUD de usuarios (admin). La lógica vive en ServicioUsuarios (core)."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from core.entidades import ROLES
from core.servicio_usuarios import ServicioUsuarios


class PantallaUsuarios(QWidget):
    def __init__(self, servicio: ServicioUsuarios) -> None:
        super().__init__()
        self._servicio = servicio
        self.setWindowTitle("Usuarios")

        self._nombre = QLineEdit()
        self._nombre.setPlaceholderText("Usuario")
        self._password = QLineEdit()
        self._password.setPlaceholderText("Contraseña")
        self._password.setEchoMode(QLineEdit.Password)
        self._rol = QComboBox()
        self._rol.addItems(ROLES)
        boton = QPushButton("Crear")
        boton.clicked.connect(self._al_crear)

        self._tabla = QTableWidget(0, 2)
        self._tabla.setHorizontalHeaderLabels(["Usuario", "Rol"])
        self._estado = QLabel("")
        self._estado.setObjectName("error")

        fila = QHBoxLayout()
        fila.addWidget(self._nombre)
        fila.addWidget(self._password)
        fila.addWidget(self._rol)
        fila.addWidget(boton)

        layout = QVBoxLayout(self)
        layout.addLayout(fila)
        layout.addWidget(self._tabla)
        layout.addWidget(self._estado)

        self._refrescar()

    def _al_crear(self) -> None:
        try:
            self._servicio.crear(
                self._nombre.text().strip(), self._password.text(),
                rol=self._rol.currentText())
        except ValueError as exc:
            self._estado.setText(f"Error: {exc}")
            return
        self._estado.setText("")
        self._nombre.clear()
        self._password.clear()
        self._refrescar()

    def _refrescar(self) -> None:
        self._tabla.setRowCount(0)
        for u in self._servicio.listar():
            fila = self._tabla.rowCount()
            self._tabla.insertRow(fila)
            self._tabla.setItem(fila, 0, QTableWidgetItem(u.nombre))
            self._tabla.setItem(fila, 1, QTableWidgetItem(u.rol))
