"""Pantalla de venta: catálogo (izq) + carrito (der). Lógica en ServicioVenta."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGridLayout, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QMessageBox,
    QPushButton, QScrollArea, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from caja.contexto import EFECTIVO_MEDIO_PAGO_ID, ContextoApp
from caja.dialogos.dialogo_cobro import DialogoCobro
from caja.formato import formato_cantidad, formato_moneda
from caja.widgets import TarjetaProducto
from core.entidades import Pago, Producto
from core.servicio_venta import ProductoNoEncontrado, PesoRequerido

CERO = Decimal("0")
_COLS_GRID = 4


class PantallaVenta(QWidget):
    caja_cambiada = Signal()

    def __init__(self, ctx: ContextoApp) -> None:
        super().__init__()
        self._ctx = ctx
        self._venta = ctx.nueva_venta()
        self._tarjetas: list[TarjetaProducto] = []
        self._categoria_filtro: int | None = None

        # --- catálogo (izquierda) ---
        self._busqueda = QLineEdit()
        self._busqueda.setPlaceholderText("Buscar producto…")
        self._busqueda.textChanged.connect(self._aplicar_filtro)

        self._fila_chips = QHBoxLayout()
        self._cont_grid = QWidget()
        self._grid = QGridLayout(self._cont_grid)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._cont_grid)

        izquierda = QVBoxLayout()
        izquierda.addWidget(self._busqueda)
        izquierda.addLayout(self._fila_chips)
        izquierda.addWidget(scroll)

        # --- carrito (derecha) ---
        panel = QWidget()
        panel.setObjectName("panel")
        self._carrito = QTableWidget(0, 3)
        self._carrito.setHorizontalHeaderLabels(["Descripción", "Cant.", "Subtotal"])
        self._carrito.setEditTriggers(QTableWidget.NoEditTriggers)
        self._lbl_total = QLabel(formato_moneda(CERO))
        self._lbl_total.setObjectName("kpi-valor")
        boton_quitar = QPushButton("Quitar ítem")
        boton_quitar.clicked.connect(self._quitar_seleccionado)
        self._boton_cobrar = QPushButton("Cobrar")
        self._boton_cobrar.setObjectName("primario")
        self._boton_cobrar.clicked.connect(self._cobrar)
        self._estado = QLabel("")
        self._estado.setObjectName("error")

        self._escaneo = QLineEdit()
        self._escaneo.setObjectName("escaneo")
        self._escaneo.setPlaceholderText("Escanear…")
        self._escaneo.returnPressed.connect(self._procesar_escaneo)

        der = QVBoxLayout(panel)
        der.addWidget(QLabel("Carrito"))
        der.addWidget(self._carrito)
        der.addWidget(self._escaneo)
        der.addWidget(self._estado)
        der.addWidget(QLabel("Total"))
        der.addWidget(self._lbl_total)
        der.addWidget(boton_quitar)
        der.addWidget(self._boton_cobrar)

        raiz = QHBoxLayout(self)
        raiz.addLayout(izquierda, 65)
        raiz.addWidget(panel, 35)

    # ---- ciclo de vida ----
    def al_mostrar(self) -> None:
        self._construir_chips()
        self._construir_grid()
        self._refrescar_carrito()
        self._escaneo.setFocus()

    # ---- catálogo ----
    def _construir_chips(self) -> None:
        while self._fila_chips.count():
            item = self._fila_chips.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        todas = QPushButton("Todas")
        todas.setObjectName("chip")
        todas.setCheckable(True)
        todas.setChecked(True)
        todas.clicked.connect(lambda: self._filtrar_categoria(None))
        self._fila_chips.addWidget(todas)
        for c in self._ctx.repo_categorias.listar():
            chip = QPushButton(c.nombre)
            chip.setObjectName("chip")
            chip.setCheckable(True)
            chip.clicked.connect(lambda _=False, cid=c.id: self._filtrar_categoria(cid))
            self._fila_chips.addWidget(chip)

    def _construir_grid(self) -> None:
        for t in self._tarjetas:
            t.deleteLater()
        self._tarjetas = []
        nombres_cat = {c.id: c.nombre for c in self._ctx.repo_categorias.listar()}
        for i, p in enumerate(self._ctx.repo_productos.listar()):
            tarjeta = TarjetaProducto(p, nombres_cat.get(p.categoria_id, ""))
            tarjeta.seleccionado.connect(self._agregar_producto)
            self._grid.addWidget(tarjeta, i // _COLS_GRID, i % _COLS_GRID)
            self._tarjetas.append(tarjeta)
        self._aplicar_filtro()

    def _filtrar_categoria(self, categoria_id: int | None) -> None:
        self._categoria_filtro = categoria_id
        for chip in (self._fila_chips.itemAt(i).widget()
                     for i in range(self._fila_chips.count())):
            chip.setChecked(False)
        self._aplicar_filtro()

    def _aplicar_filtro(self) -> None:
        texto = self._busqueda.text().strip().lower()
        for t in self._tarjetas:
            p = t._producto
            visible = (self._categoria_filtro is None or p.categoria_id == self._categoria_filtro)
            if texto:
                visible = visible and (texto in p.nombre.lower() or texto in p.codigo_barras.lower())
            t.setVisible(visible)

    # ---- carrito ----
    def _agregar_producto(self, producto: Producto) -> None:
        peso = None
        if producto.vendido_por_peso:
            valor, ok = QInputDialog.getDouble(
                self, "Peso", f"Kg de {producto.nombre}:", 1.0, 0.001, 9999, 3)
            if not ok:
                return
            peso = Decimal(str(valor))
        try:
            self._venta.agregar(producto.codigo_barras, peso_kg=peso)
        except (ProductoNoEncontrado, PesoRequerido, ValueError) as exc:
            self._estado.setText(str(exc))
            return
        self._estado.setText("")
        self._refrescar_carrito()

    def _procesar_escaneo(self) -> None:
        codigo = self._escaneo.text().strip()
        self._escaneo.clear()
        if not codigo:
            return
        try:
            self._venta.agregar_escaneado(codigo, self._ctx.formato_gs1)
        except (ProductoNoEncontrado, PesoRequerido, ValueError) as exc:
            self._estado.setText(f"{exc} — código: {codigo}")
            self._escaneo.setFocus()
            return
        self._estado.setText("")
        self._refrescar_carrito()
        self._escaneo.setFocus()

    def _refrescar_carrito(self) -> None:
        lineas = self._venta.lineas
        self._carrito.setRowCount(0)
        for linea in lineas:
            fila = self._carrito.rowCount()
            self._carrito.insertRow(fila)
            self._carrito.setItem(fila, 0, QTableWidgetItem(linea.descripcion))
            self._carrito.setItem(fila, 1, QTableWidgetItem(
                formato_cantidad(linea.cantidad_o_peso, "")))
            self._carrito.setItem(fila, 2, QTableWidgetItem(formato_moneda(linea.subtotal)))
        self._lbl_total.setText(formato_moneda(self._total_actual()))
        self._actualizar_boton_cobrar()

    def _total_actual(self) -> Decimal:
        return self._venta.total

    def _quitar_seleccionado(self) -> None:
        fila = self._carrito.currentRow()
        if fila < 0:
            return
        # ServicioVenta no expone quitar: reconstruir sin la línea.
        # peso vs unidad lo decide el flag del producto (fuente de verdad), no el valor.
        lineas = list(self._venta.lineas)
        del lineas[fila]
        self._venta = self._ctx.nueva_venta()
        for ln in lineas:
            producto = self._ctx.repo_productos.por_id(ln.producto_id)
            if producto.vendido_por_peso:
                self._venta.agregar(producto.codigo_barras, peso_kg=ln.cantidad_o_peso)
            else:
                self._venta.agregar(producto.codigo_barras, cantidad=ln.cantidad_o_peso)
        self._refrescar_carrito()

    def _actualizar_boton_cobrar(self) -> None:
        hay_caja = self._ctx.repo_sesiones.abierta() is not None
        self._boton_cobrar.setEnabled(hay_caja and bool(self._venta.lineas))

    # ---- cobro ----
    def _cobrar(self) -> None:
        sesion = self._ctx.repo_sesiones.abierta()
        if sesion is None or not self._venta.lineas:
            return
        dlg = DialogoCobro(self._total_actual(), self._ctx.repo_medios_pago.listar(),
                           modo="cobro", efectivo_id=EFECTIVO_MEDIO_PAGO_ID, parent=self)
        if dlg.exec() != DialogoCobro.Accepted:
            return
        self._registrar_pagos(dlg.pagos(), sesion.id)

    def _registrar_pagos(self, pagos: list[Pago], sesion_id: int) -> None:
        venta = self._venta.confirmar(fecha=datetime.now(), caja_sesion_id=sesion_id)
        try:
            self._ctx.svc_registro.registrar(venta, pagos)
        except Exception as exc:  # noqa: BLE001 — error inesperado al cajero
            QMessageBox.critical(self, "Error al registrar", str(exc))
            return
        self._venta = self._ctx.nueva_venta()
        self._refrescar_carrito()
        self._escaneo.setFocus()
        self.caja_cambiada.emit()
