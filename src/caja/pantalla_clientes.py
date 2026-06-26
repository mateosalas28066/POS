"""Pantalla de clientes: tabla + formulario crear/editar. Lógica en ServicioClientes."""
from __future__ import annotations

from dataclasses import replace

from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from core.entidades import Cliente
from core.servicio_clientes import ServicioClientes


class PantallaClientes(QWidget):
    def __init__(self, servicio: ServicioClientes) -> None:
        super().__init__()
        self._servicio = servicio
        self._editando: Cliente | None = None
        self._clientes: list[Cliente] = []

        self._tabla = QTableWidget(0, 3)
        self._tabla.setHorizontalHeaderLabels(["Identificación", "Nombre", "Contacto"])
        self._tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self._tabla.setSelectionBehavior(QTableWidget.SelectRows)
        self._tabla.cellClicked.connect(lambda fila, _col: self._seleccionar_fila(fila))

        self._identificacion = QLineEdit(); self._identificacion.setPlaceholderText("Identificación")
        self._nombre = QLineEdit(); self._nombre.setPlaceholderText("Nombre")
        self._contacto = QLineEdit(); self._contacto.setPlaceholderText("Contacto (opcional)")
        self._boton_guardar = QPushButton("Crear")
        self._boton_guardar.setObjectName("primario")
        self._boton_guardar.clicked.connect(self._guardar)
        boton_nuevo = QPushButton("Nuevo")
        boton_nuevo.clicked.connect(self._nuevo)
        self._estado = QLabel("")
        self._estado.setObjectName("error")

        form = QVBoxLayout()
        form.addWidget(QLabel("Cliente"))
        form.addWidget(self._identificacion)
        form.addWidget(self._nombre)
        form.addWidget(self._contacto)
        form.addWidget(self._boton_guardar)
        form.addWidget(boton_nuevo)
        form.addWidget(self._estado)
        form.addStretch(1)
        panel = QWidget(); panel.setObjectName("panel"); panel.setLayout(form)

        raiz = QHBoxLayout(self)
        raiz.addWidget(self._tabla, 65)
        raiz.addWidget(panel, 35)

        self.al_mostrar()

    def al_mostrar(self) -> None:
        self._clientes = self._servicio.listar()
        self._tabla.setRowCount(0)
        for c in self._clientes:
            fila = self._tabla.rowCount()
            self._tabla.insertRow(fila)
            self._tabla.setItem(fila, 0, QTableWidgetItem(c.identificacion))
            self._tabla.setItem(fila, 1, QTableWidgetItem(c.nombre))
            self._tabla.setItem(fila, 2, QTableWidgetItem(c.contacto or ""))

    def _seleccionar_fila(self, fila: int) -> None:
        if not (0 <= fila < len(self._clientes)):
            return
        c = self._clientes[fila]
        self._editando = c
        self._identificacion.setText(c.identificacion)
        self._nombre.setText(c.nombre)
        self._contacto.setText(c.contacto or "")
        bloqueado = c.bloqueado_edicion
        for campo in (self._identificacion, self._nombre, self._contacto):
            campo.setEnabled(not bloqueado)
        self._boton_guardar.setEnabled(not bloqueado)
        self._boton_guardar.setText("Guardar cambios")
        self._estado.setText("Cliente bloqueado" if bloqueado else "")

    def _nuevo(self) -> None:
        self._editando = None
        for campo in (self._identificacion, self._nombre, self._contacto):
            campo.clear(); campo.setEnabled(True)
        self._boton_guardar.setEnabled(True)
        self._boton_guardar.setText("Crear")
        self._estado.setText("")

    def _guardar(self) -> None:
        identificacion = self._identificacion.text().strip()
        nombre = self._nombre.text().strip()
        contacto = self._contacto.text().strip() or None
        try:
            if self._editando is None:
                self._servicio.crear(identificacion, nombre, contacto)
            else:
                self._servicio.actualizar(replace(
                    self._editando, identificacion=identificacion,
                    nombre=nombre, contacto=contacto))
        except (ValueError, LookupError) as exc:
            self._estado.setText(f"Error: {exc}")
            return
        self._nuevo()
        self.al_mostrar()
