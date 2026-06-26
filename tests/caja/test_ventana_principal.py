import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from datetime import datetime  # noqa: E402
from decimal import Decimal  # noqa: E402

from PySide6.QtWidgets import QApplication  # noqa: E402

from caja.contexto import ContextoApp  # noqa: E402
from caja.ventana_principal import VentanaPrincipal  # noqa: E402


def test_shell_tiene_seis_pantallas():
    _app = QApplication.instance() or QApplication([])
    win = VentanaPrincipal(ContextoApp.crear(":memory:"))
    assert len(win._pantallas) == 6
    assert win._stack.count() == 6


def test_navegar_cambia_pantalla_activa():
    _app = QApplication.instance() or QApplication([])
    win = VentanaPrincipal(ContextoApp.crear(":memory:"))
    win._ir_a(2)
    assert win._stack.currentIndex() == 2


def test_barra_estado_refleja_caja_abierta():
    _app = QApplication.instance() or QApplication([])
    ctx = ContextoApp.crear(":memory:")
    ctx.svc_caja.abrir(fecha=datetime.now(), monto_inicial=Decimal("0"))
    win = VentanaPrincipal(ctx)
    win._refrescar_estado()
    assert "abierta" in win.statusBar().currentMessage().lower()
