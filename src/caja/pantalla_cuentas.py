"""Pantalla de cuentas: por cobrar (clientes) / por pagar (proveedores).

Lógica (saldos, abono→ingreso, pago→egreso) vive en ctx.svc_cxc/ctx.svc_cxp.
"""
from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QTabWidget, QVBoxLayout, QWidget,
)

from caja.contexto import ContextoApp
from caja.dialogos.dialogo_abono_pago import DialogoAbonoPago
from caja.formato import formato_moneda


class PantallaCuentas(QWidget):
    caja_cambiada = Signal()

    def __init__(self, ctx: ContextoApp) -> None:
        super().__init__()
        self._ctx = ctx
        self._ids_cobrar: list[int] = []
        self._ids_pagar: list[int] = []

        tab_cobrar, self._tabla_cobrar, self._estado_cobrar = self._crear_pestana(
            "Abonar", self._abonar)
        tab_pagar, self._tabla_pagar, self._estado_pagar = self._crear_pestana(
            "Pagar", self._pagar)

        tabs = QTabWidget()
        tabs.addTab(tab_cobrar, "Por cobrar")
        tabs.addTab(tab_pagar, "Por pagar")

        layout = QVBoxLayout(self)
        layout.addWidget(tabs)

    def _crear_pestana(self, texto_boton: str, callback) -> tuple[QWidget, QTableWidget, QLabel]:
        tabla = QTableWidget(0, 2)
        tabla.setHorizontalHeaderLabels(["Nombre", "Saldo"])
        tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        tabla.setSelectionBehavior(QTableWidget.SelectRows)
        boton = QPushButton(texto_boton)
        boton.setObjectName("primario")
        boton.clicked.connect(callback)
        estado = QLabel("")
        estado.setObjectName("error")
        barra = QHBoxLayout()
        barra.addWidget(boton)
        barra.addStretch(1)
        tab = QWidget()
        l = QVBoxLayout(tab)
        l.addWidget(tabla)
        l.addLayout(barra)
        l.addWidget(estado)
        return tab, tabla, estado

    def al_mostrar(self) -> None:
        self._cargar_cobrar()
        self._cargar_pagar()

    def _cargar_cobrar(self) -> None:
        self._estado_cobrar.setText("")
        pendientes = self._ctx.svc_cxc.pendientes()
        self._ids_cobrar = list(pendientes.keys())
        self._tabla_cobrar.setRowCount(0)
        for cid in self._ids_cobrar:
            cliente = self._ctx.repo_clientes.por_id(cid)
            fila = self._tabla_cobrar.rowCount()
            self._tabla_cobrar.insertRow(fila)
            self._tabla_cobrar.setItem(fila, 0, QTableWidgetItem(
                cliente.nombre if cliente else f"#{cid}"))
            self._tabla_cobrar.setItem(fila, 1, QTableWidgetItem(
                formato_moneda(pendientes[cid])))

    def _cargar_pagar(self) -> None:
        self._estado_pagar.setText("")
        pendientes = self._ctx.svc_cxp.pendientes()
        self._ids_pagar = list(pendientes.keys())
        self._tabla_pagar.setRowCount(0)
        for pid in self._ids_pagar:
            proveedor = self._ctx.repo_proveedores.por_id(pid)
            fila = self._tabla_pagar.rowCount()
            self._tabla_pagar.insertRow(fila)
            self._tabla_pagar.setItem(fila, 0, QTableWidgetItem(
                proveedor.nombre if proveedor else f"#{pid}"))
            self._tabla_pagar.setItem(fila, 1, QTableWidgetItem(
                formato_moneda(pendientes[pid])))

    def _medios_sin_fiado(self) -> list:
        return [m for m in self._ctx.repo_medios_pago.listar() if m.id != 4]

    def _abonar(self) -> None:
        fila = self._tabla_cobrar.currentRow()
        if not (0 <= fila < len(self._ids_cobrar)):
            return
        cliente_id = self._ids_cobrar[fila]
        dlg = DialogoAbonoPago("Abonar", self._medios_sin_fiado(), self)
        if dlg.exec() != QDialog.Accepted:
            return
        try:
            self._ctx.svc_cxc.abonar(
                cliente_id=cliente_id, monto=dlg.monto(), medio_pago_id=dlg.medio_pago_id(),
                fecha=datetime.now(), usuario_id=self._ctx.usuario_actual_id)
        except ValueError as exc:
            self._estado_cobrar.setText(f"Error: {exc}")
            return
        self._cargar_cobrar()
        self.caja_cambiada.emit()

    def _pagar(self) -> None:
        fila = self._tabla_pagar.currentRow()
        if not (0 <= fila < len(self._ids_pagar)):
            return
        proveedor_id = self._ids_pagar[fila]
        dlg = DialogoAbonoPago("Pagar", self._medios_sin_fiado(), self)
        if dlg.exec() != QDialog.Accepted:
            return
        try:
            self._ctx.svc_cxp.pagar(
                proveedor_id=proveedor_id, monto=dlg.monto(), medio_pago_id=dlg.medio_pago_id(),
                fecha=datetime.now(), usuario_id=self._ctx.usuario_actual_id)
        except ValueError as exc:
            self._estado_pagar.setText(f"Error: {exc}")
            return
        self._cargar_pagar()
        self.caja_cambiada.emit()
