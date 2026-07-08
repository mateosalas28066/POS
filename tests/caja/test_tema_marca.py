import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from caja.tema import carga_tema, carga_fuentes


def test_carga_tema_aplica_marca_sin_error():
    app = QApplication.instance() or QApplication([])
    carga_tema(app)
    hoja = app.styleSheet()
    assert hoja  # qt-material dejó un stylesheet no vacío
    assert "#E01E26".lower() in hoja.lower() or "E01E26".lower() in hoja.lower()


def test_carga_fuentes_registra_familias():
    app = QApplication.instance() or QApplication([])
    familias = carga_fuentes()
    assert any("Space Grotesk" in f for f in familias)


def test_overlay_marca_en_stylesheet():
    app = QApplication.instance() or QApplication([])
    carga_tema(app)
    hoja = app.styleSheet()
    assert "QPushButton#primario" in hoja
    assert "border-left: 3px solid #E01E26" in hoja


def test_aplica_glow_pone_efecto():
    from PySide6.QtWidgets import QPushButton
    from caja.efectos import aplica_glow
    app = QApplication.instance() or QApplication([])
    b = QPushButton("x")
    aplica_glow(b)
    assert b.graphicsEffect() is not None
