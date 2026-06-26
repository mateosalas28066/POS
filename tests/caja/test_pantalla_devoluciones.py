import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from datetime import datetime  # noqa: E402
from decimal import Decimal  # noqa: E402

from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from core.entidades import Pago  # noqa: E402
from caja.contexto import ContextoApp  # noqa: E402
from caja.pantalla_devoluciones import PantallaDevoluciones  # noqa: E402


def _ctx_con_venta():
    ctx = ContextoApp.crear(":memory:")
    ctx.svc_caja.abrir(fecha=datetime.now(), monto_inicial=Decimal("0"))
    sesion = ctx.repo_sesiones.abierta()
    venta_serv = ctx.nueva_venta()
    venta_serv.agregar("7700006")  # Arroz und 2500
    venta = venta_serv.confirmar(fecha=datetime.now(), caja_sesion_id=sesion.id)
    guardada = ctx.svc_registro.registrar(venta, [Pago(medio_pago_id=1, monto=Decimal("2500"))])
    return ctx, guardada


def test_buscar_venta_existente_carga_lineas():
    _app = QApplication.instance() or QApplication([])
    ctx, venta = _ctx_con_venta()
    win = PantallaDevoluciones(ctx)
    win._id_venta.setText(str(venta.id))
    win._buscar()
    assert win._tabla.rowCount() == 1
    assert win._venta is not None


def test_buscar_venta_inexistente_muestra_error():
    _app = QApplication.instance() or QApplication([])
    ctx, _ = _ctx_con_venta()
    win = PantallaDevoluciones(ctx)
    win._id_venta.setText("9999")
    win._buscar()
    assert win._estado.text() != ""
    assert win._venta is None


def test_procesar_devolucion_total(monkeypatch):
    _app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    monkeypatch.setattr(QMessageBox, "critical", lambda *a, **k: None)
    ctx, venta = _ctx_con_venta()
    win = PantallaDevoluciones(ctx)
    win._id_venta.setText(str(venta.id))
    win._buscar()
    win._spins[0].setValue(1)  # devolver 1 unidad
    assert win._total_a_devolver() == Decimal("2500")
    win._procesar([Pago(medio_pago_id=1, monto=Decimal("2500"))])
    assert ctx.repo_ventas.por_id(venta.id).estado == "devuelta"
