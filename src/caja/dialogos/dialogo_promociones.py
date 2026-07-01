"""Diálogo crear/listar/desactivar promociones por producto (admin o cajero)."""
from __future__ import annotations

from decimal import Decimal

from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QComboBox, QDateTimeEdit, QDialog, QDoubleSpinBox, QFormLayout, QHBoxLayout,
    QLabel, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from core.entidades import Producto, Promocion
from core.servicio_promociones import PromocionActivaExiste, ServicioPromociones

_COLS = ["ID", "Producto", "Valor", "Duración", "Activa"]


class DialogoPromociones(QDialog):
    def __init__(self, productos: list[Producto], svc_promociones: ServicioPromociones,
                 parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Promociones")
        self._svc = svc_promociones
        self._productos = productos

        self._producto = QComboBox()
        for p in productos:
            self._producto.addItem(p.nombre, p.id)
        self._tipo_valor = QComboBox(); self._tipo_valor.addItems(["precio_fijo", "porcentaje"])
        self._valor = QDoubleSpinBox(); self._valor.setMaximum(99_999_999); self._valor.setDecimals(0)
        self._tipo_duracion = QComboBox()
        self._tipo_duracion.addItems(["manual", "tiempo", "unidades"])
        self._desde = QDateTimeEdit(); self._desde.setCalendarPopup(True)
        self._hasta = QDateTimeEdit(); self._hasta.setCalendarPopup(True)
        self._unidades = QDoubleSpinBox(); self._unidades.setMaximum(99_999_999)
        self._unidades.setDecimals(0)
        self._estado = QLabel(""); self._estado.setObjectName("error")

        form = QFormLayout()
        form.addRow("Producto", self._producto)
        form.addRow("Tipo de valor", self._tipo_valor)
        form.addRow("Valor (pesos o %)", self._valor)
        form.addRow("Duración", self._tipo_duracion)
        form.addRow("Desde", self._desde)
        form.addRow("Hasta", self._hasta)
        form.addRow("Unidades", self._unidades)

        boton_crear = QPushButton("Crear"); boton_crear.setObjectName("primario")
        boton_crear.clicked.connect(self._crear)
        boton_desactivar = QPushButton("Desactivar seleccionada")
        boton_desactivar.clicked.connect(self._desactivar)
        barra = QHBoxLayout(); barra.addWidget(boton_crear); barra.addWidget(boton_desactivar)

        self._tabla = QTableWidget(0, len(_COLS))
        self._tabla.setHorizontalHeaderLabels(_COLS)
        self._tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self._tabla.setSelectionBehavior(QTableWidget.SelectRows)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(barra)
        layout.addWidget(self._estado)
        layout.addWidget(self._tabla)
        self._refrescar()

    def promocion(self) -> Promocion:
        tipo_valor = self._tipo_valor.currentText()
        if tipo_valor == "porcentaje":
            valor = Decimal(str(self._valor.value())) / Decimal("100")
        else:
            valor = Decimal(str(int(self._valor.value())))
        duracion = self._tipo_duracion.currentText()
        desde = self._desde.dateTime().toPython() if duracion == "tiempo" else None
        hasta = self._hasta.dateTime().toPython() if duracion == "tiempo" else None
        unidades = (Decimal(str(int(self._unidades.value())))
                    if duracion == "unidades" else None)
        return Promocion(
            producto_id=self._producto.currentData(),
            tipo_valor=tipo_valor, valor=valor, tipo_duracion=duracion,
            desde=desde, hasta=hasta, unidades_limite=unidades)

    @Slot()
    def _crear(self) -> None:
        try:
            self._svc.crear(self.promocion())
        except (PromocionActivaExiste, ValueError) as exc:
            self._estado.setText(f"Error: {exc}")
            return
        self._estado.setText("")
        self._refrescar()

    @Slot()
    def _desactivar(self) -> None:
        fila = self._tabla.currentRow()
        promos = self._svc.listar()
        if 0 <= fila < len(promos):
            self._svc.desactivar(promos[fila].id)
            self._refrescar()

    def _refrescar(self) -> None:
        nombres = {p.id: p.nombre for p in self._productos}
        promos = self._svc.listar()
        self._tabla.setRowCount(0)
        for promo in promos:
            fila = self._tabla.rowCount()
            self._tabla.insertRow(fila)
            valor = (f"{promo.valor:.0%}" if promo.tipo_valor == "porcentaje"
                     else f"${promo.valor:,.0f}")
            celdas = [str(promo.id), nombres.get(promo.producto_id, "—"), valor,
                      promo.tipo_duracion, "sí" if promo.activa else "no"]
            for col, texto in enumerate(celdas):
                self._tabla.setItem(fila, col, QTableWidgetItem(texto))
