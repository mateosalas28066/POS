"""Pantalla de reportes: ventas / inventario por rango de fechas. Solo lectura."""
from __future__ import annotations

from datetime import datetime, time
from decimal import Decimal

from PySide6.QtCore import QDate, Slot
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QDateEdit, QGridLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from caja.contexto import ContextoApp
from caja.formato import formato_cantidad, formato_moneda
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

        # Pestaña "Por categoría"
        self._tabla_categoria = QTableWidget(0, 5)
        self._tabla_categoria.setHorizontalHeaderLabels(
            ["Categoría", "Ventas", "IVA", "Devoluciones", "Neto"])
        self._tabla_categoria.setEditTriggers(QTableWidget.NoEditTriggers)
        tab_cat = QWidget(); lcat = QVBoxLayout(tab_cat); lcat.addWidget(self._tabla_categoria)

        self._tabla_inventario = QTableWidget(0, 4)
        self._tabla_inventario.setHorizontalHeaderLabels(
            ["Producto", "Entradas", "Salidas", "Neto"])
        self._tabla_inventario.setEditTriggers(QTableWidget.NoEditTriggers)
        tab_inv = QWidget(); li = QVBoxLayout(tab_inv); li.addWidget(self._tabla_inventario)

        # Pestaña "Por factura"
        self._facturas: tuple = ()
        self._tabla_factura = QTableWidget(0, 7)
        self._tabla_factura.setHorizontalHeaderLabels(
            ["#", "Fecha", "Cajero", "Cliente", "Total", "IVA", "Estado"])
        self._tabla_factura.setEditTriggers(QTableWidget.NoEditTriggers)
        self._tabla_factura.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._tabla_factura.setSelectionMode(QAbstractItemView.SingleSelection)
        self._tabla_factura.itemSelectionChanged.connect(self._mostrar_detalle_factura)
        self._detalle_factura = QTableWidget(0, 4)
        self._detalle_factura.setHorizontalHeaderLabels(
            ["Detalle", "Cant/Peso", "Subtotal", "IVA"])
        self._detalle_factura.setEditTriggers(QTableWidget.NoEditTriggers)
        tab_fac = QWidget(); lf = QVBoxLayout(tab_fac)
        lf.addWidget(self._tabla_factura); lf.addWidget(QLabel("Detalle de la factura"))
        lf.addWidget(self._detalle_factura)

        # Pestaña "Por cajero"
        self._filas_cajero: tuple = ()
        self._fuente_cajero = QComboBox()
        self._fuente_cajero.currentIndexChanged.connect(self._consultar_cajero)
        self._tabla_cajero = QTableWidget(0, 5)
        self._tabla_cajero.setHorizontalHeaderLabels(
            ["Cajero", "# Ventas", "Total", "Devoluciones", "Neto"])
        self._tabla_cajero.setEditTriggers(QTableWidget.NoEditTriggers)
        self._tabla_cajero.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._tabla_cajero.setSelectionMode(QAbstractItemView.SingleSelection)
        self._tabla_cajero.itemSelectionChanged.connect(self._mostrar_detalle_cajero)
        self._detalle_cajero = QTableWidget(0, 2)
        self._detalle_cajero.setHorizontalHeaderLabels(["Método de pago", "Monto"])
        self._detalle_cajero.setEditTriggers(QTableWidget.NoEditTriggers)
        tab_caj = QWidget(); lc = QVBoxLayout(tab_caj)
        barra_caj = QHBoxLayout()
        barra_caj.addWidget(QLabel("Fuente")); barra_caj.addWidget(self._fuente_cajero)
        barra_caj.addStretch(1)
        lc.addLayout(barra_caj); lc.addWidget(self._tabla_cajero)
        lc.addWidget(QLabel("Métodos de pago del cajero seleccionado"))
        lc.addWidget(self._detalle_cajero)

        tabs = QTabWidget()
        tabs.addTab(tab_ventas, "Ventas")
        tabs.addTab(tab_cat, "Por categoría")
        tabs.addTab(tab_inv, "Inventario")
        tabs.addTab(tab_fac, "Por factura")
        tabs.addTab(tab_caj, "Por cajero")

        layout = QVBoxLayout(self)
        layout.addLayout(barra)
        layout.addWidget(tabs)

    def al_mostrar(self) -> None:
        self._consultar()

    def _rango(self) -> tuple[datetime, datetime]:
        d = self._desde.date().toPython()
        h = self._hasta.date().toPython()
        return (datetime.combine(d, time.min), datetime.combine(h, time.max))

    @Slot()
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

        nombres_cat = {c.id: c.nombre for c in self._ctx.repo_categorias.listar()}
        self._tabla_categoria.setRowCount(0)
        for rc in self._ctx.svc_reportes.por_categoria(desde, hasta):
            fila = self._tabla_categoria.rowCount()
            self._tabla_categoria.insertRow(fila)
            valores = [
                nombres_cat.get(rc.categoria_id, "Sin categoría"),
                formato_moneda(rc.total), formato_moneda(rc.total_impuestos),
                formato_moneda(rc.total_devoluciones), formato_moneda(rc.neto)]
            for col, texto in enumerate(valores):
                self._tabla_categoria.setItem(fila, col, QTableWidgetItem(texto))

        ri = self._ctx.svc_reportes.inventario(desde, hasta)
        self._tabla_inventario.setRowCount(0)
        for mp in ri.por_producto:
            prod = self._ctx.repo_productos.por_id(mp.producto_id)
            fila = self._tabla_inventario.rowCount()
            self._tabla_inventario.insertRow(fila)
            self._tabla_inventario.setItem(fila, 0, QTableWidgetItem(
                prod.nombre if prod else f"#{mp.producto_id}"))
            self._tabla_inventario.setItem(fila, 1, QTableWidgetItem(
                formato_cantidad(mp.entradas, "")))
            self._tabla_inventario.setItem(fila, 2, QTableWidgetItem(
                formato_cantidad(mp.salidas, "")))
            self._tabla_inventario.setItem(fila, 3, QTableWidgetItem(
                formato_cantidad(mp.neto, "")))

        self._facturas = self._ctx.svc_reportes.facturas(desde, hasta)
        self._tabla_factura.setRowCount(0)
        for v in self._facturas:
            cajero = self._ctx.repo_usuarios.por_id(v.usuario_id) if v.usuario_id else None
            cliente = self._ctx.repo_clientes.por_id(v.cliente_id) if v.cliente_id else None
            fila = self._tabla_factura.rowCount()
            self._tabla_factura.insertRow(fila)
            valores = [
                str(v.id), v.fecha.strftime("%Y-%m-%d %H:%M"),
                cajero.nombre if cajero else "Sin cajero",
                cliente.nombre if cliente else "—",
                formato_moneda(v.total), formato_moneda(v.total_impuestos), v.estado]
            for col, texto in enumerate(valores):
                self._tabla_factura.setItem(fila, col, QTableWidgetItem(texto))
        self._detalle_factura.setRowCount(0)

        self._fuente_cajero.blockSignals(True)
        self._fuente_cajero.clear()
        self._fuente_cajero.addItem("Rango de fechas", None)
        for s in self._ctx.repo_sesiones.listar():
            etiqueta = f"Sesión #{s.id} · {s.apertura_fecha.strftime('%Y-%m-%d %H:%M')}"
            self._fuente_cajero.addItem(etiqueta, s.id)
        self._fuente_cajero.blockSignals(False)
        self._consultar_cajero()

    def _mostrar_detalle_factura(self) -> None:
        fila = self._tabla_factura.currentRow()
        self._detalle_factura.setRowCount(0)
        if not (0 <= fila < len(self._facturas)):
            return
        v = self._facturas[fila]
        for ln in v.lineas:
            r = self._detalle_factura.rowCount()
            self._detalle_factura.insertRow(r)
            for col, texto in enumerate((ln.descripcion, str(ln.cantidad_o_peso),
                                         formato_moneda(ln.subtotal),
                                         formato_moneda(ln.impuesto))):
                self._detalle_factura.setItem(r, col, QTableWidgetItem(texto))
        for p in self._ctx.repo_ventas.pagos_de(v.id):
            medio = self._ctx.repo_medios_pago.por_id(p.medio_pago_id)
            r = self._detalle_factura.rowCount()
            self._detalle_factura.insertRow(r)
            nombre = medio.nombre if medio else f"#{p.medio_pago_id}"
            self._detalle_factura.setItem(r, 0, QTableWidgetItem(f"Pago · {nombre}"))
            self._detalle_factura.setItem(r, 2, QTableWidgetItem(formato_moneda(p.monto)))

    def _consultar_cajero(self) -> None:
        sesion_id = self._fuente_cajero.currentData()
        if sesion_id is None:
            desde, hasta = self._rango()
            filas = self._ctx.svc_reportes.por_cajero(desde, hasta)
        else:
            filas = self._ctx.svc_reportes.por_cajero_de_sesion(sesion_id)
        self._filas_cajero = filas
        self._tabla_cajero.setRowCount(0)
        for c in filas:
            cajero = self._ctx.repo_usuarios.por_id(c.usuario_id) if c.usuario_id else None
            fila = self._tabla_cajero.rowCount()
            self._tabla_cajero.insertRow(fila)
            valores = [
                cajero.nombre if cajero else "Sin cajero", formato_cantidad(Decimal(c.num_ventas), ""),
                formato_moneda(c.total), formato_moneda(c.total_devoluciones),
                formato_moneda(c.neto)]
            for col, texto in enumerate(valores):
                self._tabla_cajero.setItem(fila, col, QTableWidgetItem(texto))
        self._detalle_cajero.setRowCount(0)

    def _mostrar_detalle_cajero(self) -> None:
        fila = self._tabla_cajero.currentRow()
        self._detalle_cajero.setRowCount(0)
        if not (0 <= fila < len(self._filas_cajero)):
            return
        for medio_id, monto in self._filas_cajero[fila].por_medio.items():
            medio = self._ctx.repo_medios_pago.por_id(medio_id)
            r = self._detalle_cajero.rowCount()
            self._detalle_cajero.insertRow(r)
            nombre = medio.nombre if medio else f"#{medio_id}"
            self._detalle_cajero.setItem(r, 0, QTableWidgetItem(nombre))
            self._detalle_cajero.setItem(r, 1, QTableWidgetItem(formato_moneda(monto)))
