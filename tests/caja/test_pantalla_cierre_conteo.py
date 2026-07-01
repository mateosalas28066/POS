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
