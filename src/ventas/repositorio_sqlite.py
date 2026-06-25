"""Adaptadores SQLite de venta, clientes y medios de pago. Único lugar con su SQL."""
from __future__ import annotations

import sqlite3
from dataclasses import replace
from datetime import datetime

from core.entidades import Cliente, LineaVenta, MedioPago, Pago, Venta


def _fila_a_cliente(f: sqlite3.Row) -> Cliente:
    return Cliente(
        identificacion=f["identificacion"],
        nombre=f["nombre"],
        contacto=f["contacto"],
        bloqueado_edicion=bool(f["bloqueado_edicion"]),
        tipo_documento=f["tipo_documento"],
        regimen=f["regimen"],
        tipo_responsabilidad=f["tipo_responsabilidad"],
        id=f["id"],
    )


class RepositorioClientesSQLite:
    _COLS = ("identificacion, nombre, contacto, bloqueado_edicion, "
             "tipo_documento, regimen, tipo_responsabilidad")

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def guardar(self, cliente: Cliente) -> Cliente:
        cur = self._conn.execute(
            f"INSERT INTO clientes ({self._COLS}) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (cliente.identificacion, cliente.nombre, cliente.contacto,
             int(cliente.bloqueado_edicion), cliente.tipo_documento,
             cliente.regimen, cliente.tipo_responsabilidad))
        self._conn.commit()
        return replace(cliente, id=cur.lastrowid)

    def por_id(self, id: int) -> Cliente | None:
        f = self._conn.execute("SELECT * FROM clientes WHERE id = ?", (id,)).fetchone()
        return _fila_a_cliente(f) if f else None

    def por_identificacion(self, identificacion: str) -> Cliente | None:
        f = self._conn.execute(
            "SELECT * FROM clientes WHERE identificacion = ?", (identificacion,)).fetchone()
        return _fila_a_cliente(f) if f else None

    def listar(self) -> list[Cliente]:
        filas = self._conn.execute("SELECT * FROM clientes ORDER BY id").fetchall()
        return [_fila_a_cliente(f) for f in filas]


class RepositorioMediosPagoSQLite:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def listar(self) -> list[MedioPago]:
        filas = self._conn.execute("SELECT * FROM medios_pago ORDER BY id").fetchall()
        return [MedioPago(nombre=f["nombre"], id=f["id"]) for f in filas]

    def por_id(self, id: int) -> MedioPago | None:
        f = self._conn.execute("SELECT * FROM medios_pago WHERE id = ?", (id,)).fetchone()
        return MedioPago(nombre=f["nombre"], id=f["id"]) if f else None


def _fila_a_linea(f: sqlite3.Row) -> LineaVenta:
    return LineaVenta(
        producto_id=f["producto_id"],
        descripcion=f["descripcion"],
        cantidad_o_peso=f["cantidad_o_peso"],
        precio_unit=f["precio_unit"],
        impuesto=f["impuesto"],
        subtotal=f["subtotal"],
        venta_id=f["venta_id"],
        id=f["id"],
    )


class RepositorioVentasSQLite:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def guardar(self, venta: Venta, pagos: list[Pago]) -> Venta:
        cur = self._conn.execute(
            "INSERT INTO ventas "
            "(fecha, usuario_id, caja_sesion_id, cliente_id, total, total_impuestos, estado) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (venta.fecha.isoformat(), venta.usuario_id, venta.caja_sesion_id,
             venta.cliente_id, venta.total, venta.total_impuestos, venta.estado))
        venta_id = cur.lastrowid
        for l in venta.lineas:
            self._conn.execute(
                "INSERT INTO venta_lineas "
                "(venta_id, producto_id, descripcion, cantidad_o_peso, precio_unit, "
                "impuesto, subtotal) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (venta_id, l.producto_id, l.descripcion, l.cantidad_o_peso,
                 l.precio_unit, l.impuesto, l.subtotal))
        for pago in pagos:
            self._conn.execute(
                "INSERT INTO pagos (venta_id, medio_pago_id, monto, referencia) "
                "VALUES (?, ?, ?, ?)",
                (venta_id, pago.medio_pago_id, pago.monto, pago.referencia))
        self._conn.commit()
        return replace(venta, id=venta_id)

    def por_id(self, id: int) -> Venta | None:
        fv = self._conn.execute("SELECT * FROM ventas WHERE id = ?", (id,)).fetchone()
        if fv is None:
            return None
        filas = self._conn.execute(
            "SELECT * FROM venta_lineas WHERE venta_id = ? ORDER BY id", (id,)).fetchall()
        return Venta(
            fecha=datetime.fromisoformat(fv["fecha"]),
            lineas=tuple(_fila_a_linea(f) for f in filas),
            total=fv["total"],
            total_impuestos=fv["total_impuestos"],
            usuario_id=fv["usuario_id"],
            caja_sesion_id=fv["caja_sesion_id"],
            cliente_id=fv["cliente_id"],
            estado=fv["estado"],
            id=fv["id"],
        )

    def pagos_de(self, venta_id: int) -> list[Pago]:
        filas = self._conn.execute(
            "SELECT * FROM pagos WHERE venta_id = ? ORDER BY id", (venta_id,)).fetchall()
        return [Pago(medio_pago_id=f["medio_pago_id"], monto=f["monto"],
                     referencia=f["referencia"], venta_id=f["venta_id"], id=f["id"])
                for f in filas]
