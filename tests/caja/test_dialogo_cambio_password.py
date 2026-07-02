import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from caja.bootstrap import ADMIN_POR_DEFECTO  # noqa: E402
from caja.contexto import ContextoApp  # noqa: E402
from caja.dialogos.dialogo_cambio_password import DialogoCambioPassword  # noqa: E402


def _dialogo():
    _app = QApplication.instance() or QApplication([])
    ctx = ContextoApp.crear(":memory:")
    nombre, _ = ADMIN_POR_DEFECTO
    return ctx, DialogoCambioPassword(ctx.svc_usuarios, nombre)


def test_cambio_exitoso_acepta_y_actualiza():
    ctx, dlg = _dialogo()
    nombre, password = ADMIN_POR_DEFECTO
    dlg._actual.setText(password)
    dlg._nueva.setText("nueva9999")
    dlg._confirmacion.setText("nueva9999")
    dlg._al_aceptar()
    assert dlg.result() == DialogoCambioPassword.Accepted
    assert ctx.svc_usuarios.autenticar(nombre, "nueva9999") is not None
    assert ctx.svc_usuarios.autenticar(nombre, password) is None


def test_confirmacion_distinta_muestra_error():
    _ctx, dlg = _dialogo()
    _, password = ADMIN_POR_DEFECTO
    dlg._actual.setText(password)
    dlg._nueva.setText("nueva9999")
    dlg._confirmacion.setText("otra")
    dlg._al_aceptar()
    assert "Error" in dlg._estado.text()
    assert dlg.result() != DialogoCambioPassword.Accepted


def test_actual_incorrecta_muestra_error():
    ctx, dlg = _dialogo()
    nombre, password = ADMIN_POR_DEFECTO
    dlg._actual.setText("incorrecta")
    dlg._nueva.setText("nueva9999")
    dlg._confirmacion.setText("nueva9999")
    dlg._al_aceptar()
    assert "Error" in dlg._estado.text()
    assert ctx.svc_usuarios.autenticar(nombre, password) is not None
