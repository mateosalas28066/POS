"""Pantalla de cierre: abrir caja o ver arqueo en vivo y cerrar."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import (
    QDoubleSpinBox, QGridLayout, QHBoxLayout, QLabel, QMessageBox,
    QPushButton, QVBoxLayout, QWidget,
)

from caja.contexto import ContextoApp
from caja.formato import formato_moneda
from caja.widgets import TarjetaKpi
from core.entidades import CajaSesion
from core.servicio_caja import CajaNoAbierta, CajaYaAbierta

CERO = Decimal("0")


class PantallaCierre(QWidget):
    caja_cambiada = Signal()

    def __init__(self, ctx: ContextoApp) -> None:
        super().__init__()
        self._ctx = ctx
        self._layout = QVBoxLayout(self)
        # widgets persistentes para test/acceso
        self._monto_inicial = QDoubleSpinBox()
        self._monto_inicial.setMaximum(99_999_999); self._monto_inicial.setDecimals(0)
        self._monto_contado = QDoubleSpinBox()
        self._monto_contado.setMaximum(99_999_999); self._monto_contado.setDecimals(0)
        self._monto_contado.valueChanged.connect(self._recalcular_arqueo)
        self._boton_abrir = QPushButton("Abrir caja"); self._boton_abrir.setObjectName("primario")
        self._boton_abrir.clicked.connect(self._abrir)
        self._boton_cerrar = QPushButton("Cerrar caja"); self._boton_cerrar.setObjectName("primario")
        self._boton_cerrar.clicked.connect(self._cerrar)
        self._kpi_inicial = TarjetaKpi("Monto inicial")
        self._kpi_efectivo = TarjetaKpi("Ventas efectivo")
        self._kpi_esperado = TarjetaKpi("Esperado")
        self._kpi_diferencia = TarjetaKpi("Diferencia")
        self._estado = QLabel(""); self._estado.setObjectName("error")

    def al_mostrar(self) -> None:
        self._limpiar_layout()
        sesion = self._ctx.repo_sesiones.abierta()
        if sesion is None:
            self._montar_apertura()
        else:
            self._montar_arqueo(sesion)

    def _limpiar_layout(self) -> None:
        self._vaciar(self._layout)

    @staticmethod
    def _vaciar(layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
            elif item.layout() is not None:
                PantallaCierre._vaciar(item.layout())

    def _montar_apertura(self) -> None:
        self._layout.addWidget(QLabel("Caja cerrada"))
        self._layout.addWidget(QLabel("Monto inicial"))
        self._layout.addWidget(self._monto_inicial)
        self._layout.addWidget(self._boton_abrir)
        self._layout.addWidget(self._estado)
        self._layout.addStretch(1)

    def _montar_arqueo(self, sesion: CajaSesion) -> None:
        grid = QGridLayout()
        grid.addWidget(self._kpi_inicial, 0, 0)
        grid.addWidget(self._kpi_efectivo, 0, 1)
        grid.addWidget(self._kpi_esperado, 1, 0)
        grid.addWidget(self._kpi_diferencia, 1, 1)
        self._layout.addWidget(QLabel(f"Caja #{sesion.id} abierta"))
        self._layout.addLayout(grid)
        fila = QHBoxLayout()
        fila.addWidget(QLabel("Efectivo contado"))
        fila.addWidget(self._monto_contado)
        self._layout.addLayout(fila)
        self._layout.addWidget(self._boton_cerrar)
        self._layout.addWidget(self._estado)
        self._layout.addStretch(1)
        self._kpi_inicial.set_valor(formato_moneda(sesion.monto_inicial))
        self._recalcular_arqueo()

    @Slot()
    def _recalcular_arqueo(self) -> None:
        sesion = self._ctx.repo_sesiones.abierta()
        if sesion is None:
            return
        contado = Decimal(str(int(self._monto_contado.value())))
        arqueo = self._ctx.svc_caja.arqueo(sesion.id, contado)
        self._kpi_efectivo.set_valor(formato_moneda(arqueo.efectivo_ventas))
        self._kpi_esperado.set_valor(formato_moneda(arqueo.esperado))
        self._kpi_diferencia.set_valor(formato_moneda(arqueo.diferencia))
        self._kpi_diferencia.set_estado("positivo" if arqueo.diferencia >= CERO else "alerta")

    @Slot()
    def _abrir(self) -> None:
        try:
            self._ctx.svc_caja.abrir(
                fecha=datetime.now(),
                monto_inicial=Decimal(str(int(self._monto_inicial.value()))))
        except (CajaYaAbierta, ValueError) as exc:
            self._estado.setText(f"Error: {exc}")
            return
        self.al_mostrar()
        self.caja_cambiada.emit()

    @Slot()
    def _cerrar(self) -> None:
        sesion = self._ctx.repo_sesiones.abierta()
        if sesion is None:
            return
        try:
            self._ctx.svc_caja.cerrar(
                sesion_id=sesion.id, fecha=datetime.now(),
                monto_contado=Decimal(str(int(self._monto_contado.value()))))
        except (CajaNoAbierta, ValueError) as exc:
            self._estado.setText(f"Error: {exc}")
            return
        QMessageBox.information(self, "Cierre", "Caja cerrada.")
        self.al_mostrar()
        self.caja_cambiada.emit()
