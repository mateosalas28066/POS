"""Pantalla de compras a proveedor: alta de líneas + confirmación. Lógica en ServicioCompras."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation

from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QRadioButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from caja.contexto import ContextoApp
from caja.formato import formato_moneda
from core.entidades import Compra, LineaCompra

CERO = Decimal("0")


class PantallaCompras(QWidget):
    def __init__(self, ctx: ContextoApp) -> None:
        super().__init__()
        self._ctx = ctx
        self._lineas: list[LineaCompra] = []

        self._combo_proveedor = QComboBox()

        self._combo_producto = QComboBox()
        self._cantidad = QLineEdit(); self._cantidad.setPlaceholderText("Cantidad")
        self._costo_unit = QLineEdit(); self._costo_unit.setPlaceholderText("Costo unitario")
        boton_agregar = QPushButton("Agregar línea")
        boton_agregar.clicked.connect(self._agregar_linea)

        self._radio_contado = QRadioButton("Contado")
        self._radio_contado.setChecked(True)
        self._radio_credito = QRadioButton("Crédito")

        self._tabla = QTableWidget(0, 4)
        self._tabla.setHorizontalHeaderLabels(["Producto", "Cantidad", "Costo unit", "Subtotal"])
        self._tabla.setEditTriggers(QTableWidget.NoEditTriggers)

        self._lbl_total = QLabel(formato_moneda(CERO))
        self._lbl_total.setObjectName("kpi-valor")
        self._estado = QLabel("")
        self._estado.setObjectName("error")

        self._boton_confirmar = QPushButton("Confirmar compra")
        self._boton_confirmar.setObjectName("primario")
        self._boton_confirmar.clicked.connect(self._confirmar)

        form = QVBoxLayout()
        form.addWidget(QLabel("Proveedor"))
        form.addWidget(self._combo_proveedor)
        form.addWidget(QLabel("Producto"))
        form.addWidget(self._combo_producto)
        form.addWidget(self._cantidad)
        form.addWidget(self._costo_unit)
        form.addWidget(boton_agregar)
        estado_layout = QHBoxLayout()
        estado_layout.addWidget(self._radio_contado)
        estado_layout.addWidget(self._radio_credito)
        form.addLayout(estado_layout)
        form.addWidget(self._estado)
        form.addStretch(1)
        panel = QWidget(); panel.setObjectName("panel"); panel.setLayout(form)

        der = QVBoxLayout()
        der.addWidget(QLabel("Líneas"))
        der.addWidget(self._tabla)
        der.addWidget(QLabel("Total"))
        der.addWidget(self._lbl_total)
        der.addWidget(self._boton_confirmar)

        raiz = QHBoxLayout(self)
        raiz.addWidget(panel, 35)
        raiz.addLayout(der, 65)

        self.al_mostrar()

    def al_mostrar(self) -> None:
        self._combo_proveedor.blockSignals(True)
        self._combo_proveedor.clear()
        for p in self._ctx.svc_proveedores.listar():
            self._combo_proveedor.addItem(p.nombre, p.id)
        self._combo_proveedor.blockSignals(False)

        self._combo_producto.blockSignals(True)
        self._combo_producto.clear()
        for p in self._ctx.repo_productos.listar():
            self._combo_producto.addItem(p.nombre, p)
        self._combo_producto.blockSignals(False)

    @Slot()
    def _agregar_linea(self) -> None:
        producto = self._combo_producto.currentData()
        if producto is None:
            self._estado.setText("Selecciona un producto")
            return
        try:
            cantidad = Decimal(self._cantidad.text().strip())
            costo_unit = Decimal(self._costo_unit.text().strip())
        except InvalidOperation:
            self._estado.setText("Cantidad y costo unitario deben ser números válidos")
            return
        if cantidad <= CERO or costo_unit < CERO:
            self._estado.setText("Cantidad debe ser > 0 y costo unitario ≥ 0")
            return
        subtotal = cantidad * costo_unit
        linea = LineaCompra(
            producto_id=producto.id, descripcion=producto.nombre,
            cantidad=cantidad, costo_unit=costo_unit, subtotal=subtotal)
        self._lineas.append(linea)
        fila = self._tabla.rowCount()
        self._tabla.insertRow(fila)
        self._tabla.setItem(fila, 0, QTableWidgetItem(linea.descripcion))
        self._tabla.setItem(fila, 1, QTableWidgetItem(str(linea.cantidad)))
        self._tabla.setItem(fila, 2, QTableWidgetItem(formato_moneda(linea.costo_unit)))
        self._tabla.setItem(fila, 3, QTableWidgetItem(formato_moneda(linea.subtotal)))
        self._cantidad.clear()
        self._costo_unit.clear()
        self._estado.setText("")
        self._actualizar_total()

    def _actualizar_total(self) -> None:
        total = sum((l.subtotal for l in self._lineas), CERO)
        self._lbl_total.setText(formato_moneda(total))

    @Slot()
    def _confirmar(self) -> None:
        proveedor_id = self._combo_proveedor.currentData()
        if proveedor_id is None:
            self._estado.setText("Selecciona un proveedor")
            return
        if not self._lineas:
            self._estado.setText("Agrega al menos una línea")
            return
        estado = "pagada" if self._radio_contado.isChecked() else "credito"
        compra = Compra(
            proveedor_id=proveedor_id, fecha=datetime.now(), lineas=tuple(self._lineas),
            total=sum((l.subtotal for l in self._lineas), CERO), estado=estado,
            usuario_id=self._ctx.usuario_actual_id)
        try:
            self._ctx.svc_compras.registrar(compra)
        except ValueError as exc:
            self._estado.setText(f"Error: {exc}")
            return
        self._lineas = []
        self._tabla.setRowCount(0)
        self._actualizar_total()
        self._estado.setText("Compra registrada")
