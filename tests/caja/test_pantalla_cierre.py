import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from decimal import Decimal  # noqa: E402

from PySide6.QtWidgets import QApplication  # noqa: E402

from caja.bootstrap import ADMIN_POR_DEFECTO  # noqa: E402
from caja.contexto import ContextoApp  # noqa: E402
from caja.pantalla_cierre import PantallaCierre  # noqa: E402


def test_abrir_caja_crea_sesion():
    _app = QApplication.instance() or QApplication([])
    ctx = ContextoApp.crear(":memory:")
    win = PantallaCierre(ctx)
    win.al_mostrar()
    win._monto_inicial.setValue(50000)
    win._abrir()
    assert ctx.repo_sesiones.abierta() is not None


def test_cerrar_caja_cierra_sesion(monkeypatch):
    _app = QApplication.instance() or QApplication([])
    ctx = ContextoApp.crear(":memory:")
    win = PantallaCierre(ctx)
    win.al_mostrar()
    win._monto_inicial.setValue(50000)
    win._abrir()
    win.al_mostrar()
    win._monto_contado.setValue(50000)
    from PySide6.QtWidgets import QMessageBox  # noqa: E402
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    win._cerrar()
    assert ctx.repo_sesiones.abierta() is None


def test_abrir_caja_registra_usuario_actual():
    _app = QApplication.instance() or QApplication([])
    ctx = ContextoApp.crear(":memory:")
    nombre, password = ADMIN_POR_DEFECTO
    ctx.usuario_actual = ctx.svc_usuarios.autenticar(nombre, password)
    win = PantallaCierre(ctx)
    win.al_mostrar()
    win._monto_inicial.setValue(0)
    win._abrir()
    assert ctx.repo_sesiones.abierta().usuario_id == ctx.usuario_actual.id
