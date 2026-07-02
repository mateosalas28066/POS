"""Diálogo crear/listar/desactivar promociones por producto (admin o cajero)."""
from __future__ import annotations

from decimal import Decimal

from PySide6.QtCore import Qt, QDateTime, Slot
from PySide6.QtWidgets import (
    QComboBox, QDateTimeEdit, QDialog, QFormLayout, QHBoxLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from caja.widgets import DecimalSpinBoxPos
from core.entidades import Producto, Promocion
from core.servicio_promociones import PromocionActivaExiste, ServicioPromociones

_COLS = ["ID", "Producto", "Valor", "Duración", "Activa"]


class DialogoPromociones(QDialog):
    def __init__(self, productos: list[Producto], svc_promociones: ServicioPromociones,
                 parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Promociones")
        self.setMinimumSize(640, 520)
        self._svc = svc_promociones
        self._productos = productos

        self._tabla = QTableWidget(0, len(_COLS))
        self._tabla.setHorizontalHeaderLabels(_COLS)
        self._tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self._tabla.setSelectionBehavior(QTableWidget.SelectRows)

        boton_agregar = QPushButton("Agregar"); boton_agregar.setObjectName("primario")
        boton_agregar.clicked.connect(self._mostrar_formulario)
        boton_desactivar = QPushButton("Desactivar seleccionada")
        boton_desactivar.clicked.connect(self._desactivar)
        barra = QHBoxLayout(); barra.addWidget(boton_agregar); barra.addWidget(boton_desactivar)

        self._panel_form = self._crear_panel_formulario()
        self._panel_form.setVisible(False)

        self._estado = QLabel(""); self._estado.setObjectName("error")

        layout = QVBoxLayout(self)
        layout.addWidget(self._tabla)
        layout.addLayout(barra)
        layout.addWidget(self._panel_form)
        layout.addWidget(self._estado)
        self._refrescar()

    def _crear_panel_formulario(self) -> QWidget:
        self._producto = QComboBox()
        for p in self._productos:
            self._producto.addItem(p.nombre, p.id)
        self._tipo_valor = QComboBox(); self._tipo_valor.addItems(["precio_fijo", "porcentaje"])
        self._tipo_valor.currentTextChanged.connect(self._actualizar_formato_valor)
        self._valor = DecimalSpinBoxPos(); self._valor.setMaximum(99_999_999); self._valor.setDecimals(0)
        self._valor.setGroupSeparatorShown(True)
        self._tipo_duracion = QComboBox()
        self._tipo_duracion.addItems(["manual", "tiempo", "unidades"])
        self._tipo_duracion.currentTextChanged.connect(self._actualizar_visibilidad_duracion)
        ahora = QDateTime.currentDateTime()
        self._desde = QDateTimeEdit(ahora); self._desde.setCalendarPopup(True)
        self._hasta = QDateTimeEdit(ahora.addSecs(3600)); self._hasta.setCalendarPopup(True)
        self._unidades = DecimalSpinBoxPos(); self._unidades.setMaximum(99_999_999)
        self._unidades.setDecimals(0)

        self._form = QFormLayout()
        self._form.addRow("Producto", self._producto)
        self._form.addRow("Tipo de valor", self._tipo_valor)
        self._form.addRow("Valor (pesos o %)", self._valor)
        self._form.addRow("Duración", self._tipo_duracion)
        self._form.addRow("Desde", self._desde)
        self._form.addRow("Hasta", self._hasta)
        self._form.addRow("Unidades", self._unidades)

        boton_crear = QPushButton("Crear"); boton_crear.setObjectName("primario")
        boton_crear.clicked.connect(self._crear)
        boton_cancelar = QPushButton("Cancelar")
        boton_cancelar.clicked.connect(lambda: self._panel_form.setVisible(False))
        botones = QHBoxLayout(); botones.addWidget(boton_crear); botones.addWidget(boton_cancelar)

        panel = QWidget()
        contenedor = QVBoxLayout(panel)
        contenedor.addLayout(self._form)
        contenedor.addLayout(botones)
        self._actualizar_formato_valor(self._tipo_valor.currentText())
        self._actualizar_visibilidad_duracion(self._tipo_duracion.currentText())
        return panel

    @Slot()
    def _mostrar_formulario(self) -> None:
        self._panel_form.setVisible(True)

    @Slot(str)
    def _actualizar_formato_valor(self, tipo_valor: str) -> None:
        if tipo_valor == "porcentaje":
            self._valor.setPrefix("")
            self._valor.setSuffix(" %")
        else:
            self._valor.setPrefix("$ ")
            self._valor.setSuffix("")

    @Slot(str)
    def _actualizar_visibilidad_duracion(self, tipo_duracion: str) -> None:
        self._form.setRowVisible(self._desde, tipo_duracion == "tiempo")
        self._form.setRowVisible(self._hasta, tipo_duracion == "tiempo")
        self._form.setRowVisible(self._unidades, tipo_duracion == "unidades")

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
        self._panel_form.setVisible(False)
        self._refrescar()

    @Slot()
    def _desactivar(self) -> None:
        item = self._tabla.item(self._tabla.currentRow(), 0)
        if item is None:
            return
        self._svc.desactivar(item.data(Qt.UserRole))
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
                item = QTableWidgetItem(texto)
                if col == 0:
                    item.setData(Qt.UserRole, promo.id)
                self._tabla.setItem(fila, col, item)
