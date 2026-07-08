"""Diálogo de devolución: buscar factura, elegir cantidades, reembolsar.

Reusa `ServicioDevolucion` de `core` (misma regla que antes usaba
`PantallaDevoluciones`); aquí solo cambia el envoltorio de UI a un `QDialog`
que se abre desde la pantalla de Venta.
"""
from __future__ import annotations

from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from caja.contexto import EFECTIVO_MEDIO_PAGO_ID, ContextoApp
from caja.dialogos.dialogo_cobro import DialogoCobro
from caja.formato import formato_cantidad, formato_moneda
from caja.widgets import DecimalSpinBoxPos
from core.entidades import Devolucion, ItemDevolucion, Pago, Venta
from core.servicio_venta import (
    CantidadDevueltaExcede, ReembolsoDescuadrado, VentaNoDevolvible, VentaNoEncontrada,
)

CERO = Decimal("0")
_COLS = ["Producto", "Vendido", "Ya devuelto", "Remanente", "A devolver"]


class DialogoDevolucion(QDialog):
    """Devuelve líneas de una factura y reembolsa, reusando ServicioDevolucion."""

    caja_cambiada = Signal()

    def __init__(self, ctx: ContextoApp, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Devolución")
        self._ctx = ctx
        self._venta: Venta | None = None
        self._spins: list[DecimalSpinBoxPos] = []
        self._remanentes: list[Decimal] = []

        self._id_venta = QLineEdit()
        self._id_venta.setPlaceholderText("ID de venta / factura")
        boton_buscar = QPushButton("Buscar")
        boton_buscar.clicked.connect(self._buscar)
        barra = QHBoxLayout()
        barra.addWidget(self._id_venta, 1)
        barra.addWidget(boton_buscar)

        self._resumen = QLabel("")
        self._resumen.setObjectName("secundario")
        self._tabla = QTableWidget(0, len(_COLS))
        self._tabla.setHorizontalHeaderLabels(_COLS)
        self._tabla.setEditTriggers(QTableWidget.NoEditTriggers)

        self._lbl_total = QLabel(formato_moneda(CERO))
        self._lbl_total.setObjectName("kpi-valor")
        self._boton_procesar = QPushButton("Procesar devolución")
        self._boton_procesar.setObjectName("primario")
        self._boton_procesar.clicked.connect(self._abrir_reembolso)
        self._boton_procesar.setEnabled(False)
        self._estado = QLabel("")
        self._estado.setObjectName("error")

        layout = QVBoxLayout(self)
        layout.addLayout(barra)
        layout.addWidget(self._resumen)
        layout.addWidget(self._tabla)
        layout.addWidget(self._estado)
        layout.addWidget(QLabel("Total a reembolsar"))
        layout.addWidget(self._lbl_total)
        layout.addWidget(self._boton_procesar)

    # ---- carga de la factura ----
    def cargar_factura(self, venta_id: int) -> None:
        """Carga programática de una venta por id (equivale a teclear el id y Buscar)."""
        self._id_venta.setText(str(venta_id))
        self._buscar()

    @Slot()
    def _buscar(self) -> None:
        self._limpiar()
        texto = self._id_venta.text().strip()
        if not texto.isdigit():
            self._estado.setText("ID inválido")
            return
        venta = self._ctx.repo_ventas.por_id(int(texto))
        if venta is None:
            self._estado.setText("Venta no encontrada")
            return
        if venta.estado in ("anulada", "devuelta"):
            self._estado.setText(f"Venta en estado '{venta.estado}', no devolvible")
            return
        self._venta = venta
        self._resumen.setText(
            f"Venta #{venta.id} · {venta.estado} · {formato_moneda(venta.total)}")
        ya_devuelto = self._ctx.repo_devoluciones.devuelto_por_linea(venta.id)
        for linea in venta.lineas:
            remanente = linea.cantidad_o_peso - ya_devuelto.get(linea.id, CERO)
            fila = self._tabla.rowCount()
            self._tabla.insertRow(fila)
            self._tabla.setItem(fila, 0, QTableWidgetItem(linea.descripcion))
            self._tabla.setItem(fila, 1, QTableWidgetItem(
                formato_cantidad(linea.cantidad_o_peso, "")))
            self._tabla.setItem(fila, 2, QTableWidgetItem(
                formato_cantidad(ya_devuelto.get(linea.id, CERO), "")))
            self._tabla.setItem(fila, 3, QTableWidgetItem(formato_cantidad(remanente, "")))
            spin = DecimalSpinBoxPos()
            spin.setDecimals(3)
            spin.setMaximum(float(remanente))
            spin.valueChanged.connect(self._refrescar_total)
            self._tabla.setCellWidget(fila, 4, spin)
            self._spins.append(spin)
            self._remanentes.append(remanente)
        self._refrescar_total()

    def _limpiar(self) -> None:
        self._venta = None
        self._spins = []
        self._remanentes = []
        self._tabla.setRowCount(0)
        self._resumen.setText("")
        self._estado.setText("")
        self._lbl_total.setText(formato_moneda(CERO))
        self._boton_procesar.setEnabled(False)

    # ---- selección de cantidades ----
    def marcar_devolucion(self, linea_idx: int, cantidad) -> None:
        """Marca cuánto devolver en una línea (por índice de la factura cargada)."""
        self._spins[linea_idx].setValue(float(cantidad))

    def _items_a_devolver(self) -> list[ItemDevolucion]:
        items: list[ItemDevolucion] = []
        for linea, spin in zip(self._venta.lineas, self._spins):
            cantidad = Decimal(str(spin.value()))
            if cantidad > CERO:
                items.append(ItemDevolucion(venta_linea_id=linea.id, cantidad_o_peso=cantidad))
        return items

    def _total_a_devolver(self) -> Decimal:
        total = CERO
        for linea, spin in zip(self._venta.lineas, self._spins):
            cantidad = Decimal(str(spin.value()))
            if cantidad > CERO and linea.cantidad_o_peso > CERO:
                ratio = cantidad / linea.cantidad_o_peso
                total += (linea.subtotal * ratio).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        return total

    def _refrescar_total(self) -> None:
        if self._venta is None:
            return
        total = self._total_a_devolver()
        self._lbl_total.setText(formato_moneda(total))
        self._boton_procesar.setEnabled(total > CERO)

    # ---- confirmación ----
    @Slot()
    def _abrir_reembolso(self) -> None:
        if self._venta is None:
            return
        total = self._total_a_devolver()
        dlg = DialogoCobro(total, self._ctx.repo_medios_pago.listar(),
                           modo="reembolso", efectivo_id=EFECTIVO_MEDIO_PAGO_ID, parent=self)
        if dlg.exec() != DialogoCobro.Accepted:
            return
        resultado = self.confirmar(dlg.pagos())
        if resultado is not None:
            QMessageBox.information(self, "Devolución", "Devolución procesada.")
            self.accept()

    def confirmar(self, pagos: list[Pago] | None = None) -> Devolucion | None:
        """Procesa la devolución con `ServicioDevolucion`. Si no se pasan pagos,
        reembolsa el total en efectivo. Devuelve la `Devolucion` o None si falló."""
        if self._venta is None:
            return None
        total = self._total_a_devolver()
        if pagos is None:
            pagos = [Pago(medio_pago_id=EFECTIVO_MEDIO_PAGO_ID, monto=total)]
        sesion = self._ctx.repo_sesiones.abierta()
        try:
            guardada = self._ctx.svc_devolucion.devolver(
                self._venta.id, self._items_a_devolver(), pagos,
                fecha=datetime.now(),
                caja_sesion_id=sesion.id if sesion else None,
                usuario_id=self._ctx.usuario_actual_id)
        except (VentaNoEncontrada, VentaNoDevolvible, CantidadDevueltaExcede,
                ReembolsoDescuadrado) as exc:
            self._estado.setText(f"Error: {exc}")
            return None
        self.caja_cambiada.emit()
        return guardada
