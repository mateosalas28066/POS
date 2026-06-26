"""Arranque de datos: conexión, migraciones y seed demo idempotente."""
from __future__ import annotations

import sqlite3
from datetime import datetime

from inventario.db import aplicar_migraciones, conectar

# (codigo_barras, nombre, precio, categoria_nombre, impuesto_nombre, vendido_por_peso, unidad, stock)
_PRODUCTOS_DEMO = [
    ("7700001", "Pechuga de pollo", "18900", "Carnes", "IVA 0%", 1, "kg", "25"),
    ("7700002", "Carne molida", "22000", "Carnes", "IVA 0%", 1, "kg", "18"),
    ("7700003", "Manzana roja", "6500", "Frutas", "IVA 0%", 1, "kg", "40"),
    ("7700004", "Banano", "3200", "Frutas", "IVA 0%", 1, "kg", "60"),
    ("7700005", "Papa pastusa", "2800", "Verduras", "IVA 0%", 1, "kg", "80"),
    ("7700006", "Arroz 500g", "2500", "Abarrotes", "IVA 19%", 0, "und", "100"),
]
_CATEGORIAS_DEMO = ["Carnes", "Frutas", "Verduras", "Abarrotes"]
_IMPUESTOS_DEMO = [("IVA 0%", "0"), ("IVA 19%", "0.19")]


def sembrar_demo(conn: sqlite3.Connection) -> None:
    """Crea categorías, impuestos y productos demo si no existen. Idempotente."""
    for nombre in _CATEGORIAS_DEMO:
        conn.execute("INSERT OR IGNORE INTO categorias (nombre) VALUES (?)", (nombre,))
    for nombre, tarifa in _IMPUESTOS_DEMO:
        conn.execute(
            "INSERT OR IGNORE INTO impuestos (nombre, tarifa) VALUES (?, ?)", (nombre, tarifa))
    conn.commit()

    cat_id = {r["nombre"]: r["id"]
              for r in conn.execute("SELECT id, nombre FROM categorias")}
    imp_id = {r["nombre"]: r["id"]
              for r in conn.execute("SELECT id, nombre FROM impuestos")}

    for cod, nombre, precio, cat, imp, peso, unidad, stock in _PRODUCTOS_DEMO:
        existe = conn.execute(
            "SELECT id FROM productos WHERE codigo_barras = ?", (cod,)).fetchone()
        if existe:
            continue
        cur = conn.execute(
            "INSERT INTO productos "
            "(codigo_barras, nombre, precio, costo, categoria_id, impuesto_id, "
            "vendido_por_peso, unidad) VALUES (?, ?, ?, 0, ?, ?, ?, ?)",
            (cod, nombre, precio, cat_id[cat], imp_id[imp], peso, unidad))
        conn.execute(
            "INSERT INTO inventario_movimientos "
            "(producto_id, tipo, cantidad, fecha, ref) VALUES (?, 'entrada', ?, ?, 'seed')",
            (cur.lastrowid, stock, datetime.now().isoformat()))
    conn.commit()


def preparar_db(ruta: str = "pos.db") -> sqlite3.Connection:
    conn = conectar(ruta)
    aplicar_migraciones(conn)
    sembrar_demo(conn)
    return conn
