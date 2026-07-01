import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from datetime import datetime  # noqa: E402
from decimal import Decimal  # noqa: E402

from PySide6.QtWidgets import QApplication  # noqa: E402

from caja.bootstrap import ADMIN_POR_DEFECTO  # noqa: E402
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


def test_cobro_registra_usuario_actual():
    _app = QApplication.instance() or QApplication([])
    ctx = _ctx()
    nombre, password = ADMIN_POR_DEFECTO
    ctx.usuario_actual = ctx.svc_usuarios.autenticar(nombre, password)
    ctx.svc_caja.abrir(fecha=datetime.now(), monto_inicial=Decimal("0"))
    win = PantallaVenta(ctx)
    win.al_mostrar()
    win._agregar_producto(ctx.repo_productos.por_codigo("7700006"))
    sesion = ctx.repo_sesiones.abierta()
    from core.entidades import Pago
    win._registrar_pagos([Pago(medio_pago_id=1, monto=Decimal("2500"))], sesion.id)
    venta = ctx.repo_ventas.ventas_de_sesion(sesion.id)[0]
    assert venta.usuario_id == ctx.usuario_actual.id


from decimal import Decimal as _D  # noqa: E402

from core.entidades import Cliente, Usuario  # noqa: E402


def test_seleccionar_cliente_con_descuento_aplica_al_total():
    _app = QApplication.instance() or QApplication([])
    ctx = _ctx()
    ctx.usuario_actual = Usuario(nombre="admin", rol="admin", id=1)
    cliente = ctx.repo_clientes.guardar(
        Cliente(identificacion="900", nombre="Mayorista", descuento_pct=_D("0.1")))
    win = PantallaVenta(ctx)
    win.al_mostrar()
    idx = win._combo_cliente.findData(cliente.id)
    win._combo_cliente.setCurrentIndex(idx)  # dispara _al_cambiar_cliente
    win._agregar_producto(ctx.repo_productos.por_codigo("7700006"))  # 2500
    assert win._total_actual() == _D("2250")


def test_descuento_manual_visible_solo_para_admin():
    _app = QApplication.instance() or QApplication([])
    ctx_admin = _ctx()
    ctx_admin.usuario_actual = Usuario(nombre="a", rol="admin", id=1)
    win_admin = PantallaVenta(ctx_admin)
    assert win_admin._descuento_manual.isVisibleTo(win_admin) is True

    ctx_cajero = _ctx()
    ctx_cajero.usuario_actual = Usuario(nombre="c", rol="cajero", id=2)
    win_cajero = PantallaVenta(ctx_cajero)
    assert win_cajero._descuento_manual.isVisibleTo(win_cajero) is False


def test_default_es_consumidor_final():
    _app = QApplication.instance() or QApplication([])
    ctx = _ctx()
    ctx.usuario_actual = Usuario(nombre="admin", rol="admin", id=1)
    win = PantallaVenta(ctx)
    win.al_mostrar()
    assert win._cliente.identificacion == "222222222222"
