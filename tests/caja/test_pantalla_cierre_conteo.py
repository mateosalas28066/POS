# tests/caja/test_pantalla_cierre_conteo.py
import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from decimal import Decimal  # noqa: E402

from PySide6.QtWidgets import QApplication, QDialog  # noqa: E402

from caja.contexto import ContextoApp  # noqa: E402
from caja.pantalla_cierre import PantallaCierre  # noqa: E402
import caja.pantalla_cierre as mod  # noqa: E402


class _FakeDialogo:
    def __init__(self, *a, **k):
        pass

    def exec(self):
        return QDialog.Accepted

    def total(self):
        return Decimal("123000")

    def desglose(self):
        return {1000: 123}


def test_boton_conteo_rellena_monto_contado(monkeypatch):
    _app = QApplication.instance() or QApplication([])
    ctx = ContextoApp.crear(":memory:")
    win = PantallaCierre(ctx)
    win.al_mostrar()
    win._monto_inicial.setValue(0)
    win._abrir()               # abre caja → vista de arqueo con el botón
    win.al_mostrar()
    monkeypatch.setattr(mod, "DialogoConteoEfectivo", _FakeDialogo)
    win._abrir_conteo()
    assert win._monto_contado.value() == 123000


def test_reabrir_conteo_conserva_desglose_mientras_caja_sigue_abierta(monkeypatch):
    _app = QApplication.instance() or QApplication([])
    ctx = ContextoApp.crear(":memory:")
    win = PantallaCierre(ctx)
    win.al_mostrar()
    win._monto_inicial.setValue(0)
    win._abrir()
    win.al_mostrar()

    recibido = {}

    class _Fake(_FakeDialogo):
        def __init__(self, *a, desglose=None, **k):
            recibido["desglose"] = desglose

    monkeypatch.setattr(mod, "DialogoConteoEfectivo", _Fake)
    win._abrir_conteo()
    assert recibido["desglose"] is None  # primera vez: sin conteo previo

    win._abrir_conteo()
    assert recibido["desglose"] == {1000: 123}  # segunda vez: conserva el desglose anterior


def test_desglose_se_descarta_al_cerrar_caja(monkeypatch):
    _app = QApplication.instance() or QApplication([])
    ctx = ContextoApp.crear(":memory:")
    win = PantallaCierre(ctx)
    win.al_mostrar()
    win._monto_inicial.setValue(0)
    win._abrir()
    win.al_mostrar()
    monkeypatch.setattr(mod, "DialogoConteoEfectivo", _FakeDialogo)
    win._abrir_conteo()
    assert win._desglose_conteo == {1000: 123}

    from PySide6.QtWidgets import QMessageBox  # noqa: E402
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    win._cerrar()
    assert win._desglose_conteo is None
