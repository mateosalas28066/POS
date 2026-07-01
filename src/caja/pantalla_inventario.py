"""Pantalla de inventario: tabla de productos con stock + CRUD y movimientos."""
from __future__ import annotations

from PySide6.QtCore import Slot
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QHBoxLayout, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from caja.contexto import ContextoApp
from caja.dialogos.dialogo_movimiento import DialogoMovimiento
from caja.dialogos.dialogo_producto import DialogoProducto
from caja.formato import formato_cantidad, formato_moneda
from core.entidades import MovimientoInventario, Producto
from core.permisos import ACCION_EDITAR_PRODUCTOS, puede

_COLS = ["Código", "Nombre", "Categoría", "Precio", "Costo", "Stock", "Unidad"]
_COLOR_ALERTA = QColor("#F59E0B")


class PantallaInventario(QWidget):
    def __init__(self, ctx: ContextoApp) -> None:
        super().__init__()
        self._ctx = ctx
        self._productos: list[Producto] = []

        self._busqueda = QLineEdit()
        self._busqueda.setPlaceholderText("Buscar por nombre o código…")
        self._busqueda.textChanged.connect(self._filtrar)

        self._boton_nuevo = QPushButton("Nuevo producto")
        self._boton_nuevo.clicked.connect(self._crear_producto)
        self._boton_editar = QPushButton("Editar")
        self._boton_editar.clicked.connect(self._editar_producto)
        self._boton_mov = QPushButton("Movimiento")
        self._boton_mov.clicked.connect(self._registrar_movimiento)

        rol = ctx.usuario_actual.rol if ctx.usuario_actual else "cajero"
        puede_editar = puede(rol, ACCION_EDITAR_PRODUCTOS)
        self._boton_nuevo.setVisible(puede_editar)
        self._boton_editar.setVisible(puede_editar)

        barra = QHBoxLayout()
        barra.addWidget(self._busqueda, 1)
        barra.addWidget(self._boton_nuevo)
        barra.addWidget(self._boton_editar)
        barra.addWidget(self._boton_mov)

        self._tabla = QTableWidget(0, len(_COLS))
        self._tabla.setHorizontalHeaderLabels(_COLS)
        self._tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self._tabla.setSelectionBehavior(QTableWidget.SelectRows)

        layout = QVBoxLayout(self)
        layout.addLayout(barra)
        layout.addWidget(self._tabla)

    def al_mostrar(self) -> None:
        self._productos = self._ctx.repo_productos.listar()
        nombres_cat = {c.id: c.nombre for c in self._ctx.repo_categorias.listar()}
        self._tabla.setRowCount(0)
        for p in self._productos:
            fila = self._tabla.rowCount()
            self._tabla.insertRow(fila)
            stock = self._ctx.repo_inventario.stock_de(p.id)
            celdas = [
                p.codigo_barras, p.nombre, nombres_cat.get(p.categoria_id, "—"),
                formato_moneda(p.precio), formato_moneda(p.costo),
                formato_cantidad(stock, p.unidad), p.unidad,
            ]
            for col, texto in enumerate(celdas):
                item = QTableWidgetItem(texto)
                if col == 5 and stock <= 0:
                    item.setForeground(_COLOR_ALERTA)
                self._tabla.setItem(fila, col, item)
        self._filtrar()

    @Slot()
    def _filtrar(self) -> None:
        texto = self._busqueda.text().strip().lower()
        for fila, p in enumerate(self._productos):
            visible = (not texto) or (texto in p.nombre.lower()
                                      or texto in p.codigo_barras.lower())
            self._tabla.setRowHidden(fila, not visible)

    def _producto_seleccionado(self) -> Producto | None:
        fila = self._tabla.currentRow()
        if 0 <= fila < len(self._productos):
            return self._productos[fila]
        return None

    @Slot()
    def _crear_producto(self) -> None:
        dlg = DialogoProducto(self._ctx.repo_categorias.listar(),
                              self._ctx.repo_impuestos.listar(), parent=self)
        if dlg.exec() == DialogoProducto.Accepted:
            self._guardar_producto(dlg.producto())
            self.al_mostrar()

    @Slot()
    def _editar_producto(self) -> None:
        p = self._producto_seleccionado()
        if p is None:
            return
        dlg = DialogoProducto(self._ctx.repo_categorias.listar(),
                              self._ctx.repo_impuestos.listar(), producto=p, parent=self)
        if dlg.exec() == DialogoProducto.Accepted:
            self._guardar_producto(dlg.producto())
            self.al_mostrar()

    def _guardar_producto(self, producto: Producto) -> None:
        if producto.id is None:
            self._ctx.repo_productos.guardar(producto)
        else:
            self._ctx.repo_productos.actualizar(producto)

    @Slot()
    def _registrar_movimiento(self) -> None:
        p = self._producto_seleccionado()
        if p is None:
            return
        dlg = DialogoMovimiento(p.id, parent=self)
        if dlg.exec() == DialogoMovimiento.Accepted:
            self._aplicar_movimiento(dlg.movimiento())
            self.al_mostrar()

    def _aplicar_movimiento(self, movimiento: MovimientoInventario) -> None:
        self._ctx.repo_inventario.registrar(movimiento)
