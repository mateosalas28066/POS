import sqlite3

import pytest

from inventario.db import aplicar_migraciones, conectar


def _columnas(conn, tabla):
    return {r["name"] for r in conn.execute(f"PRAGMA table_info({tabla})")}


def test_agrega_descuento_pct_a_clientes_y_ventas():
    conn = conectar()
    aplicar_migraciones(conn)
    assert "descuento_pct" in _columnas(conn, "clientes")
    assert "descuento_pct" in _columnas(conn, "ventas")


def test_aplicar_migraciones_es_idempotente():
    conn = conectar()
    aplicar_migraciones(conn)
    aplicar_migraciones(conn)  # no debe lanzar "duplicate column name"
    assert "descuento_pct" in _columnas(conn, "clientes")


def test_nombre_de_usuario_es_unico():
    conn = conectar()
    aplicar_migraciones(conn)
    conn.execute("INSERT INTO usuarios (nombre, rol, hash_password) VALUES ('ana','cajero','h')")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO usuarios (nombre, rol, hash_password) VALUES ('ana','admin','h2')")
