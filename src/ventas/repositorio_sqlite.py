"""Adaptadores SQLite de venta, clientes y medios de pago. Único lugar con su SQL."""
from __future__ import annotations

import sqlite3
from dataclasses import replace
from datetime import datetime

from decimal import Decimal

from core.entidades import (
    CajaSesion, Cliente, Devolucion, LineaDevolucion, LineaVenta, MedioPago, Pago, Venta,
)


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

    def actualizar(self, cliente: Cliente) -> Cliente:
        cur = self._conn.execute(
            "UPDATE clientes SET identificacion = ?, nombre = ?, contacto = ?, "
            "bloqueado_edicion = ?, tipo_documento = ?, regimen = ?, "
            "tipo_responsabilidad = ? WHERE id = ?",
            (cliente.identificacion, cliente.nombre, cliente.contacto,
             int(cliente.bloqueado_edicion), cliente.tipo_documento,
             cliente.regimen, cliente.tipo_responsabilidad, cliente.id))
        if cur.rowcount == 0:
            raise LookupError(f"cliente inexistente: id={cliente.id}")
        self._conn.commit()
        return cliente


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
        for linea in venta.lineas:
            self._conn.execute(
                "INSERT INTO venta_lineas "
                "(venta_id, producto_id, descripcion, cantidad_o_peso, precio_unit, "
                "impuesto, subtotal) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (venta_id, linea.producto_id, linea.descripcion, linea.cantidad_o_peso,
                 linea.precio_unit, linea.impuesto, linea.subtotal))
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

    def marcar_estado(self, venta_id: int, estado: str) -> None:
        self._conn.execute(
            "UPDATE ventas SET estado = ? WHERE id = ?", (estado, venta_id))
        self._conn.commit()

    def anular(self, venta_id: int) -> None:
        self.marcar_estado(venta_id, "anulada")

    def totales_por_medio(self, caja_sesion_id: int) -> dict[int, Decimal]:
        ingresos = self._conn.execute(
            "SELECT p.medio_pago_id AS medio_pago_id, p.monto AS monto "
            "FROM pagos p JOIN ventas v ON v.id = p.venta_id "
            "WHERE v.caja_sesion_id = ? AND v.estado != 'anulada'",
            (caja_sesion_id,)).fetchall()
        egresos = self._conn.execute(
            "SELECT r.medio_pago_id AS medio_pago_id, r.monto AS monto "
            "FROM devolucion_reembolsos r JOIN devoluciones d ON d.id = r.devolucion_id "
            "WHERE d.caja_sesion_id = ?",
            (caja_sesion_id,)).fetchall()
        totales: dict[int, Decimal] = {}
        for f in ingresos:
            totales[f["medio_pago_id"]] = totales.get(f["medio_pago_id"], Decimal("0")) + f["monto"]
        for f in egresos:
            totales[f["medio_pago_id"]] = totales.get(f["medio_pago_id"], Decimal("0")) - f["monto"]
        return totales

    def ventas_en(self, desde: datetime, hasta: datetime) -> list[Venta]:
        ids = self._conn.execute(
            "SELECT id FROM ventas "
            "WHERE fecha >= ? AND fecha < ? AND estado != 'anulada' ORDER BY id",
            (desde.isoformat(), hasta.isoformat())).fetchall()
        return [self.por_id(f["id"]) for f in ids]

    def ventas_de_sesion(self, caja_sesion_id: int) -> list[Venta]:
        ids = self._conn.execute(
            "SELECT id FROM ventas "
            "WHERE caja_sesion_id = ? AND estado != 'anulada' ORDER BY id",
            (caja_sesion_id,)).fetchall()
        return [self.por_id(f["id"]) for f in ids]

    def pagos_en(self, desde: datetime, hasta: datetime) -> list[Pago]:
        filas = self._conn.execute(
            "SELECT p.* FROM pagos p JOIN ventas v ON v.id = p.venta_id "
            "WHERE v.fecha >= ? AND v.fecha < ? AND v.estado != 'anulada' ORDER BY p.id",
            (desde.isoformat(), hasta.isoformat())).fetchall()
        return [Pago(medio_pago_id=f["medio_pago_id"], monto=f["monto"],
                     referencia=f["referencia"], venta_id=f["venta_id"], id=f["id"])
                for f in filas]


def _fila_a_sesion(f: sqlite3.Row) -> CajaSesion:
    return CajaSesion(
        apertura_fecha=datetime.fromisoformat(f["apertura_fecha"]),
        monto_inicial=f["monto_inicial"],
        usuario_id=f["usuario_id"],
        cierre_fecha=datetime.fromisoformat(f["cierre_fecha"]) if f["cierre_fecha"] else None,
        monto_contado=f["monto_contado"],
        estado=f["estado"],
        id=f["id"],
    )


class RepositorioCajaSesionesSQLite:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def abrir(self, s: CajaSesion) -> CajaSesion:
        cur = self._conn.execute(
            "INSERT INTO caja_sesiones (usuario_id, apertura_fecha, monto_inicial, estado) "
            "VALUES (?, ?, ?, ?)",
            (s.usuario_id, s.apertura_fecha.isoformat(), s.monto_inicial, s.estado))
        self._conn.commit()
        return replace(s, id=cur.lastrowid)

    def cerrar(self, s: CajaSesion) -> CajaSesion:
        self._conn.execute(
            "UPDATE caja_sesiones SET cierre_fecha = ?, monto_contado = ?, estado = ? "
            "WHERE id = ?",
            (s.cierre_fecha.isoformat() if s.cierre_fecha else None,
             s.monto_contado, s.estado, s.id))
        self._conn.commit()
        return s

    def por_id(self, id: int) -> CajaSesion | None:
        f = self._conn.execute("SELECT * FROM caja_sesiones WHERE id = ?", (id,)).fetchone()
        return _fila_a_sesion(f) if f else None

    def abierta(self) -> CajaSesion | None:
        f = self._conn.execute(
            "SELECT * FROM caja_sesiones WHERE estado = 'abierta' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return _fila_a_sesion(f) if f else None


def _fila_a_linea_dev(f: sqlite3.Row) -> LineaDevolucion:
    return LineaDevolucion(
        producto_id=f["producto_id"],
        cantidad_o_peso=f["cantidad_o_peso"],
        impuesto=f["impuesto"],
        subtotal=f["subtotal"],
        venta_linea_id=f["venta_linea_id"],
        devolucion_id=f["devolucion_id"],
        id=f["id"],
    )


class RepositorioDevolucionesSQLite:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def guardar(self, d: Devolucion) -> Devolucion:
        cur = self._conn.execute(
            "INSERT INTO devoluciones "
            "(venta_id, fecha, caja_sesion_id, usuario_id, total, total_impuestos, estado) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (d.venta_id, d.fecha.isoformat(), d.caja_sesion_id, d.usuario_id,
             d.total, d.total_impuestos, d.estado))
        dev_id = cur.lastrowid
        for linea in d.lineas:
            self._conn.execute(
                "INSERT INTO devolucion_lineas "
                "(devolucion_id, venta_linea_id, producto_id, cantidad_o_peso, impuesto, subtotal) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (dev_id, linea.venta_linea_id, linea.producto_id, linea.cantidad_o_peso,
                 linea.impuesto, linea.subtotal))
        for r in d.reembolsos:
            self._conn.execute(
                "INSERT INTO devolucion_reembolsos (devolucion_id, medio_pago_id, monto, referencia) "
                "VALUES (?, ?, ?, ?)",
                (dev_id, r.medio_pago_id, r.monto, r.referencia))
        self._conn.commit()
        return replace(d, id=dev_id)

    def por_id(self, id: int) -> Devolucion | None:
        fd = self._conn.execute("SELECT * FROM devoluciones WHERE id = ?", (id,)).fetchone()
        if fd is None:
            return None
        lineas = self._conn.execute(
            "SELECT * FROM devolucion_lineas WHERE devolucion_id = ? ORDER BY id", (id,)).fetchall()
        reembolsos = self._conn.execute(
            "SELECT * FROM devolucion_reembolsos WHERE devolucion_id = ? ORDER BY id", (id,)).fetchall()
        return Devolucion(
            venta_id=fd["venta_id"],
            fecha=datetime.fromisoformat(fd["fecha"]),
            lineas=tuple(_fila_a_linea_dev(f) for f in lineas),
            total=fd["total"],
            total_impuestos=fd["total_impuestos"],
            reembolsos=tuple(Pago(medio_pago_id=r["medio_pago_id"], monto=r["monto"],
                                  referencia=r["referencia"], id=r["id"]) for r in reembolsos),
            caja_sesion_id=fd["caja_sesion_id"],
            usuario_id=fd["usuario_id"],
            estado=fd["estado"],
            id=fd["id"],
        )

    def de_venta(self, venta_id: int) -> list[Devolucion]:
        ids = self._conn.execute(
            "SELECT id FROM devoluciones WHERE venta_id = ? ORDER BY id", (venta_id,)).fetchall()
        return [self.por_id(f["id"]) for f in ids]

    def devoluciones_en(self, desde: datetime, hasta: datetime) -> list[Devolucion]:
        ids = self._conn.execute(
            "SELECT id FROM devoluciones WHERE fecha >= ? AND fecha < ? ORDER BY id",
            (desde.isoformat(), hasta.isoformat())).fetchall()
        return [self.por_id(f["id"]) for f in ids]

    def de_sesion(self, caja_sesion_id: int) -> list[Devolucion]:
        ids = self._conn.execute(
            "SELECT id FROM devoluciones WHERE caja_sesion_id = ? ORDER BY id",
            (caja_sesion_id,)).fetchall()
        return [self.por_id(f["id"]) for f in ids]

    def devuelto_por_linea(self, venta_id: int) -> dict[int, Decimal]:
        filas = self._conn.execute(
            "SELECT dl.venta_linea_id AS venta_linea_id, dl.cantidad_o_peso AS cantidad "
            "FROM devolucion_lineas dl JOIN devoluciones d ON d.id = dl.devolucion_id "
            "WHERE d.venta_id = ?",
            (venta_id,)).fetchall()
        acum: dict[int, Decimal] = {}
        for f in filas:
            acum[f["venta_linea_id"]] = acum.get(f["venta_linea_id"], Decimal("0")) + f["cantidad"]
        return acum
