"""Conexión SQLite y aplicación de migraciones. Único lugar con detalles de sqlite3."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
DIR_MIGRACIONES = RAIZ / "scripts" / "migraciones"

# Dinero/cantidades viajan como texto exacto, no como float.
sqlite3.register_adapter(Decimal, str)
sqlite3.register_converter("DECIMAL", lambda b: Decimal(b.decode()))


def conectar(ruta: str = ":memory:", check_same_thread: bool = True) -> sqlite3.Connection:
    conn = sqlite3.connect(ruta, detect_types=sqlite3.PARSE_DECLTYPES,
                           check_same_thread=check_same_thread)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def aplicar_migraciones(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migraciones ("
        "archivo TEXT PRIMARY KEY, aplicada_en TEXT NOT NULL)")
    aplicadas = {r[0] for r in conn.execute("SELECT archivo FROM schema_migraciones")}
    for archivo in sorted(DIR_MIGRACIONES.glob("*.sql")):
        if archivo.name in aplicadas:
            continue
        conn.executescript(archivo.read_text(encoding="utf-8"))
        conn.execute(
            "INSERT INTO schema_migraciones (archivo, aplicada_en) VALUES (?, ?)",
            (archivo.name, datetime.now(timezone.utc).isoformat()))
    conn.commit()
