import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from datetime import datetime  # noqa: E402
from decimal import Decimal  # noqa: E402

from PySide6.QtWidgets import QApplication  # noqa: E402

from caja.contexto import ContextoApp  # noqa: E402
from caja.ventana_principal import VentanaPrincipal  # noqa: E402


def test_shell_registra_las_pantallas_del_mostrador():
    _app = QApplication.instance() or QApplication([])
    win = VentanaPrincipal(ContextoApp.crear(":memory:"))
    # POS reenfocado: Venta · Inventario · Reportes · Cierre.
    assert len(win._pantallas) == 4
    assert win._stack.count() == 4


def test_tablas_configuradas_para_ajustar_texto():
    from PySide6.QtWidgets import QHeaderView, QTableView
    _app = QApplication.instance() or QApplication([])
    win = VentanaPrincipal(ContextoApp.crear(":memory:"))
    tablas = win.findChildren(QTableView)
    assert tablas  # hay tablas en las pantallas
    for t in tablas:
        assert t.wordWrap()
        assert t.horizontalHeader().sectionResizeMode(0) == QHeaderView.Stretch


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


def _tooltips(win):
    return {b.toolTip() for b in win._botones}


def test_rail_solo_muestra_vistas_del_mostrador():
    _app = QApplication.instance() or QApplication([])
    win = VentanaPrincipal(ContextoApp.crear(":memory:"))
    assert _tooltips(win) == {"Venta", "Inventario", "Reportes", "Cierre"}
    # La gestión de usuarios se administra en la web, no en el POS.
    assert "Usuarios" not in _tooltips(win)
