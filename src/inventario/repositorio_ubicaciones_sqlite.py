"""Adaptador SQLite de inventario multi-ubicación: append-only + único flip
pendiente->confirmado. Implementa core.puertos.RepositorioMovimientosUbicacion
más extras de sync (aplicar_delta, cursor por ubicación, bandeja de pendientes)."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from core.servicio_inventario_ubicaciones import stock_por_suma


def _iso(v) -> str:
    return v.isoformat() if hasattr(v, "isoformat") else v


class RepositorioMovimientosUbicacionSQLite:
    def __init__(self, conn) -> None:
        self._conn = conn

    # --- puerto RepositorioMovimientosUbicacion ---
    def registrar(self, mov: dict) -> None:
        fecha_iso = _iso(mov["fecha"])
        self._conn.execute(
            "INSERT OR IGNORE INTO movimientos_ubicacion (uuid, tipo, producto_id, cantidad, "
            "origen_id, destino_id, estado, grupo_uuid, lote_id, ref, fecha, actualizado_en) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (mov["uuid"], mov["tipo"], mov["producto_id"], mov["cantidad"],
             mov.get("origen_id"), mov.get("destino_id"), mov.get("estado", "confirmado"),
             mov.get("grupo_uuid"), mov.get("lote_id"), mov.get("ref"), fecha_iso,
             mov.get("actualizado_en") or fecha_iso))
        self._conn.commit()

    def confirmar(self, uuid: str) -> None:
        self._conn.execute(
            "UPDATE movimientos_ubicacion SET estado='confirmado', actualizado_en=? "
            "WHERE uuid=? AND estado='pendiente'",
            (datetime.now(timezone.utc).isoformat(), uuid))
        self._conn.commit()

    def stock(self, ubicacion_id: int, producto_id: int) -> Decimal:
        filas = self._conn.execute(
            "SELECT tipo, producto_id, cantidad, origen_id, destino_id, estado "
            "FROM movimientos_ubicacion WHERE producto_id=? AND (origen_id=? OR destino_id=?)",
            (producto_id, ubicacion_id, ubicacion_id)).fetchall()
        return stock_por_suma([dict(f) for f in filas], ubicacion_id, producto_id)

    def movimientos_grupo(self, grupo_uuid: str) -> list[dict]:
        return [dict(f) for f in self._conn.execute(
            "SELECT * FROM movimientos_ubicacion WHERE grupo_uuid=? ORDER BY fecha",
            (grupo_uuid,)).fetchall()]

    # --- extras de sync (delta por cursor, bandeja) ---
    def aplicar_delta(self, movimientos: list[dict]) -> None:
        """Aplica el delta bajado de la nube: crea la fila (nueva) o hace el único
        flip pendiente->confirmado; nunca reescribe cantidad/origen/destino."""
        for m in movimientos:
            self._conn.execute(
                "INSERT INTO movimientos_ubicacion (uuid, tipo, producto_id, cantidad, "
                "origen_id, destino_id, estado, grupo_uuid, lote_id, ref, origen_nombre, "
                "fecha, actualizado_en) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?) "
                "ON CONFLICT(uuid) DO UPDATE SET estado=excluded.estado, "
                "actualizado_en=excluded.actualizado_en "
                "WHERE movimientos_ubicacion.estado='pendiente' AND excluded.estado='confirmado'",
                (m["uuid"], m["tipo"], m["producto_id"], Decimal(str(m["cantidad"])),
                 m.get("origen_id"), m.get("destino_id"), m["estado"], m.get("grupo_uuid"),
                 m.get("lote_id"), m.get("ref"), m.get("origen_nombre"),
                 m["fecha"], m["actualizado_en"]))
        self._conn.commit()

    def pendientes(self, ubicacion_id: int) -> list[dict]:
        return [dict(f) for f in self._conn.execute(
            "SELECT * FROM movimientos_ubicacion WHERE destino_id=? AND tipo='entrada' "
            "AND estado='pendiente' ORDER BY fecha", (ubicacion_id,)).fetchall()]

    def cursor(self, ubicacion_id: int) -> str | None:
        f = self._conn.execute(
            "SELECT valor FROM sync_cursor WHERE clave=?",
            (f"inventario:{ubicacion_id}",)).fetchone()
        return f["valor"] if f else None

    def guardar_cursor(self, ubicacion_id: int, valor: str) -> None:
        self._conn.execute(
            "INSERT INTO sync_cursor (clave, valor) VALUES (?, ?) "
            "ON CONFLICT (clave) DO UPDATE SET valor=excluded.valor",
            (f"inventario:{ubicacion_id}", valor))
        self._conn.commit()
