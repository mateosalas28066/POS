"""Adaptadores SQLite de venta, clientes y medios de pago. Único lugar con su SQL."""
from __future__ import annotations

import sqlite3
from dataclasses import replace
from datetime import datetime

from decimal import Decimal

from core.entidades import (
    AbonoCliente, CajaSesion, CategoriaGasto, Cliente, Compra, Despiece, Devolucion, Gasto,
    LineaCompra, LineaDespiece, LineaDevolucion, LineaVenta, MedioPago, MovimientoCaja, Pago,
    PagoProveedor, Proveedor, Usuario, Venta,
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
        descuento_pct=f["descuento_pct"],
        id=f["id"],
    )


class RepositorioClientesSQLite:
    _COLS = ("identificacion, nombre, contacto, bloqueado_edicion, "
             "tipo_documento, regimen, tipo_responsabilidad, descuento_pct")

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def guardar(self, cliente: Cliente) -> Cliente:
        cur = self._conn.execute(
            f"INSERT INTO clientes ({self._COLS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (cliente.identificacion, cliente.nombre, cliente.contacto,
             int(cliente.bloqueado_edicion), cliente.tipo_documento,
             cliente.regimen, cliente.tipo_responsabilidad, cliente.descuento_pct))
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
            "tipo_responsabilidad = ?, descuento_pct = ? WHERE id = ?",
            (cliente.identificacion, cliente.nombre, cliente.contacto,
             int(cliente.bloqueado_edicion), cliente.tipo_documento,
             cliente.regimen, cliente.tipo_responsabilidad, cliente.descuento_pct, cliente.id))
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
        promocion_id=f["promocion_id"],
        venta_id=f["venta_id"],
        id=f["id"],
    )


class RepositorioVentasSQLite:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def guardar(self, venta: Venta, pagos: list[Pago]) -> Venta:
        cur = self._conn.execute(
            "INSERT INTO ventas "
            "(fecha, usuario_id, caja_sesion_id, cliente_id, total, total_impuestos, "
            "estado, descuento_pct) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (venta.fecha.isoformat(), venta.usuario_id, venta.caja_sesion_id,
             venta.cliente_id, venta.total, venta.total_impuestos, venta.estado,
             venta.descuento_pct))
        venta_id = cur.lastrowid
        for linea in venta.lineas:
            self._conn.execute(
                "INSERT INTO venta_lineas "
                "(venta_id, producto_id, descripcion, cantidad_o_peso, precio_unit, "
                "impuesto, subtotal, promocion_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (venta_id, linea.producto_id, linea.descripcion, linea.cantidad_o_peso,
                 linea.precio_unit, linea.impuesto, linea.subtotal, linea.promocion_id))
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
            descuento_pct=fv["descuento_pct"],
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

    def fiado_por_cliente(self, medio_fiado_id: int) -> dict[int, Decimal]:
        filas = self._conn.execute(
            "SELECT v.cliente_id AS cliente_id, p.monto AS monto "
            "FROM pagos p JOIN ventas v ON v.id = p.venta_id "
            "WHERE p.medio_pago_id = ? AND v.estado != 'anulada' AND v.cliente_id IS NOT NULL",
            (medio_fiado_id,)).fetchall()
        total: dict[int, Decimal] = {}
        for f in filas:
            total[f["cliente_id"]] = total.get(f["cliente_id"], Decimal("0")) + f["monto"]
        return total


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

    def listar(self) -> list[CajaSesion]:
        filas = self._conn.execute(
            "SELECT * FROM caja_sesiones ORDER BY id").fetchall()
        return [_fila_a_sesion(f) for f in filas]


class RepositorioMovimientosCajaSQLite:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def registrar(self, m: MovimientoCaja) -> MovimientoCaja:
        cur = self._conn.execute(
            "INSERT INTO caja_movimientos (caja_sesion_id, usuario_id, tipo, monto, motivo, fecha) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (m.caja_sesion_id, m.usuario_id, m.tipo, m.monto, m.motivo, m.fecha.isoformat()))
        self._conn.commit()
        return replace(m, id=cur.lastrowid)

    def de_sesion(self, caja_sesion_id: int) -> list[MovimientoCaja]:
        filas = self._conn.execute(
            "SELECT * FROM caja_movimientos WHERE caja_sesion_id = ? ORDER BY id",
            (caja_sesion_id,)).fetchall()
        return [MovimientoCaja(
            caja_sesion_id=f["caja_sesion_id"], tipo=f["tipo"], monto=f["monto"],
            motivo=f["motivo"], fecha=datetime.fromisoformat(f["fecha"]),
            usuario_id=f["usuario_id"], id=f["id"]) for f in filas]


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


def _fila_a_usuario(f: sqlite3.Row) -> Usuario:
    return Usuario(nombre=f["nombre"], rol=f["rol"], id=f["id"])


class RepositorioUsuariosSQLite:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def guardar(self, usuario: Usuario, hash_password: str) -> Usuario:
        cur = self._conn.execute(
            "INSERT INTO usuarios (nombre, rol, hash_password) VALUES (?, ?, ?)",
            (usuario.nombre, usuario.rol, hash_password))
        self._conn.commit()
        return replace(usuario, id=cur.lastrowid)

    def por_id(self, id: int) -> Usuario | None:
        f = self._conn.execute("SELECT * FROM usuarios WHERE id = ?", (id,)).fetchone()
        return _fila_a_usuario(f) if f else None

    def por_nombre(self, nombre: str) -> Usuario | None:
        f = self._conn.execute("SELECT * FROM usuarios WHERE nombre = ?", (nombre,)).fetchone()
        return _fila_a_usuario(f) if f else None

    def credencial(self, nombre: str) -> tuple[Usuario, str] | None:
        f = self._conn.execute("SELECT * FROM usuarios WHERE nombre = ?", (nombre,)).fetchone()
        return (_fila_a_usuario(f), f["hash_password"]) if f else None

    def actualizar_password(self, usuario_id: int, hash_password: str) -> None:
        cur = self._conn.execute(
            "UPDATE usuarios SET hash_password = ? WHERE id = ?", (hash_password, usuario_id))
        if cur.rowcount == 0:
            raise LookupError(f"usuario inexistente: id={usuario_id}")
        self._conn.commit()

    def listar(self) -> list[Usuario]:
        filas = self._conn.execute("SELECT * FROM usuarios ORDER BY id").fetchall()
        return [_fila_a_usuario(f) for f in filas]


def _fila_a_proveedor(f: sqlite3.Row) -> Proveedor:
    return Proveedor(
        identificacion=f["identificacion"],
        nombre=f["nombre"],
        contacto=f["contacto"],
        bloqueado_edicion=bool(f["bloqueado_edicion"]),
        id=f["id"],
    )


class RepositorioProveedoresSQLite:
    _COLS = "identificacion, nombre, contacto, bloqueado_edicion"

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def guardar(self, proveedor: Proveedor) -> Proveedor:
        cur = self._conn.execute(
            f"INSERT INTO proveedores ({self._COLS}) VALUES (?, ?, ?, ?)",
            (proveedor.identificacion, proveedor.nombre, proveedor.contacto,
             int(proveedor.bloqueado_edicion)))
        self._conn.commit()
        return replace(proveedor, id=cur.lastrowid)

    def por_id(self, id: int) -> Proveedor | None:
        f = self._conn.execute("SELECT * FROM proveedores WHERE id = ?", (id,)).fetchone()
        return _fila_a_proveedor(f) if f else None

    def por_identificacion(self, identificacion: str) -> Proveedor | None:
        f = self._conn.execute(
            "SELECT * FROM proveedores WHERE identificacion = ?", (identificacion,)).fetchone()
        return _fila_a_proveedor(f) if f else None

    def listar(self) -> list[Proveedor]:
        filas = self._conn.execute("SELECT * FROM proveedores ORDER BY id").fetchall()
        return [_fila_a_proveedor(f) for f in filas]

    def actualizar(self, proveedor: Proveedor) -> Proveedor:
        cur = self._conn.execute(
            "UPDATE proveedores SET identificacion = ?, nombre = ?, contacto = ?, "
            "bloqueado_edicion = ? WHERE id = ?",
            (proveedor.identificacion, proveedor.nombre, proveedor.contacto,
             int(proveedor.bloqueado_edicion), proveedor.id))
        if cur.rowcount == 0:
            raise LookupError(f"proveedor inexistente: id={proveedor.id}")
        self._conn.commit()
        return proveedor


def _fila_a_linea_compra(f: sqlite3.Row) -> LineaCompra:
    return LineaCompra(
        producto_id=f["producto_id"],
        descripcion=f["descripcion"],
        cantidad=f["cantidad"],
        costo_unit=f["costo_unit"],
        subtotal=f["subtotal"],
        compra_id=f["compra_id"],
        id=f["id"],
    )


class RepositorioComprasSQLite:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def guardar(self, compra: Compra) -> Compra:
        cur = self._conn.execute(
            "INSERT INTO compras (proveedor_id, fecha, total, estado, usuario_id) "
            "VALUES (?, ?, ?, ?, ?)",
            (compra.proveedor_id, compra.fecha.isoformat(), compra.total,
             compra.estado, compra.usuario_id))
        compra_id = cur.lastrowid
        lineas_guardadas = []
        for linea in compra.lineas:
            lcur = self._conn.execute(
                "INSERT INTO compra_lineas "
                "(compra_id, producto_id, descripcion, cantidad, costo_unit, subtotal) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (compra_id, linea.producto_id, linea.descripcion, linea.cantidad,
                 linea.costo_unit, linea.subtotal))
            lineas_guardadas.append(replace(linea, compra_id=compra_id, id=lcur.lastrowid))
        self._conn.commit()
        return replace(compra, lineas=tuple(lineas_guardadas), id=compra_id)

    def por_id(self, id: int) -> Compra | None:
        fc = self._conn.execute("SELECT * FROM compras WHERE id = ?", (id,)).fetchone()
        if fc is None:
            return None
        filas = self._conn.execute(
            "SELECT * FROM compra_lineas WHERE compra_id = ? ORDER BY id", (id,)).fetchall()
        return Compra(
            proveedor_id=fc["proveedor_id"],
            fecha=datetime.fromisoformat(fc["fecha"]),
            lineas=tuple(_fila_a_linea_compra(f) for f in filas),
            total=fc["total"],
            estado=fc["estado"],
            usuario_id=fc["usuario_id"],
            id=fc["id"],
        )

    def compras_en(self, desde: datetime, hasta: datetime) -> list[Compra]:
        ids = self._conn.execute(
            "SELECT id FROM compras WHERE fecha >= ? AND fecha < ? ORDER BY id",
            (desde.isoformat(), hasta.isoformat())).fetchall()
        return [self.por_id(f["id"]) for f in ids]

    def compras_de_proveedor(self, proveedor_id: int) -> list[Compra]:
        ids = self._conn.execute(
            "SELECT id FROM compras WHERE proveedor_id = ? ORDER BY id",
            (proveedor_id,)).fetchall()
        return [self.por_id(f["id"]) for f in ids]

    def credito_por_proveedor(self) -> dict[int, Decimal]:
        filas = self._conn.execute(
            "SELECT proveedor_id, total FROM compras WHERE estado = 'credito'").fetchall()
        total: dict[int, Decimal] = {}
        for f in filas:
            total[f["proveedor_id"]] = total.get(f["proveedor_id"], Decimal("0")) + f["total"]
        return total


def _fila_a_linea_despiece(f: sqlite3.Row) -> LineaDespiece:
    return LineaDespiece(
        producto_corte_id=f["producto_corte_id"],
        peso=f["peso"],
        costo_asignado=f["costo_asignado"],
        costo_unit=f["costo_unit"],
        despiece_id=f["despiece_id"],
        id=f["id"],
    )


class RepositorioDespiecesSQLite:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def guardar(self, despiece: Despiece) -> Despiece:
        cur = self._conn.execute(
            "INSERT INTO despieces "
            "(producto_canal_id, peso_canal, costo_canal, fecha, usuario_id) "
            "VALUES (?, ?, ?, ?, ?)",
            (despiece.producto_canal_id, despiece.peso_canal, despiece.costo_canal,
             despiece.fecha.isoformat(), despiece.usuario_id))
        despiece_id = cur.lastrowid
        lineas_guardadas = []
        for linea in despiece.lineas:
            lcur = self._conn.execute(
                "INSERT INTO despiece_lineas "
                "(despiece_id, producto_corte_id, peso, costo_asignado, costo_unit) "
                "VALUES (?, ?, ?, ?, ?)",
                (despiece_id, linea.producto_corte_id, linea.peso,
                 linea.costo_asignado, linea.costo_unit))
            lineas_guardadas.append(replace(linea, despiece_id=despiece_id, id=lcur.lastrowid))
        self._conn.commit()
        return replace(despiece, lineas=tuple(lineas_guardadas), id=despiece_id)

    def por_id(self, id: int) -> Despiece | None:
        fd = self._conn.execute("SELECT * FROM despieces WHERE id = ?", (id,)).fetchone()
        if fd is None:
            return None
        filas = self._conn.execute(
            "SELECT * FROM despiece_lineas WHERE despiece_id = ? ORDER BY id", (id,)).fetchall()
        return Despiece(
            producto_canal_id=fd["producto_canal_id"],
            peso_canal=fd["peso_canal"],
            costo_canal=fd["costo_canal"],
            fecha=datetime.fromisoformat(fd["fecha"]),
            lineas=tuple(_fila_a_linea_despiece(f) for f in filas),
            usuario_id=fd["usuario_id"],
            id=fd["id"],
        )


def _fila_a_abono_cliente(f: sqlite3.Row) -> AbonoCliente:
    return AbonoCliente(
        cliente_id=f["cliente_id"],
        monto=f["monto"],
        fecha=datetime.fromisoformat(f["fecha"]),
        medio_pago_id=f["medio_pago_id"],
        caja_sesion_id=f["caja_sesion_id"],
        usuario_id=f["usuario_id"],
        id=f["id"],
    )


class RepositorioCuentasCobrarSQLite:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def guardar(self, abono: AbonoCliente) -> AbonoCliente:
        cur = self._conn.execute(
            "INSERT INTO abonos_cliente "
            "(cliente_id, monto, fecha, medio_pago_id, caja_sesion_id, usuario_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (abono.cliente_id, abono.monto, abono.fecha.isoformat(), abono.medio_pago_id,
             abono.caja_sesion_id, abono.usuario_id))
        self._conn.commit()
        return replace(abono, id=cur.lastrowid)

    def abonos_por_cliente(self) -> dict[int, Decimal]:
        filas = self._conn.execute(
            "SELECT cliente_id, monto FROM abonos_cliente").fetchall()
        total: dict[int, Decimal] = {}
        for f in filas:
            total[f["cliente_id"]] = total.get(f["cliente_id"], Decimal("0")) + f["monto"]
        return total


def _fila_a_pago_proveedor(f: sqlite3.Row) -> PagoProveedor:
    return PagoProveedor(
        proveedor_id=f["proveedor_id"],
        monto=f["monto"],
        fecha=datetime.fromisoformat(f["fecha"]),
        medio_pago_id=f["medio_pago_id"],
        caja_sesion_id=f["caja_sesion_id"],
        usuario_id=f["usuario_id"],
        id=f["id"],
    )


class RepositorioCuentasPagarSQLite:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def guardar(self, pago: PagoProveedor) -> PagoProveedor:
        cur = self._conn.execute(
            "INSERT INTO pagos_proveedor "
            "(proveedor_id, monto, fecha, medio_pago_id, caja_sesion_id, usuario_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (pago.proveedor_id, pago.monto, pago.fecha.isoformat(), pago.medio_pago_id,
             pago.caja_sesion_id, pago.usuario_id))
        self._conn.commit()
        return replace(pago, id=cur.lastrowid)

    def pagos_por_proveedor(self) -> dict[int, Decimal]:
        filas = self._conn.execute(
            "SELECT proveedor_id, monto FROM pagos_proveedor").fetchall()
        total: dict[int, Decimal] = {}
        for f in filas:
            total[f["proveedor_id"]] = total.get(f["proveedor_id"], Decimal("0")) + f["monto"]
        return total


def _fila_a_categoria_gasto(f: sqlite3.Row) -> CategoriaGasto:
    return CategoriaGasto(nombre=f["nombre"], id=f["id"])


class RepositorioCategoriasGastoSQLite:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def guardar(self, categoria: CategoriaGasto) -> CategoriaGasto:
        cur = self._conn.execute(
            "INSERT INTO categorias_gasto (nombre) VALUES (?)", (categoria.nombre,))
        self._conn.commit()
        return replace(categoria, id=cur.lastrowid)

    def listar(self) -> list[CategoriaGasto]:
        filas = self._conn.execute("SELECT * FROM categorias_gasto ORDER BY id").fetchall()
        return [_fila_a_categoria_gasto(f) for f in filas]

    def actualizar(self, categoria: CategoriaGasto) -> CategoriaGasto:
        cur = self._conn.execute(
            "UPDATE categorias_gasto SET nombre = ? WHERE id = ?",
            (categoria.nombre, categoria.id))
        if cur.rowcount == 0:
            raise LookupError(f"categoría de gasto inexistente: id={categoria.id}")
        self._conn.commit()
        return categoria


def _fila_a_gasto(f: sqlite3.Row) -> Gasto:
    return Gasto(
        fecha=datetime.fromisoformat(f["fecha"]),
        categoria_gasto_id=f["categoria_gasto_id"],
        monto=f["monto"],
        descripcion=f["descripcion"],
        medio_pago_id=f["medio_pago_id"],
        caja_sesion_id=f["caja_sesion_id"],
        usuario_id=f["usuario_id"],
        id=f["id"],
    )


class RepositorioGastosSQLite:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def guardar(self, gasto: Gasto) -> Gasto:
        cur = self._conn.execute(
            "INSERT INTO gastos "
            "(fecha, categoria_gasto_id, monto, descripcion, medio_pago_id, caja_sesion_id, "
            "usuario_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (gasto.fecha.isoformat(), gasto.categoria_gasto_id, gasto.monto, gasto.descripcion,
             gasto.medio_pago_id, gasto.caja_sesion_id, gasto.usuario_id))
        self._conn.commit()
        return replace(gasto, id=cur.lastrowid)

    def gastos_en(self, desde: datetime, hasta: datetime) -> list[Gasto]:
        filas = self._conn.execute(
            "SELECT * FROM gastos WHERE fecha >= ? AND fecha < ? ORDER BY id",
            (desde.isoformat(), hasta.isoformat())).fetchall()
        return [_fila_a_gasto(f) for f in filas]
