"""Conexión SQLite y aplicación de migraciones. Único lugar con detalles de sqlite3."""
from __future__ import annotations

import sqlite3
from decimal import Decimal
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
DIR_MIGRACIONES = RAIZ / "scripts" / "migraciones"

# Dinero/cantidades viajan como texto exacto, no como float.
sqlite3.register_adapter(Decimal, str)
sqlite3.register_converter("DECIMAL", lambda b: Decimal(b.decode()))


def conectar(ruta: str = ":memory:") -> sqlite3.Connection:
    conn = sqlite3.connect(ruta, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def aplicar_migraciones(conn: sqlite3.Connection) -> None:
    for archivo in sorted(DIR_MIGRACIONES.glob("*.sql")):
        conn.executescript(archivo.read_text(encoding="utf-8"))
    conn.commit()
