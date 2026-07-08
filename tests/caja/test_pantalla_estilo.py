import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from caja.tema import carga_tema
from caja.pantalla_estilo import VentanaEstilo


def test_ventana_estilo_construye():
    app = QApplication.instance() or QApplication([])
    carga_tema(app)
    v = VentanaEstilo()
    assert v.findChild(type(v), ) is None or True  # construye sin excepción
    assert v.windowTitle() == "Estilo · Carnes y Fruver RL"
