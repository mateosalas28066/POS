"""Pantalla de reportes: ventas / inventario por rango de fechas. Solo lectura."""
from __future__ import annotations

from datetime import datetime, time

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QDateEdit, QGridLayout, QHBoxLayout, QLabel, QPushButton, QTabWidget,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from caja.contexto import ContextoApp
from caja.formato import formato_moneda
from caja.widgets import TarjetaKpi


class PantallaReportes(QWidget):
    def __init__(self, ctx: ContextoApp) -> None:
        super().__init__()
        self._ctx = ctx

        self._desde = QDateEdit(QDate.currentDate()); self._desde.setCalendarPopup(True)
        self._hasta = QDateEdit(QDate.currentDate()); self._hasta.setCalendarPopup(True)
        boton = QPushButton("Consultar"); boton.setObjectName("primario")
        boton.clicked.connect(self._consultar)
        barra = QHBoxLayout()
        barra.addWidget(QLabel("Desde")); barra.addWidget(self._desde)
        barra.addWidget(QLabel("Hasta")); barra.addWidget(self._hasta)
        barra.addWidget(boton); barra.addStretch(1)

        # KPIs ventas
        self._kpi_num = TarjetaKpi("# Ventas")
        self._kpi_total = TarjetaKpi("Total bruto")
        self._kpi_iva = TarjetaKpi("IVA")
        self._kpi_dev = TarjetaKpi("Devoluciones")
        self._kpi_neto = TarjetaKpi("Neto")
        kpis = QGridLayout()
        for i, k in enumerate((self._kpi_num, self._kpi_total, self._kpi_iva,
                               self._kpi_dev, self._kpi_neto)):
            kpis.addWidget(k, 0, i)

        self._tabla_ventas = QTableWidget(0, 2)
        self._tabla_ventas.setHorizontalHeaderLabels(["Medio de pago", "Neto"])
        self._tabla_ventas.setEditTriggers(QTableWidget.NoEditTriggers)
        tab_ventas = QWidget(); lv = QVBoxLayout(tab_ventas)
        lv.addLayout(kpis); lv.addWidget(self._tabla_ventas)

        self._tabla_inventario = QTableWidget(0, 4)
        self._tabla_inventario.setHorizontalHeaderLabels(
            ["Producto", "Entradas", "Salidas", "Neto"])
        self._tabla_inventario.setEditTriggers(QTableWidget.NoEditTriggers)
        tab_inv = QWidget(); li = QVBoxLayout(tab_inv); li.addWidget(self._tabla_inventario)

        tabs = QTabWidget()
        tabs.addTab(tab_ventas, "Ventas")
        tabs.addTab(tab_inv, "Inventario")

        layout = QVBoxLayout(self)
        layout.addLayout(barra)
        layout.addWidget(tabs)

    def al_mostrar(self) -> None:
        self._consultar()

    def _rango(self) -> tuple[datetime, datetime]:
        d = self._desde.date().toPython()
        h = self._hasta.date().toPython()
        return (datetime.combine(d, time.min), datetime.combine(h, time.max))

    def _consultar(self) -> None:
        desde, hasta = self._rango()
        rv = self._ctx.svc_reportes.ventas(desde, hasta)
        self._kpi_num.set_valor(str(rv.num_ventas))
        self._kpi_total.set_valor(formato_moneda(rv.total))
        self._kpi_iva.set_valor(formato_moneda(rv.total_impuestos))
        self._kpi_dev.set_valor(formato_moneda(rv.total_devoluciones))
        self._kpi_neto.set_valor(formato_moneda(rv.neto))

        self._tabla_ventas.setRowCount(0)
        for medio_id, monto in rv.por_medio.items():
            medio = self._ctx.repo_medios_pago.por_id(medio_id)
            fila = self._tabla_ventas.rowCount()
            self._tabla_ventas.insertRow(fila)
            self._tabla_ventas.setItem(fila, 0, QTableWidgetItem(
                medio.nombre if medio else f"#{medio_id}"))
            self._tabla_ventas.setItem(fila, 1, QTableWidgetItem(formato_moneda(monto)))

        ri = self._ctx.svc_reportes.inventario(desde, hasta)
        self._tabla_inventario.setRowCount(0)
        for mp in ri.por_producto:
            prod = self._ctx.repo_productos.por_id(mp.producto_id)
            fila = self._tabla_inventario.rowCount()
            self._tabla_inventario.insertRow(fila)
            self._tabla_inventario.setItem(fila, 0, QTableWidgetItem(
                prod.nombre if prod else f"#{mp.producto_id}"))
            self._tabla_inventario.setItem(fila, 1, QTableWidgetItem(str(mp.entradas)))
            self._tabla_inventario.setItem(fila, 2, QTableWidgetItem(str(mp.salidas)))
            self._tabla_inventario.setItem(fila, 3, QTableWidgetItem(str(mp.neto)))
