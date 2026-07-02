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


def test_tabla_por_categoria_se_llena():
    _app = QApplication.instance() or QApplication([])
    ctx = ContextoApp.crear(":memory:")
    ctx.svc_caja.abrir(fecha=datetime.now(), monto_inicial=Decimal("0"))
    sesion = ctx.repo_sesiones.abierta()
    v = ctx.nueva_venta()
    v.agregar("7700006")
    venta = v.confirmar(fecha=datetime.now(), caja_sesion_id=sesion.id)
    ctx.svc_registro.registrar(venta, [Pago(medio_pago_id=1, monto=Decimal("2500"))])

    win = PantallaReportes(ctx)
    win.al_mostrar()
    assert win._tabla_categoria.rowCount() >= 1
    # la primera columna muestra el nombre de la categoría (o "Sin categoría")
    assert win._tabla_categoria.item(0, 0).text() != ""
