"""Adaptadores SQLite de los repositorios. Unico lugar con SQL del inventario."""
from __future__ import annotations

import sqlite3
from dataclasses import replace
from datetime import datetime
from decimal import Decimal

from core.entidades import Categoria, Impuesto, MovimientoInventario, Producto, Promocion


class RepositorioCategoriasSQLite:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def guardar(self, categoria: Categoria) -> Categoria:
        cur = self._conn.execute(
            "INSERT INTO categorias (nombre) VALUES (?)", (categoria.nombre,))
        self._conn.commit()
        return replace(categoria, id=cur.lastrowid)

    def por_id(self, id: int) -> Categoria | None:
        f = self._conn.execute("SELECT * FROM categorias WHERE id = ?", (id,)).fetchone()
        return Categoria(nombre=f["nombre"], id=f["id"]) if f else None

    def listar(self) -> list[Categoria]:
        filas = self._conn.execute("SELECT * FROM categorias ORDER BY id").fetchall()
        return [Categoria(nombre=f["nombre"], id=f["id"]) for f in filas]


class RepositorioImpuestosSQLite:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def guardar(self, impuesto: Impuesto) -> Impuesto:
        cur = self._conn.execute(
            "INSERT INTO impuestos (nombre, tarifa, codigo_dian) VALUES (?, ?, ?)",
            (impuesto.nombre, impuesto.tarifa, impuesto.codigo_dian))
        self._conn.commit()
        return replace(impuesto, id=cur.lastrowid)

    def por_id(self, id: int) -> Impuesto | None:
        f = self._conn.execute("SELECT * FROM impuestos WHERE id = ?", (id,)).fetchone()
        return Impuesto(nombre=f["nombre"], tarifa=f["tarifa"],
                        codigo_dian=f["codigo_dian"], id=f["id"]) if f else None

    def listar(self) -> list[Impuesto]:
        filas = self._conn.execute("SELECT * FROM impuestos ORDER BY id").fetchall()
        return [Impuesto(nombre=f["nombre"], tarifa=f["tarifa"],
                         codigo_dian=f["codigo_dian"], id=f["id"]) for f in filas]


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

    def actualizar(self, producto: Producto) -> Producto:
        cur = self._conn.execute(
            "UPDATE productos SET codigo_barras = ?, nombre = ?, precio = ?, costo = ?, "
            "categoria_id = ?, impuesto_id = ?, vendido_por_peso = ?, unidad = ? WHERE id = ?",
            (producto.codigo_barras, producto.nombre, producto.precio, producto.costo,
             producto.categoria_id, producto.impuesto_id,
             int(producto.vendido_por_peso), producto.unidad, producto.id))
        if cur.rowcount == 0:
            raise LookupError(f"producto inexistente: id={producto.id}")
        self._conn.commit()
        return producto

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


def _fila_a_movimiento(f: sqlite3.Row) -> MovimientoInventario:
    return MovimientoInventario(
        producto_id=f["producto_id"],
        tipo=f["tipo"],
        cantidad=f["cantidad"],
        fecha=datetime.fromisoformat(f["fecha"]),
        ref=f["ref"],
        lote_id=f["lote_id"],
        id=f["id"],
    )


class RepositorioInventarioSQLite:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def registrar(self, m: MovimientoInventario) -> MovimientoInventario:
        cur = self._conn.execute(
            "INSERT INTO inventario_movimientos "
            "(producto_id, lote_id, tipo, cantidad, fecha, ref) VALUES (?, ?, ?, ?, ?, ?)",
            (m.producto_id, m.lote_id, m.tipo, m.cantidad, m.fecha.isoformat(), m.ref))
        self._conn.commit()
        return replace(m, id=cur.lastrowid)

    def stock_de(self, producto_id: int) -> Decimal:
        filas = self._conn.execute(
            "SELECT tipo, cantidad FROM inventario_movimientos WHERE producto_id = ?",
            (producto_id,)).fetchall()
        total = Decimal("0")
        for f in filas:
            total += f["cantidad"] if f["tipo"] == "entrada" else -f["cantidad"]
        return total

    def movimientos_en(self, desde: datetime, hasta: datetime) -> list[MovimientoInventario]:
        filas = self._conn.execute(
            "SELECT * FROM inventario_movimientos "
            "WHERE fecha >= ? AND fecha < ? ORDER BY id",
            (desde.isoformat(), hasta.isoformat())).fetchall()
        return [_fila_a_movimiento(f) for f in filas]


def _fila_a_promocion(f: sqlite3.Row) -> Promocion:
    return Promocion(
        producto_id=f["producto_id"],
        tipo_valor=f["tipo_valor"],
        valor=f["valor"],
        tipo_duracion=f["tipo_duracion"],
        activa=bool(f["activa"]),
        desde=datetime.fromisoformat(f["desde"]) if f["desde"] else None,
        hasta=datetime.fromisoformat(f["hasta"]) if f["hasta"] else None,
        unidades_limite=f["unidades_limite"],
        unidades_restantes=f["unidades_restantes"],
        id=f["id"],
    )


class RepositorioPromocionesSQLite:
    _COLS = ("producto_id, tipo_valor, valor, tipo_duracion, activa, "
             "desde, hasta, unidades_limite, unidades_restantes")

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def guardar(self, promo: Promocion) -> Promocion:
        cur = self._conn.execute(
            f"INSERT INTO promociones ({self._COLS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            self._valores(promo))
        self._conn.commit()
        return replace(promo, id=cur.lastrowid)

    def actualizar(self, promo: Promocion) -> None:
        cur = self._conn.execute(
            "UPDATE promociones SET producto_id = ?, tipo_valor = ?, valor = ?, "
            "tipo_duracion = ?, activa = ?, desde = ?, hasta = ?, "
            "unidades_limite = ?, unidades_restantes = ? WHERE id = ?",
            (*self._valores(promo), promo.id))
        if cur.rowcount == 0:
            raise LookupError(f"promoción inexistente: id={promo.id}")
        self._conn.commit()

    @staticmethod
    def _valores(promo: Promocion) -> tuple:
        return (
            promo.producto_id, promo.tipo_valor, promo.valor, promo.tipo_duracion,
            int(promo.activa),
            promo.desde.isoformat() if promo.desde else None,
            promo.hasta.isoformat() if promo.hasta else None,
            promo.unidades_limite, promo.unidades_restantes,
        )

    def por_id(self, id: int) -> Promocion | None:
        f = self._conn.execute("SELECT * FROM promociones WHERE id = ?", (id,)).fetchone()
        return _fila_a_promocion(f) if f else None

    def activa_por_producto(self, producto_id: int) -> Promocion | None:
        f = self._conn.execute(
            "SELECT * FROM promociones WHERE producto_id = ? AND activa = 1 "
            "ORDER BY id DESC LIMIT 1", (producto_id,)).fetchone()
        return _fila_a_promocion(f) if f else None

    def listar(self) -> list[Promocion]:
        filas = self._conn.execute("SELECT * FROM promociones ORDER BY id").fetchall()
        return [_fila_a_promocion(f) for f in filas]
