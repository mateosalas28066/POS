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


def test_scanner_serial_agrega_al_carrito():
    class PuertoFake:
        def __init__(self, datos: bytes) -> None:
            self._datos = bytearray(datos)
            self.cerrado = False

        @property
        def in_waiting(self) -> int:
            return len(self._datos)

        def read(self, n: int) -> bytes:
            datos = bytes(self._datos[:n])
            del self._datos[:n]
            return datos

        def close(self) -> None:
            self.cerrado = True

    _app = QApplication.instance() or QApplication([])
    ctx = _ctx()
    win = PantallaVenta(ctx)
    win.al_mostrar()
    win._scanner_serial = PuertoFake(b"7700006\r\n")
    win._leer_scanner_serial()
    assert win._carrito.rowCount() == 1
    assert win._total_actual() == Decimal("2500")


def test_scanner_serial_agrega_etiqueta_real_de_bascula():
    class PuertoFake:
        def __init__(self, datos: bytes) -> None:
            self._datos = bytearray(datos)

        @property
        def in_waiting(self) -> int:
            return len(self._datos)

        def read(self, n: int) -> bytes:
            datos = bytes(self._datos[:n])
            del self._datos[:n]
            return datos

        def close(self) -> None:
            pass

    _app = QApplication.instance() or QApplication([])
    ctx = _ctx()
    win = PantallaVenta(ctx)
    win.al_mostrar()
    win._scanner_serial = PuertoFake(b"2400190008059\r\n")
    win._leer_scanner_serial()
    assert win._carrito.rowCount() == 1
    assert win._carrito.item(0, 0).text() == "Ampolleta"
    assert win._carrito.item(0, 1).text() == "0,805"
    assert win._total_actual() == Decimal("24150")


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


def test_grid_5_columnas_y_no_deja_huecos_al_filtrar():
    _app = QApplication.instance() or QApplication([])
    win = PantallaVenta(_ctx())
    win.al_mostrar()
    from caja.pantalla_venta import _COLS_GRID
    assert _COLS_GRID == 5

    win._busqueda.setText("arroz")
    win._aplicar_filtro()
    visibles = [t for t in win._tarjetas if t.isVisibleTo(win)]
    assert 1 <= len(visibles) < len(win._tarjetas)
    # las visibles deben quedar contiguas desde (0, 0), sin huecos
    for i, t in enumerate(visibles):
        idx = win._grid.indexOf(t)
        assert idx != -1
        fila, col, _, _ = win._grid.getItemPosition(idx)
        assert (fila, col) == (i // _COLS_GRID, i % _COLS_GRID)


def test_producto_sin_stock_aparece_agotado():
    _app = QApplication.instance() or QApplication([])
    ctx = _ctx()
    win = PantallaVenta(ctx)
    win.al_mostrar()
    producto = ctx.repo_productos.por_codigo("7700006")
    ctx.repo_inventario.registrar(__import__("core.entidades", fromlist=["MovimientoInventario"])
                                   .MovimientoInventario(
                                       producto_id=producto.id, tipo="salida",
                                       cantidad=ctx.repo_inventario.stock_de(producto.id),
                                       fecha=datetime.now()))
    win._construir_grid()
    tarjeta = next(t for t in win._tarjetas if t._producto.id == producto.id)
    assert tarjeta.property("agotado") is True


def test_default_es_consumidor_final():
    _app = QApplication.instance() or QApplication([])
    ctx = _ctx()
    ctx.usuario_actual = Usuario(nombre="admin", rol="admin", id=1)
    win = PantallaVenta(ctx)
    win.al_mostrar()
    assert win._cliente.identificacion == "222222222222"
