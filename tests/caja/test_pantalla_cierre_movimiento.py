import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from datetime import datetime  # noqa: E402
from decimal import Decimal  # noqa: E402

from PySide6.QtWidgets import QApplication  # noqa: E402

from caja.contexto import ContextoApp  # noqa: E402
from caja.dialogos.dialogo_movimiento_caja import DialogoMovimientoCaja  # noqa: E402
from caja.pantalla_cierre import PantallaCierre  # noqa: E402


def _pantalla_con_caja_abierta():
    _app = QApplication.instance() or QApplication([])
    ctx = ContextoApp.crear(":memory:")
    win = PantallaCierre(ctx)
    win.al_mostrar()
    win._monto_inicial.setValue(100000)
    win._abrir()
    win.al_mostrar()
    return ctx, win


def test_dialogo_expone_tipo_monto_motivo():
    _app = QApplication.instance() or QApplication([])
    dlg = DialogoMovimientoCaja()
    dlg._tipo.setCurrentIndex(1)  # Egreso
    dlg._monto.setValue(20000)
    dlg._motivo.setText("  retiro a bóveda  ")
    assert dlg.tipo() == "egreso"
    assert dlg.monto() == Decimal("20000")
    assert dlg.motivo() == "retiro a bóveda"


def test_movimiento_actualiza_arqueo(monkeypatch):
    ctx, win = _pantalla_con_caja_abierta()
    sesion = ctx.repo_sesiones.abierta()
    ctx.svc_caja.registrar_movimiento(
        tipo="egreso", monto=Decimal("30000"), motivo="retiro", fecha=datetime.now())
    win._recalcular_arqueo()
    arqueo = ctx.svc_caja.arqueo(sesion.id, Decimal("70000"))
    assert arqueo.esperado == Decimal("70000")
    assert arqueo.diferencia == Decimal("0")
    assert win._kpi_egresos._valor.text() != ""


def test_egreso_excesivo_muestra_error(monkeypatch):
    ctx, win = _pantalla_con_caja_abierta()

    class _DlgFake:
        def __init__(self, parent=None):
            pass

        def exec(self):
            from PySide6.QtWidgets import QDialog
            return QDialog.Accepted

        def tipo(self):
            return "egreso"

        def monto(self):
            return Decimal("999999")

        def motivo(self):
            return "retiro imposible"

    monkeypatch.setattr("caja.pantalla_cierre.DialogoMovimientoCaja", _DlgFake)
    win._abrir_movimiento()
    assert "Error" in win._estado.text()
    assert ctx.repo_movimientos_caja.de_sesion(ctx.repo_sesiones.abierta().id) == []
