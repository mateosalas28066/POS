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


def _guardar_venta(ctx, usuario_id, total=Decimal("7000")):
    linea = LineaVenta(producto_id=1, descripcion="Café", cantidad_o_peso=Decimal("1"),
                       precio_unit=total, impuesto=Decimal("0"), subtotal=total)
    venta = Venta(fecha=datetime.now(), lineas=(linea,), total=total,
                  total_impuestos=Decimal("0"), usuario_id=usuario_id)
    ctx.repo_ventas.guardar(venta, [Pago(medio_pago_id=1, monto=total)])


def test_pestana_cajero_muestra_neto_por_cajero():
    _app = QApplication.instance() or QApplication([])
    ctx = ContextoApp.crear(":memory:")
    u = ctx.svc_usuarios.autenticar(*ADMIN_POR_DEFECTO)
    _guardar_venta(ctx, u.id)
    win = PantallaReportes(ctx)
    win.al_mostrar()
    assert win._tabla_cajero.rowCount() >= 1
    assert win._tabla_cajero.item(0, 0).text() == u.nombre
    assert win._tabla_cajero.item(0, 4).text() == "$ 7.000"      # Neto (formato_moneda: "$ 7.000")


def test_pestana_cajero_usuario_nulo_es_sin_cajero():
    _app = QApplication.instance() or QApplication([])
    ctx = ContextoApp.crear(":memory:")
    _guardar_venta(ctx, None)
    win = PantallaReportes(ctx)
    win.al_mostrar()
    assert win._tabla_cajero.item(0, 0).text() == "Sin cajero"
