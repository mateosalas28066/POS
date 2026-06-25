"""Adaptadores SQLite de los repositorios. Unico lugar con SQL del inventario."""
from __future__ import annotations

import sqlite3
from dataclasses import replace

from core.entidades import Categoria, Impuesto, Producto


class RepositorioCategoriasSQLite:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def guardar(self, categoria: Categoria) -> Categoria:
        cur = self._conn.execute(
            "INSERT INTO categorias (nombre) VALUES (?)", (categoria.nombre,))
        self._conn.commit()
        return replace(categoria, id=cur.lastrowid)


class RepositorioImpuestosSQLite:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def guardar(self, impuesto: Impuesto) -> Impuesto:
        cur = self._conn.execute(
            "INSERT INTO impuestos (nombre, tarifa, codigo_dian) VALUES (?, ?, ?)",
            (impuesto.nombre, impuesto.tarifa, impuesto.codigo_dian))
        self._conn.commit()
        return replace(impuesto, id=cur.lastrowid)


def _fila_a_producto(f: sqlite3.Row) -> Producto:
    return Producto(
        codigo_barras=f["codigo_barras"],
        nombre=f["nombre"],
        precio=f["precio"],
        vendido_por_peso=bool(f["vendido_por_peso"]),
        unidad=f["unidad"],
        costo=f["costo"],
        categoria_id=f["categoria_id"],
        impuesto_id=f["impuesto_id"],
        id=f["id"],
    )


class RepositorioProductosSQLite:
    _COLS = ("codigo_barras, nombre, precio, costo, categoria_id, impuesto_id, "
             "vendido_por_peso, unidad")

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def guardar(self, producto: Producto) -> Producto:
        cur = self._conn.execute(
            f"INSERT INTO productos ({self._COLS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (producto.codigo_barras, producto.nombre, producto.precio, producto.costo,
             producto.categoria_id, producto.impuesto_id,
             int(producto.vendido_por_peso), producto.unidad))
        self._conn.commit()
        return replace(producto, id=cur.lastrowid)

    def por_id(self, id: int) -> Producto | None:
        f = self._conn.execute("SELECT * FROM productos WHERE id = ?", (id,)).fetchone()
        return _fila_a_producto(f) if f else None

    def por_codigo(self, codigo_barras: str) -> Producto | None:
        f = self._conn.execute(
            "SELECT * FROM productos WHERE codigo_barras = ?", (codigo_barras,)).fetchone()
        return _fila_a_producto(f) if f else None

    def listar(self) -> list[Producto]:
        filas = self._conn.execute("SELECT * FROM productos ORDER BY id").fetchall()
        return [_fila_a_producto(f) for f in filas]
