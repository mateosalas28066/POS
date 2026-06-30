import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from datetime import datetime  # noqa: E402
from decimal import Decimal  # noqa: E402

from PySide6.QtWidgets import QApplication  # noqa: E402

from caja.contexto import ContextoApp  # noqa: E402
from caja.pantalla_venta import PantallaVenta  # noqa: E402


def _ctx():
    return ContextoApp.crear(":memory:")


def test_pantalla_construye_y_lista_productos():
    _app = QApplication.instance() or QApplication([])
    win = PantallaVenta(_ctx())
    win.al_mostrar()
    assert len(win._tarjetas) >= 4


def test_agregar_producto_actualiza_carrito_y_total():
    _app = QApplication.instance() or QApplication([])
    ctx = _ctx()
    win = PantallaVenta(ctx)
    win.al_mostrar()
    producto = ctx.repo_productos.por_codigo("7700006")  # Arroz, por unidad
    win._agregar_producto(producto)
    assert win._carrito.rowCount() == 1
    assert win._total_actual() == Decimal("2500")


def test_cobrar_deshabilitado_sin_caja_abierta():
    _app = QApplication.instance() or QApplication([])
    ctx = _ctx()
    win = PantallaVenta(ctx)
    win.al_mostrar()
    producto = ctx.repo_productos.por_codigo("7700006")
    win._agregar_producto(producto)
    assert win._boton_cobrar.isEnabled() is False  # no hay caja abierta


def test_cobrar_registra_venta_con_caja_abierta():
    _app = QApplication.instance() or QApplication([])
    ctx = _ctx()
    ctx.svc_caja.abrir(fecha=datetime.now(), monto_inicial=Decimal("0"))
    win = PantallaVenta(ctx)
    win.al_mostrar()
    producto = ctx.repo_productos.por_codigo("7700006")
    win._agregar_producto(producto)
    sesion = ctx.repo_sesiones.abierta()
    win._registrar_pagos([__import__("core.entidades", fromlist=["Pago"]).Pago(
        medio_pago_id=1, monto=Decimal("2500"))], sesion.id)
    assert win._carrito.rowCount() == 0  # carrito limpio tras cobro
    assert len(ctx.repo_ventas.ventas_de_sesion(sesion.id)) == 1


def test_escanear_codigo_normal_agrega_al_carrito():
    _app = QApplication.instance() or QApplication([])
    ctx = _ctx()
    win = PantallaVenta(ctx)
    win.al_mostrar()
    win._escaneo.setText("7700006")  # Arroz, por unidad
    win._procesar_escaneo()
    assert win._carrito.rowCount() == 1
    assert win._total_actual() == Decimal("2500")
    assert win._escaneo.text() == ""  # el campo se limpia tras escanear
