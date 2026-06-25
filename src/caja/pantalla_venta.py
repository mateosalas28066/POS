"""Prototipo de pantalla de caja (PySide6). La lógica vive en ServicioVenta (core)."""
from __future__ import annotations

from decimal import Decimal

from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from core.servicio_venta import ServicioVenta


class PantallaVenta(QWidget):
    def __init__(self, servicio: ServicioVenta) -> None:
        super().__init__()
        self._servicio = servicio
        self.setWindowTitle("Caja — Venta")

        self._codigo = QLineEdit()
        self._codigo.setPlaceholderText("Código de barras")
        self._peso = QLineEdit()
        self._peso.setPlaceholderText("Peso kg (si aplica)")
        boton = QPushButton("Agregar")
        boton.clicked.connect(self._al_agregar)

        self._tabla = QTableWidget(0, 3)
        self._tabla.setHorizontalHeaderLabels(["Descripción", "Cant/Peso", "Subtotal"])
        self._total = QLabel("Total: 0")

        fila = QHBoxLayout()
        fila.addWidget(self._codigo)
        fila.addWidget(self._peso)
        fila.addWidget(boton)

        layout = QVBoxLayout(self)
        layout.addLayout(fila)
        layout.addWidget(self._tabla)
        layout.addWidget(self._total)

    def _al_agregar(self) -> None:
        codigo = self._codigo.text().strip()
        if not codigo:
            return
        peso_txt = self._peso.text().strip()
        peso = Decimal(peso_txt) if peso_txt else None
        try:
            linea = self._servicio.agregar(codigo, peso_kg=peso)
        except ValueError as exc:
            self._total.setText(f"Error: {exc}")
            return
        fila = self._tabla.rowCount()
        self._tabla.insertRow(fila)
        self._tabla.setItem(fila, 0, QTableWidgetItem(linea.descripcion))
        self._tabla.setItem(fila, 1, QTableWidgetItem(str(linea.cantidad_o_peso)))
        self._tabla.setItem(fila, 2, QTableWidgetItem(str(linea.subtotal)))
        self._total.setText(f"Total: {self._servicio.total}")
        self._codigo.clear()
        self._peso.clear()
