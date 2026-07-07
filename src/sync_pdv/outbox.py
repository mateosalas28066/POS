"""Outbox local: cola SQLite de eventos append-only pendientes de subir a la nube."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from core.entidades import Pago, Venta


@dataclass(frozen=True)
class EventoSync:
    uuid: str
    local_id: str
    tipo: str
    payload: dict
    creado_en: str


class RepositorioOutboxSQLite:
    def __init__(self, conn) -> None:
        self._conn = conn

    def encolar(self, evento: EventoSync) -> None:
        self._conn.execute(
            "INSERT OR IGNORE INTO eventos_sync (uuid, local_id, tipo, payload, creado_en) "
            "VALUES (?, ?, ?, ?, ?)",
            (evento.uuid, evento.local_id, evento.tipo,
             json.dumps(evento.payload), evento.creado_en))
        self._conn.commit()

    def pendientes(self, limite: int = 100) -> list[EventoSync]:
        filas = self._conn.execute(
            "SELECT uuid, local_id, tipo, payload, creado_en FROM eventos_sync "
            "WHERE enviado_en IS NULL ORDER BY creado_en LIMIT ?", (limite,)).fetchall()
        return [EventoSync(f[0], f[1], f[2], json.loads(f[3]), f[4]) for f in filas]

    def marcar_enviados(self, uuids: list[str]) -> None:
        ahora = datetime.now(timezone.utc).isoformat()
        self._conn.executemany(
            "UPDATE eventos_sync SET enviado_en = ? WHERE uuid = ?",
            [(ahora, u) for u in uuids])
        self._conn.commit()


def serializar_venta(venta: Venta, pagos: list[Pago], almacen_id: int, local_id: str) -> EventoSync:
    payload = {
        "id": venta.id,
        "almacen_id": almacen_id,
        "local_id": local_id,
        "usuario_id": venta.usuario_id,
        "cliente_id": venta.cliente_id,
        "sesion_id": venta.caja_sesion_id,
        "fecha": venta.fecha.isoformat(),
        "total": str(venta.total),
        "total_impuestos": str(venta.total_impuestos),
        "lineas": [{"producto_id": ln.producto_id, "cantidad": str(ln.cantidad_o_peso),
                    "subtotal": str(ln.subtotal), "impuesto": str(ln.impuesto)}
                   for ln in venta.lineas],
        "pagos": [{"medio_pago_id": p.medio_pago_id, "monto": str(p.monto)} for p in pagos],
    }
    return EventoSync(uuid=str(uuid4()), local_id=local_id, tipo="venta",
                      payload=payload, creado_en=datetime.now(timezone.utc).isoformat())
