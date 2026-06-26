"""Diálogo crear/editar Producto. No persiste; solo construye la entidad."""
from __future__ import annotations

from decimal import Decimal

from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox,
    QFormLayout, QLineEdit, QVBoxLayout,
)

from core.entidades import Categoria, Impuesto, Producto


class DialogoProducto(QDialog):
    def __init__(self, categorias: list[Categoria], impuestos: list[Impuesto], *,
                 producto: Producto | None = None, parent=None) -> None:
        super().__init__(parent)
        self._editando = producto
        self.setWindowTitle("Editar producto" if producto else "Nuevo producto")

        self._codigo = QLineEdit()
        self._nombre = QLineEdit()
        self._precio = QDoubleSpinBox(); self._precio.setMaximum(99_999_999); self._precio.setDecimals(0)
        self._costo = QDoubleSpinBox(); self._costo.setMaximum(99_999_999); self._costo.setDecimals(0)
        self._categoria = QComboBox()
        for c in categorias:
            self._categoria.addItem(c.nombre, c.id)
        self._impuesto = QComboBox()
        self._impuesto.addItem("(ninguno)", None)
        for i in impuestos:
            self._impuesto.addItem(i.nombre, i.id)
        self._por_peso = QCheckBox("Vendido por peso")
        self._unidad = QComboBox()
        self._unidad.addItems(["und", "kg"])

        if producto:
            self._codigo.setText(producto.codigo_barras)
            self._nombre.setText(producto.nombre)
            self._precio.setValue(float(producto.precio))
            self._costo.setValue(float(producto.costo))
            self._seleccionar(self._categoria, producto.categoria_id)
            self._seleccionar(self._impuesto, producto.impuesto_id)
            self._por_peso.setChecked(producto.vendido_por_peso)
            self._unidad.setCurrentText(producto.unidad)

        form = QFormLayout()
        form.addRow("Código de barras", self._codigo)
        form.addRow("Nombre", self._nombre)
        form.addRow("Precio", self._precio)
        form.addRow("Costo", self._costo)
        form.addRow("Categoría", self._categoria)
        form.addRow("Impuesto", self._impuesto)
        form.addRow("", self._por_peso)
        form.addRow("Unidad", self._unidad)

        botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botones.button(QDialogButtonBox.Ok).setObjectName("primario")
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(botones)

    @staticmethod
    def _seleccionar(combo: QComboBox, data) -> None:
        idx = combo.findData(data)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def producto(self) -> Producto:
        return Producto(
            codigo_barras=self._codigo.text().strip(),
            nombre=self._nombre.text().strip(),
            precio=Decimal(str(int(self._precio.value()))),
            costo=Decimal(str(int(self._costo.value()))),
            categoria_id=self._categoria.currentData(),
            impuesto_id=self._impuesto.currentData(),
            vendido_por_peso=self._por_peso.isChecked(),
            unidad=self._unidad.currentText(),
            id=self._editando.id if self._editando else None,
        )
