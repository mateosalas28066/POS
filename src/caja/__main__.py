"""Entry point: python -m caja [ruta_db]."""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from caja.contexto import ContextoApp
from caja.tema import carga_tema
from caja.ventana_principal import VentanaPrincipal


def main(ruta_db: str = "pos.db") -> int:
    app = QApplication(sys.argv)
    carga_tema(app)
    ctx = ContextoApp.crear(ruta_db)
    ventana = VentanaPrincipal(ctx)
    ventana.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "pos.db"))
