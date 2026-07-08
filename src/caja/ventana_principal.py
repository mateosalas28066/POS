"""Shell de la app: rail de navegación + QStackedWidget + barra de estado."""
from __future__ import annotations

from decimal import Decimal

from PySide6.QtCore import QTimer, Slot
from PySide6.QtWidgets import (
    QButtonGroup, QDialog, QHBoxLayout, QLabel, QMainWindow, QPushButton,
    QStackedWidget, QTableView, QVBoxLayout, QWidget,
)

from caja.contexto import EFECTIVO_MEDIO_PAGO_ID, ContextoApp
from caja.dialogos.dialogo_cambio_password import DialogoCambioPassword
from caja.formato import formato_moneda
from caja.pantalla_cierre import PantallaCierre
from caja.pantalla_clientes import PantallaClientes
from caja.pantalla_compras import PantallaCompras
from caja.pantalla_cuentas import PantallaCuentas
from caja.pantalla_despiece import PantallaDespiece
from caja.pantalla_devoluciones import PantallaDevoluciones
from caja.pantalla_gastos import PantallaGastos
from caja.pantalla_inventario import PantallaInventario
from caja.pantalla_proveedores import PantallaProveedores
from caja.pantalla_reportes import PantallaReportes
from caja.pantalla_usuarios import PantallaUsuarios
from caja.pantalla_venta import PantallaVenta
from caja.tema import icono
from caja.widgets import BotonRail, configura_tabla
from core.permisos import ACCION_GESTIONAR_USUARIOS, puede

# (icono, tooltip, factory, permiso)
_DEFINICION = [
    ("venta", "Venta", PantallaVenta, None),
    ("inventario", "Inventario", PantallaInventario, None),
    ("clientes", "Clientes", PantallaClientes, None),
    ("clientes", "Proveedores", PantallaProveedores, None),
    ("inventario", "Compras", PantallaCompras, None),
    ("clientes", "Cuentas", PantallaCuentas, None),
    ("inventario", "Gastos", PantallaGastos, None),
    ("inventario", "Despiece", PantallaDespiece, None),
    ("devoluciones", "Devoluciones", PantallaDevoluciones, None),
    ("reportes", "Reportes", PantallaReportes, None),
    ("cierre", "Cierre", PantallaCierre, None),
    ("clientes", "Usuarios", PantallaUsuarios, ACCION_GESTIONAR_USUARIOS),
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

        rol = ctx.usuario_actual.rol if ctx.usuario_actual else "cajero"
        visibles = [d for d in _DEFINICION if d[3] is None or puede(rol, d[3])]
        for i, (ic, tip, factory, _permiso) in enumerate(visibles):
            pantalla = self._construir_pantalla(factory)
            self._pantallas.append(pantalla)
            self._stack.addWidget(pantalla)
            boton = BotonRail(icono(ic), tip)
            boton.clicked.connect(lambda _=False, idx=i: self._ir_a(idx))
            self._grupo.addButton(boton, i)
            rail_layout.addWidget(boton)
            self._botones.append(boton)
        rail_layout.addStretch(1)
        if ctx.usuario_actual is not None:
            boton_pwd = BotonRail(icono("clientes"), "Cambiar mi contraseña")
            boton_pwd.setCheckable(False)
            boton_pwd.clicked.connect(self._cambiar_password)
            rail_layout.addWidget(boton_pwd)

        central = QWidget(); central.setObjectName("fondo")
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(rail)
        layout.addWidget(self._stack, 1)
        self.setCentralWidget(central)

        # Legibilidad uniforme: todas las tablas de las pantallas ajustan columnas
        # al ancho y envuelven texto largo (evita que las celdas corten palabras).
        for tabla in self.findChildren(QTableView):
            configura_tabla(tabla)

        # Aviso no bloqueante de precios actualizados desde la nube (sync híbrido).
        self._novedades: list[dict] = []
        self._boton_novedades = QPushButton()
        self._boton_novedades.setFlat(True)
        self._boton_novedades.setVisible(False)
        self._boton_novedades.clicked.connect(self._mostrar_novedades)
        self.statusBar().addPermanentWidget(self._boton_novedades)
        if self._ctx.repo_replica is not None:
            self._timer_novedades = QTimer(self)
            self._timer_novedades.timeout.connect(self._revisar_novedades)
            self._timer_novedades.start(5000)

        self._botones[0].setChecked(True)
        self._ir_a(0)

    def _construir_pantalla(self, factory) -> QWidget:
        if factory is PantallaClientes:
            pantalla = factory(self._ctx.svc_clientes)
        elif factory is PantallaProveedores:
            pantalla = factory(self._ctx.svc_proveedores)
        elif factory is PantallaUsuarios:
            pantalla = factory(self._ctx.svc_usuarios)
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

    @Slot()
    def _cambiar_password(self) -> None:
        dlg = DialogoCambioPassword(
            self._ctx.svc_usuarios, self._ctx.usuario_actual.nombre, self)
        if dlg.exec() == QDialog.Accepted:
            self.statusBar().showMessage("Contraseña actualizada", 5000)

    @Slot()
    def _refrescar_estado(self) -> None:
        sesion = self._ctx.repo_sesiones.abierta()
        if sesion is None:
            self.statusBar().showMessage("Caja cerrada")
            return
        efectivo = self._ctx.repo_ventas.totales_por_medio(sesion.id).get(EFECTIVO_MEDIO_PAGO_ID, None)
        monto = efectivo if efectivo is not None else Decimal("0")
        self.statusBar().showMessage(
            f"● Caja #{sesion.id} abierta  ·  Efectivo: {formato_moneda(monto)}")

    @Slot()
    def _revisar_novedades(self) -> None:
        """Timer: consulta precios cambiados en la nube y actualiza el aviso de la barra."""
        self._novedades = self._ctx.repo_replica.novedades_pendientes()
        if self._novedades:
            self._boton_novedades.setText(f"🔔 {len(self._novedades)} precio(s) actualizados")
            self._boton_novedades.setVisible(True)
        else:
            self._boton_novedades.setVisible(False)

    @Slot()
    def _mostrar_novedades(self) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle("Precios actualizados desde la nube")
        lay = QVBoxLayout(dlg)
        lay.addWidget(QLabel("Estos precios cambiaron en la nube y ya están aplicados:"))
        for n in self._novedades:
            antes = "—" if n["precio_anterior"] is None else formato_moneda(n["precio_anterior"])
            lay.addWidget(QLabel(f"•  {n['nombre']}:  {antes}  →  {formato_moneda(n['precio_nuevo'])}"))
        boton = QPushButton("Entendido")
        boton.clicked.connect(dlg.accept)
        lay.addWidget(boton)
        dlg.exec()
        self._ctx.repo_replica.marcar_novedades_vistas()
        self._boton_novedades.setVisible(False)
        actual = self._pantallas[self._stack.currentIndex()]
        if hasattr(actual, "al_mostrar"):
            actual.al_mostrar()             # refresca precios en la pantalla visible
