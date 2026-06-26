"""Shell de la app: rail de navegación + QStackedWidget + barra de estado."""
from __future__ import annotations

from decimal import Decimal

from PySide6.QtWidgets import (
    QButtonGroup, QHBoxLayout, QMainWindow, QStackedWidget, QVBoxLayout, QWidget,
)

from caja.contexto import EFECTIVO_MEDIO_PAGO_ID, ContextoApp
from caja.formato import formato_moneda
from caja.pantalla_cierre import PantallaCierre
from caja.pantalla_clientes import PantallaClientes
from caja.pantalla_devoluciones import PantallaDevoluciones
from caja.pantalla_inventario import PantallaInventario
from caja.pantalla_reportes import PantallaReportes
from caja.pantalla_venta import PantallaVenta
from caja.tema import icono
from caja.widgets import BotonRail

# (icono, tooltip, factory)
_DEFINICION = [
    ("venta", "Venta", PantallaVenta),
    ("inventario", "Inventario", PantallaInventario),
    ("clientes", "Clientes", PantallaClientes),
    ("devoluciones", "Devoluciones", PantallaDevoluciones),
    ("reportes", "Reportes", PantallaReportes),
    ("cierre", "Cierre", PantallaCierre),
]


class VentanaPrincipal(QMainWindow):
    def __init__(self, ctx: ContextoApp) -> None:
        super().__init__()
        self._ctx = ctx
        self.setWindowTitle("POS — Carnes y Frutas")
        self.resize(1100, 720)

        self._stack = QStackedWidget()
        self._botones: list[BotonRail] = []
        self._pantallas: list[QWidget] = []
        self._grupo = QButtonGroup(self)
        self._grupo.setExclusive(True)

        rail = QWidget(); rail.setObjectName("rail"); rail.setFixedWidth(60)
        rail_layout = QVBoxLayout(rail)
        rail_layout.setContentsMargins(0, 8, 0, 8)

        for i, (ic, tip, factory) in enumerate(_DEFINICION):
            pantalla = self._construir_pantalla(factory)
            self._pantallas.append(pantalla)
            self._stack.addWidget(pantalla)
            boton = BotonRail(icono(ic), tip)
            boton.clicked.connect(lambda _=False, idx=i: self._ir_a(idx))
            self._grupo.addButton(boton, i)
            rail_layout.addWidget(boton)
            self._botones.append(boton)
        rail_layout.addStretch(1)

        central = QWidget(); central.setObjectName("fondo")
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(rail)
        layout.addWidget(self._stack, 1)
        self.setCentralWidget(central)

        self._botones[0].setChecked(True)
        self._ir_a(0)

    def _construir_pantalla(self, factory) -> QWidget:
        if factory is PantallaClientes:
            pantalla = factory(self._ctx.svc_clientes)
        else:
            pantalla = factory(self._ctx)
        if hasattr(pantalla, "caja_cambiada"):
            pantalla.caja_cambiada.connect(self._refrescar_estado)
        return pantalla

    def _ir_a(self, indice: int) -> None:
        self._stack.setCurrentIndex(indice)
        pantalla = self._pantallas[indice]
        if hasattr(pantalla, "al_mostrar"):
            pantalla.al_mostrar()
        self._refrescar_estado()

    def _refrescar_estado(self) -> None:
        sesion = self._ctx.repo_sesiones.abierta()
        if sesion is None:
            self.statusBar().showMessage("Caja cerrada")
            return
        efectivo = self._ctx.repo_ventas.totales_por_medio(sesion.id).get(EFECTIVO_MEDIO_PAGO_ID, None)
        monto = efectivo if efectivo is not None else Decimal("0")
        self.statusBar().showMessage(
            f"● Caja #{sesion.id} abierta  ·  Efectivo: {formato_moneda(monto)}")
