import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from datetime import datetime  # noqa: E402
from decimal import Decimal  # noqa: E402

from PySide6.QtWidgets import QApplication  # noqa: E402

from core.entidades import Pago  # noqa: E402
from caja.contexto import ContextoApp  # noqa: E402
from caja.pantalla_reportes import PantallaReportes  # noqa: E402


def _ctx_con_venta():
    ctx = ContextoApp.crear(":memory:")
    ctx.svc_caja.abrir(fecha=datetime.now(), monto_inicial=Decimal("0"))
    sesion = ctx.repo_sesiones.abierta()
    v = ctx.nueva_venta()
    v.agregar("7700006")
    venta = v.confirmar(fecha=datetime.now(), caja_sesion_id=sesion.id)
    ctx.svc_registro.registrar(venta, [Pago(medio_pago_id=1, monto=Decimal("2500"))])
    return ctx


def test_consultar_llena_kpi_neto():
    _app = QApplication.instance() or QApplication([])
    ctx = _ctx_con_venta()
    win = PantallaReportes(ctx)
    win.al_mostrar()
    win._consultar()
    assert "2.500" in win._kpi_neto._valor.text()


def test_tabla_inventario_se_llena():
    _app = QApplication.instance() or QApplication([])
    ctx = _ctx_con_venta()
    win = PantallaReportes(ctx)
    win.al_mostrar()
    win._consultar()
    assert win._tabla_inventario.rowCount() >= 1
