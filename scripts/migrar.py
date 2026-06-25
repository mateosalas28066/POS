"""Aplica las migraciones SQLite a la ruta dada. Uso: python scripts/migrar.py pos.db"""
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "src"))

from inventario.db import conectar, aplicar_migraciones  # noqa: E402


def main(ruta: str) -> None:
    conn = conectar(ruta)
    aplicar_migraciones(conn)
    conn.close()
    print(f"Migraciones aplicadas en {ruta}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "pos.db")
