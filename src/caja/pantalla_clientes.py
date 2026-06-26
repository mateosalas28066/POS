"""Pantalla CRUD de clientes (PySide6). La lógica vive en ServicioClientes (core)."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from core.servicio_clientes import ServicioClientes


class PantallaClientes(QWidget):
    def __init__(self, servicio: ServicioClientes) -> None:
        super().__init__()
        self._servicio = servicio
        self.setWindowTitle("Clientes")

        self._identificacion = QLineEdit()
        self._identificacion.setPlaceholderText("Identificación")
        self._nombre = QLineEdit()
        self._nombre.setPlaceholderText("Nombre")
        self._contacto = QLineEdit()
        self._contacto.setPlaceholderText("Contacto (opcional)")
        boton = QPushButton("Crear")
        boton.clicked.connect(self._al_crear)

        self._tabla = QTableWidget(0, 3)
        self._tabla.setHorizontalHeaderLabels(["Identificación", "Nombre", "Contacto"])
        self._estado = QLabel("")

        fila = QHBoxLayout()
        fila.addWidget(self._identificacion)
        fila.addWidget(self._nombre)
        fila.addWidget(self._contacto)
        fila.addWidget(boton)

        layout = QVBoxLayout(self)
        layout.addLayout(fila)
        layout.addWidget(self._tabla)
        layout.addWidget(self._estado)

        self._refrescar()

    def _al_crear(self) -> None:
        try:
            self._servicio.crear(
                self._identificacion.text().strip(),
                self._nombre.text().strip(),
                self._contacto.text().strip() or None)
        except ValueError as exc:
            self._estado.setText(f"Error: {exc}")
            return
        self._estado.setText("")
        self._identificacion.clear()
        self._nombre.clear()
        self._contacto.clear()
        self._refrescar()

    def _refrescar(self) -> None:
        clientes = self._servicio.listar()
        self._tabla.setRowCount(0)
        for c in clientes:
            fila = self._tabla.rowCount()
            self._tabla.insertRow(fila)
            self._tabla.setItem(fila, 0, QTableWidgetItem(c.identificacion))
            self._tabla.setItem(fila, 1, QTableWidgetItem(c.nombre))
            self._tabla.setItem(fila, 2, QTableWidgetItem(c.contacto or ""))
