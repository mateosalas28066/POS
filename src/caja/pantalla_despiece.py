"""Pantalla de despiece (carnicería): reparte el costo del canal entre los cortes.
Lógica de costeo y persistencia en ServicioDespiece."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation

from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from caja.contexto import ContextoApp
from caja.formato import formato_moneda
from core.entidades import Producto
from core.servicio_despiece import prorratear_costeo_despiece

CERO = Decimal("0")


class PantallaDespiece(QWidget):
    def __init__(self, ctx: ContextoApp) -> None:
        super().__init__()
        self._ctx = ctx
        self._cortes: list[tuple[Producto, Decimal]] = []

        self._combo_canal = QComboBox()
        self._peso_canal = QLineEdit(); self._peso_canal.setPlaceholderText("Peso a despiezar (kg)")
        self._costo_canal = QLineEdit(); self._costo_canal.setPlaceholderText("Costo del canal")

        self._combo_corte = QComboBox()
        self._peso_corte = QLineEdit(); self._peso_corte.setPlaceholderText("Peso (kg)")
        boton_agregar = QPushButton("Agregar corte")
        boton_agregar.clicked.connect(self._agregar_corte)

        self._tabla = QTableWidget(0, 4)
        self._tabla.setHorizontalHeaderLabels(
            ["Corte", "Peso", "Costo asignado", "Costo unit"])
        self._tabla.setEditTriggers(QTableWidget.NoEditTriggers)

        boton_previsualizar = QPushButton("Previsualizar costeo")
        boton_previsualizar.clicked.connect(self._previsualizar)

        self._estado = QLabel("")
        self._estado.setObjectName("error")

        self._boton_confirmar = QPushButton("Confirmar despiece")
        self._boton_confirmar.setObjectName("primario")
        self._boton_confirmar.clicked.connect(self._confirmar)

        form = QVBoxLayout()
        form.addWidget(QLabel("Canal"))
        form.addWidget(self._combo_canal)
        form.addWidget(self._peso_canal)
        form.addWidget(self._costo_canal)
        form.addWidget(QLabel("Corte"))
        form.addWidget(self._combo_corte)
        form.addWidget(self._peso_corte)
        form.addWidget(boton_agregar)
        form.addWidget(self._estado)
        form.addStretch(1)
        panel = QWidget(); panel.setObjectName("panel"); panel.setLayout(form)

        der = QVBoxLayout()
        der.addWidget(QLabel("Cortes"))
        der.addWidget(self._tabla)
        der.addWidget(boton_previsualizar)
        der.addWidget(self._boton_confirmar)

        raiz = QHBoxLayout(self)
        raiz.addWidget(panel, 35)
        raiz.addLayout(der, 65)

        self.al_mostrar()

    def al_mostrar(self) -> None:
        productos = self._ctx.repo_productos.listar()
        self._combo_canal.blockSignals(True)
        self._combo_canal.clear()
        for p in productos:
            self._combo_canal.addItem(p.nombre, p)
        self._combo_canal.blockSignals(False)

        self._combo_corte.blockSignals(True)
        self._combo_corte.clear()
        for p in productos:
            self._combo_corte.addItem(p.nombre, p)
        self._combo_corte.blockSignals(False)

    @Slot()
    def _agregar_corte(self) -> None:
        producto = self._combo_corte.currentData()
        if producto is None:
            self._estado.setText("Selecciona un producto-corte")
            return
        try:
            peso = Decimal(self._peso_corte.text().strip())
        except InvalidOperation:
            self._estado.setText("Peso debe ser un número válido")
            return
        if peso <= CERO:
            self._estado.setText("Peso debe ser > 0")
            return
        self._cortes.append((producto, peso))
        fila = self._tabla.rowCount()
        self._tabla.insertRow(fila)
        self._tabla.setItem(fila, 0, QTableWidgetItem(producto.nombre))
        self._tabla.setItem(fila, 1, QTableWidgetItem(str(peso)))
        self._tabla.setItem(fila, 2, QTableWidgetItem(""))
        self._tabla.setItem(fila, 3, QTableWidgetItem(""))
        self._peso_corte.clear()
        self._estado.setText("")

    @Slot()
    def _previsualizar(self) -> None:
        if not self._cortes:
            self._estado.setText("Agrega al menos un corte")
            return
        try:
            costo_canal = Decimal(self._costo_canal.text().strip())
        except InvalidOperation:
            self._estado.setText("Costo del canal debe ser un número válido")
            return
        try:
            lineas = prorratear_costeo_despiece(
                costo_canal,
                [(prod.id, peso, prod.precio) for prod, peso in self._cortes])
        except ValueError as exc:
            self._estado.setText(f"Error: {exc}")
            return
        for fila, linea in enumerate(lineas):
            self._tabla.setItem(fila, 2, QTableWidgetItem(formato_moneda(linea.costo_asignado)))
            self._tabla.setItem(fila, 3, QTableWidgetItem(formato_moneda(linea.costo_unit)))
        self._estado.setText("")

    @Slot()
    def _confirmar(self) -> None:
        canal = self._combo_canal.currentData()
        if canal is None:
            self._estado.setText("Selecciona un canal")
            return
        if not self._cortes:
            self._estado.setText("Agrega al menos un corte")
            return
        try:
            peso_canal = Decimal(self._peso_canal.text().strip())
            costo_canal = Decimal(self._costo_canal.text().strip())
        except InvalidOperation:
            self._estado.setText("Peso y costo del canal deben ser números válidos")
            return
        cortes = [(prod.id, peso) for prod, peso in self._cortes]
        try:
            self._ctx.svc_despiece.registrar(
                producto_canal_id=canal.id, peso_canal=peso_canal, costo_canal=costo_canal,
                cortes=cortes, fecha=datetime.now(), usuario_id=self._ctx.usuario_actual_id)
        except ValueError as exc:
            self._estado.setText(f"Error: {exc}")
            return
        self._cortes = []
        self._tabla.setRowCount(0)
        self._peso_canal.clear()
        self._costo_canal.clear()
        self._estado.setText("Despiece registrado")
