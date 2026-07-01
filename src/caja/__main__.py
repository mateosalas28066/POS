"""Entry point: python -m caja [ruta_db]."""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QDialog

from caja.contexto import ContextoApp
from caja.dialogos.dialogo_login import DialogoLogin
from caja.tema import carga_tema
from caja.ventana_principal import VentanaPrincipal


def main(ruta_db: str = "pos.db") -> int:
    app = QApplication(sys.argv)
    carga_tema(app)
    ctx = ContextoApp.crear(ruta_db)
    login = DialogoLogin(ctx.svc_usuarios)
    if login.exec() != QDialog.Accepted:
        return 0
    ctx.usuario_actual = login.usuario
    ventana = VentanaPrincipal(ctx)
    ventana.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "pos.db"))
