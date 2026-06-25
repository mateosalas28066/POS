"""Lanza la pantalla de caja. Uso: python scripts/caja.py [pos.db]"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from core.servicio_venta import ServicioVenta  # noqa: E402
from inventario.db import aplicar_migraciones, conectar  # noqa: E402
from inventario.repositorio_sqlite import (  # noqa: E402
    RepositorioImpuestosSQLite,
    RepositorioProductosSQLite,
)
from caja.pantalla_venta import PantallaVenta  # noqa: E402


def main(ruta: str = "pos.db") -> None:
    conn = conectar(ruta)
    aplicar_migraciones(conn)
    servicio = ServicioVenta(RepositorioProductosSQLite(conn), RepositorioImpuestosSQLite(conn))
    app = QApplication(sys.argv)
    ventana = PantallaVenta(servicio)
    ventana.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "pos.db")
