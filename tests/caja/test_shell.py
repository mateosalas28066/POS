import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from caja.contexto import ContextoApp  # noqa: E402
from caja.tema import icono  # noqa: E402
from caja.widgets import BotonRail, CabeceraVista  # noqa: E402

_app = QApplication.instance() or QApplication([])


def test_cabecera_muestra_titulo_y_cambia_de_vista():
    cab = CabeceraVista(icono("venta"), "Venta")
    assert cab._titulo.text() == "Venta"
    cab.set_vista(icono("cierre"), "Cierre")
    assert cab._titulo.text() == "Cierre"


def test_boton_rail_muestra_etiqueta():
    b = BotonRail(icono("venta"), "Venta")
    assert b.text() == "Venta"
    assert b.toolButtonStyle() == Qt.ToolButtonTextUnderIcon


def test_cabecera_sigue_a_la_vista_activa():
    from caja.ventana_principal import VentanaPrincipal
    win = VentanaPrincipal(ContextoApp.crear(":memory:"))
    win._ir_a(0)
    assert win._cabecera._titulo.text() == "Venta"
    idx_cierre = [i for i, p in enumerate(win._pantallas)
                  if p.__class__.__name__ == "PantallaCierre"][0]
    win._ir_a(idx_cierre)
    assert win._cabecera._titulo.text() == "Cierre"


def test_perfil_expone_cambiar_password_y_cerrar_sesion():
    from caja.ventana_principal import VentanaPrincipal
    win = VentanaPrincipal(ContextoApp.crear(":memory:"))
    textos = [a.text() for a in win._menu_perfil.actions()]
    assert "Cambiar mi contraseña" in textos
    assert "Cerrar sesión" in textos
