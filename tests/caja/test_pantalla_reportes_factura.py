import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from datetime import datetime  # noqa: E402
from decimal import Decimal  # noqa: E402

from PySide6.QtWidgets import QApplication  # noqa: E402

from caja.bootstrap import ADMIN_POR_DEFECTO  # noqa: E402
from caja.contexto import ContextoApp  # noqa: E402
from caja.pantalla_reportes import PantallaReportes  # noqa: E402
from core.entidades import LineaVenta, Pago, Venta  # noqa: E402


def _ctx_con_venta():
    ctx = ContextoApp.crear(":memory:")
    u = ctx.svc_usuarios.autenticar(*ADMIN_POR_DEFECTO)
    linea = LineaVenta(producto_id=1, descripcion="Café", cantidad_o_peso=Decimal("1"),
                       precio_unit=Decimal("7000"), impuesto=Decimal("1118"),
                       subtotal=Decimal("7000"))
    venta = Venta(fecha=datetime.now(), lineas=(linea,), total=Decimal("7000"),
                  total_impuestos=Decimal("1118"), usuario_id=u.id)
    ctx.repo_ventas.guardar(venta, [Pago(medio_pago_id=1, monto=Decimal("7000"))])
    return ctx, u


def test_pestana_factura_lista_la_venta_con_cajero():
    _app = QApplication.instance() or QApplication([])
    ctx, u = _ctx_con_venta()
    win = PantallaReportes(ctx)
    win.al_mostrar()
    assert win._tabla_factura.rowCount() == 1
    assert win._tabla_factura.item(0, 2).text() == u.nombre     # columna Cajero
    assert win._tabla_factura.item(0, 3).text() == "—"          # sin cliente


def test_seleccionar_factura_muestra_lineas_y_pagos():
    _app = QApplication.instance() or QApplication([])
    ctx, _ = _ctx_con_venta()
    win = PantallaReportes(ctx)
    win.al_mostrar()
    win._tabla_factura.selectRow(0)
    # 1 línea + 1 pago
    assert win._detalle_factura.rowCount() == 2
