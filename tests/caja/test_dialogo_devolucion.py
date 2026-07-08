import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from datetime import datetime  # noqa: E402
from decimal import Decimal  # noqa: E402

from PySide6.QtWidgets import QApplication  # noqa: E402

from core.entidades import Pago  # noqa: E402
from caja.contexto import ContextoApp  # noqa: E402
from caja.dialogos.dialogo_devolucion import DialogoDevolucion  # noqa: E402


def _ctx_con_venta():
    ctx = ContextoApp.crear(":memory:")
    ctx.svc_caja.abrir(fecha=datetime.now(), monto_inicial=Decimal("0"))
    sesion = ctx.repo_sesiones.abierta()
    venta_serv = ctx.nueva_venta()
    venta_serv.agregar("7700006")  # Arroz und 2500
    venta = venta_serv.confirmar(fecha=datetime.now(), caja_sesion_id=sesion.id)
    guardada = ctx.svc_registro.registrar(venta, [Pago(medio_pago_id=1, monto=Decimal("2500"))])
    return ctx, guardada


def test_cargar_factura_lista_lineas():
    _app = QApplication.instance() or QApplication([])
    ctx, venta = _ctx_con_venta()
    dlg = DialogoDevolucion(ctx)
    dlg.cargar_factura(venta.id)
    assert dlg._tabla.rowCount() == 1
    assert dlg._venta is not None


def test_devolucion_total_desde_dialogo():
    _app = QApplication.instance() or QApplication([])
    ctx, venta = _ctx_con_venta()
    dlg = DialogoDevolucion(ctx)
    dlg.cargar_factura(venta.id)
    dlg.marcar_devolucion(linea_idx=0, cantidad=1)
    resultado = dlg.confirmar()  # sin pagos → reembolso en efectivo del total
    assert resultado is not None
    assert resultado.total == Decimal("2500")
    assert ctx.repo_ventas.por_id(venta.id).estado == "devuelta"


def test_factura_inexistente_no_carga():
    _app = QApplication.instance() or QApplication([])
    ctx, _ = _ctx_con_venta()
    dlg = DialogoDevolucion(ctx)
    dlg.cargar_factura(9999)
    assert dlg._venta is None
    assert dlg._estado.text() != ""
