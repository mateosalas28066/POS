"""Outbox local: cola SQLite de eventos append-only pendientes de subir a la nube."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from core.entidades import Pago, Producto, Promocion, Venta


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


def _evento(local_id: str, tipo: str, payload: dict) -> EventoSync:
    return EventoSync(uuid=str(uuid4()), local_id=local_id, tipo=tipo,
                      payload=payload, creado_en=datetime.now(timezone.utc).isoformat())


def _str_o_none(v) -> str | None:
    return None if v is None else str(v)


def serializar_overlay(local_id: str, producto_id: int, precio, costo, activo: bool,
                       actualizado_en: str) -> EventoSync:
    """Evento de precio/costo/activo local (overlay) para materializar en la nube (LWW)."""
    return _evento(local_id, "catalogo_overlay", {
        "local_id": local_id, "producto_id": producto_id,
        "precio": str(precio), "costo": str(costo), "activo": activo,
        "actualizado_en": actualizado_en})


def serializar_producto_maestro(p: Producto, local_id: str, actualizado_en: str) -> EventoSync:
    """Evento de alta/edición del maestro (nombre, unidad, impuesto, costo default)."""
    return _evento(local_id, "catalogo_producto", {
        "id": p.id, "codigo_barras": p.codigo_barras, "nombre": p.nombre,
        "unidad": p.unidad, "vendido_por_peso": p.vendido_por_peso,
        "categoria_id": p.categoria_id, "impuesto_id": p.impuesto_id,
        "costo": str(p.costo), "actualizado_en": actualizado_en})


def serializar_promo(promo: Promocion, local_id: str, actualizado_en: str) -> EventoSync:
    """Evento de promoción por (producto, local) = campos de core.Promocion + local/ts."""
    return _evento(local_id, "catalogo_promo", {
        "id": promo.id, "producto_id": promo.producto_id, "local_id": local_id,
        "tipo_valor": promo.tipo_valor, "valor": str(promo.valor),
        "tipo_duracion": promo.tipo_duracion, "activa": promo.activa,
        "desde": promo.desde.isoformat() if promo.desde else None,
        "hasta": promo.hasta.isoformat() if promo.hasta else None,
        "unidades_limite": _str_o_none(promo.unidades_limite),
        "unidades_restantes": _str_o_none(promo.unidades_restantes),
        "actualizado_en": actualizado_en})
