"""Lanza la pantalla de clientes. Uso: python scripts/clientes.py [pos.db]"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from core.servicio_clientes import ServicioClientes  # noqa: E402
from inventario.db import aplicar_migraciones, conectar  # noqa: E402
from ventas.repositorio_sqlite import RepositorioClientesSQLite  # noqa: E402
from caja.pantalla_clientes import PantallaClientes  # noqa: E402


def main(ruta: str = "pos.db") -> None:
    conn = conectar(ruta)
    aplicar_migraciones(conn)
    servicio = ServicioClientes(RepositorioClientesSQLite(conn))
    app = QApplication(sys.argv)
    ventana = PantallaClientes(servicio)
    ventana.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "pos.db")
