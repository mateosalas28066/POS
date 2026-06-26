"""Pantalla de devoluciones: buscar venta, elegir cantidades, reembolsar."""
from __future__ import annotations

from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QDoubleSpinBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from caja.contexto import EFECTIVO_MEDIO_PAGO_ID, ContextoApp
from caja.dialogos.dialogo_cobro import DialogoCobro
from caja.formato import formato_cantidad, formato_moneda
from core.entidades import ItemDevolucion, Pago, Venta
from core.servicio_venta import (
    CantidadDevueltaExcede, ReembolsoDescuadrado, VentaNoDevolvible, VentaNoEncontrada,
)

CERO = Decimal("0")
_COLS = ["Producto", "Vendido", "Ya devuelto", "Remanente", "A devolver"]


class PantallaDevoluciones(QWidget):
    caja_cambiada = Signal()

    def __init__(self, ctx: ContextoApp) -> None:
        super().__init__()
        self._ctx = ctx
        self._venta: Venta | None = None
        self._spins: list[QDoubleSpinBox] = []
        self._remanentes: list[Decimal] = []

        self._id_venta = QLineEdit()
        self._id_venta.setPlaceholderText("ID de venta")
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

    def al_mostrar(self) -> None:
        self._limpiar()

    def _limpiar(self) -> None:
        self._venta = None
        self._spins = []
        self._remanentes = []
        self._tabla.setRowCount(0)
        self._resumen.setText("")
        self._estado.setText("")
        self._lbl_total.setText(formato_moneda(CERO))
        self._boton_procesar.setEnabled(False)

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
            spin = QDoubleSpinBox()
            spin.setDecimals(3)
            spin.setMaximum(float(remanente))
            spin.valueChanged.connect(self._refrescar_total)
            self._tabla.setCellWidget(fila, 4, spin)
            self._spins.append(spin)
            self._remanentes.append(remanente)
        self._refrescar_total()

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

    def _abrir_reembolso(self) -> None:
        if self._venta is None:
            return
        total = self._total_a_devolver()
        dlg = DialogoCobro(total, self._ctx.repo_medios_pago.listar(),
                           modo="reembolso", efectivo_id=EFECTIVO_MEDIO_PAGO_ID, parent=self)
        if dlg.exec() == DialogoCobro.Accepted:
            self._procesar(dlg.pagos())

    def _procesar(self, pagos: list[Pago]) -> None:
        sesion = self._ctx.repo_sesiones.abierta()
        try:
            self._ctx.svc_devolucion.devolver(
                self._venta.id, self._items_a_devolver(), pagos,
                fecha=datetime.now(),
                caja_sesion_id=sesion.id if sesion else None)
        except (VentaNoEncontrada, VentaNoDevolvible, CantidadDevueltaExcede,
                ReembolsoDescuadrado) as exc:
            self._estado.setText(f"Error: {exc}")
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", str(exc))
            return
        QMessageBox.information(self, "Devolución", "Devolución procesada.")
        self._limpiar()
        self.caja_cambiada.emit()
