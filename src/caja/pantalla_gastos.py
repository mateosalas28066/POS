"""Pantalla de gastos: registrar + listar por período + administrar categorías (solo admin).

Lógica (efectivo→egreso de caja, CxC/CxP no aplica) vive en ctx.svc_gastos.
"""
from __future__ import annotations

from datetime import datetime, time
from decimal import Decimal

from PySide6.QtCore import QDate, Signal, Slot
from PySide6.QtWidgets import (
    QComboBox, QDateEdit, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from caja.contexto import ContextoApp, EFECTIVO_MEDIO_PAGO_ID
from caja.formato import formato_moneda
from caja.widgets import SpinMoneda

FIADO_MEDIO_PAGO_ID = 4


class PantallaGastos(QWidget):
    caja_cambiada = Signal()

    def __init__(self, ctx: ContextoApp) -> None:
        super().__init__()
        self._ctx = ctx
        self._categorias: list = []

        # --- Registrar gasto ---
        self._combo_categoria = QComboBox()
        self._monto = SpinMoneda()
        self._descripcion = QLineEdit(); self._descripcion.setPlaceholderText("Descripción (opcional)")
        self._combo_medio = QComboBox()
        for m in self._ctx.repo_medios_pago.listar():
            if m.id != FIADO_MEDIO_PAGO_ID:
                self._combo_medio.addItem(m.nombre, m.id)
        boton_registrar = QPushButton("Registrar")
        boton_registrar.setObjectName("primario")
        boton_registrar.clicked.connect(self._registrar)
        self._error_registro = QLabel("")
        self._error_registro.setObjectName("error")

        form = QVBoxLayout()
        form.addWidget(QLabel("Registrar gasto"))
        form.addWidget(QLabel("Categoría")); form.addWidget(self._combo_categoria)
        form.addWidget(QLabel("Monto")); form.addWidget(self._monto)
        form.addWidget(self._descripcion)
        form.addWidget(QLabel("Medio de pago")); form.addWidget(self._combo_medio)
        form.addWidget(boton_registrar)
        form.addWidget(self._error_registro)
        panel_form = QWidget(); panel_form.setObjectName("panel"); panel_form.setLayout(form)

        # --- Listado por período ---
        self._desde = QDateEdit(QDate.currentDate()); self._desde.setCalendarPopup(True)
        self._hasta = QDateEdit(QDate.currentDate()); self._hasta.setCalendarPopup(True)
        boton_consultar = QPushButton("Consultar")
        boton_consultar.clicked.connect(self._consultar)
        barra = QHBoxLayout()
        barra.addWidget(QLabel("Desde")); barra.addWidget(self._desde)
        barra.addWidget(QLabel("Hasta")); barra.addWidget(self._hasta)
        barra.addWidget(boton_consultar); barra.addStretch(1)

        self._tabla = QTableWidget(0, 5)
        self._tabla.setHorizontalHeaderLabels(["Fecha", "Categoría", "Monto", "Descripción", "Medio"])
        self._tabla.setEditTriggers(QTableWidget.NoEditTriggers)

        panel_lista = QWidget()
        ll = QVBoxLayout(panel_lista)
        ll.addLayout(barra)
        ll.addWidget(self._tabla)

        # --- Administrar categorías (solo admin) ---
        self._nombre_categoria = QLineEdit(); self._nombre_categoria.setPlaceholderText("Nueva categoría")
        boton_agregar_categoria = QPushButton("Agregar categoría")
        boton_agregar_categoria.clicked.connect(self._agregar_categoria)
        self._error_categoria = QLabel("")
        self._error_categoria.setObjectName("error")
        form_cat = QVBoxLayout()
        form_cat.addWidget(QLabel("Administrar categorías"))
        form_cat.addWidget(self._nombre_categoria)
        form_cat.addWidget(boton_agregar_categoria)
        form_cat.addWidget(self._error_categoria)
        self._panel_categorias = QWidget()
        self._panel_categorias.setObjectName("panel")
        self._panel_categorias.setLayout(form_cat)
        es_admin = self._ctx.usuario_actual is not None and self._ctx.usuario_actual.rol == "admin"
        self._panel_categorias.setVisible(es_admin)

        columnas = QHBoxLayout()
        columnas.addWidget(panel_form, 30)
        columnas.addWidget(panel_lista, 45)
        columnas.addWidget(self._panel_categorias, 25)

        raiz = QVBoxLayout(self)
        raiz.addLayout(columnas)

        self._cargar_categorias()
        self._consultar()

    def al_mostrar(self) -> None:
        self._cargar_categorias()
        self._consultar()

    def _cargar_categorias(self) -> None:
        self._categorias = self._ctx.svc_gastos.listar_categorias()
        actual = self._combo_categoria.currentData()
        self._combo_categoria.blockSignals(True)
        self._combo_categoria.clear()
        for c in self._categorias:
            self._combo_categoria.addItem(c.nombre, c.id)
        if actual is not None:
            idx = self._combo_categoria.findData(actual)
            if idx >= 0:
                self._combo_categoria.setCurrentIndex(idx)
        self._combo_categoria.blockSignals(False)

    def _rango(self) -> tuple[datetime, datetime]:
        d = self._desde.date().toPython()
        h = self._hasta.date().toPython()
        return (datetime.combine(d, time.min), datetime.combine(h, time.max))

    @Slot()
    def _consultar(self) -> None:
        desde, hasta = self._rango()
        nombres_cat = {c.id: c.nombre for c in self._categorias}
        self._tabla.setRowCount(0)
        for g in self._ctx.svc_gastos.listar(desde, hasta):
            medio = self._ctx.repo_medios_pago.por_id(g.medio_pago_id)
            fila = self._tabla.rowCount()
            self._tabla.insertRow(fila)
            valores = [
                g.fecha.strftime("%Y-%m-%d %H:%M"),
                nombres_cat.get(g.categoria_gasto_id, f"#{g.categoria_gasto_id}"),
                formato_moneda(g.monto),
                g.descripcion or "",
                medio.nombre if medio else f"#{g.medio_pago_id}",
            ]
            for col, texto in enumerate(valores):
                self._tabla.setItem(fila, col, QTableWidgetItem(texto))

    @Slot()
    def _registrar(self) -> None:
        categoria_id = self._combo_categoria.currentData()
        medio_id = self._combo_medio.currentData()
        monto = Decimal(str(int(self._monto.value())))
        descripcion = self._descripcion.text().strip() or None
        try:
            self._ctx.svc_gastos.registrar(
                categoria_gasto_id=categoria_id, monto=monto, medio_pago_id=medio_id,
                fecha=datetime.now(), descripcion=descripcion,
                usuario_id=self._ctx.usuario_actual_id)
        except ValueError as exc:
            self._error_registro.setText(f"Error: {exc}")
            return
        self._error_registro.setText("")
        self._monto.setValue(0)
        self._descripcion.clear()
        self._consultar()
        if medio_id == EFECTIVO_MEDIO_PAGO_ID:
            self.caja_cambiada.emit()

    @Slot()
    def _agregar_categoria(self) -> None:
        nombre = self._nombre_categoria.text().strip()
        try:
            self._ctx.svc_gastos.crear_categoria(nombre)
        except ValueError as exc:
            self._error_categoria.setText(f"Error: {exc}")
            return
        self._error_categoria.setText("")
        self._nombre_categoria.clear()
        self._cargar_categorias()
