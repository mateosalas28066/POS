import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path  # noqa: E402

from PySide6.QtWidgets import QApplication  # noqa: E402

from caja.tema import carga_tema, icono  # noqa: E402


def test_carga_tema_aplica_stylesheet():
    app = QApplication.instance() or QApplication([])
    app.setStyleSheet("")
    carga_tema(app)
    assert "#0B0E14" in app.styleSheet()


def test_icono_existe():
    for nombre in ("venta", "inventario", "clientes", "devoluciones", "reportes", "cierre"):
        assert Path(icono(nombre)).exists()
