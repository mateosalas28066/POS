"""Adaptador SQLite de la réplica RO del catálogo. Reemplaza el espejo con el snapshot."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal


class RepositorioReplicaSQLite:
    def __init__(self, conn) -> None:
        self._conn = conn

    def aplicar_catalogo(self, snapshot: dict) -> None:
        prods = snapshot.get("productos", [])
        promos = snapshot.get("promociones", [])
        # Precios previos, para detectar los que cambiaron desde la nube (aviso no bloqueante).
        anteriores = {r["producto_id"]: r["precio"] for r in self._conn.execute(
            "SELECT producto_id, precio FROM catalogo_replica")}
        self._conn.execute("DELETE FROM catalogo_replica")
        self._conn.execute("DELETE FROM promo_replica")
        self._conn.executemany(
            "INSERT INTO catalogo_replica (producto_id, codigo_barras, nombre, unidad, "
            "vendido_por_peso, categoria_id, categoria_nombre, impuesto_id, tarifa_impuesto, "
            "precio, costo, activo, actualizado_en) VALUES (?,?,?,?,?,?,?,?,?,?,?,1,?)",
            [(p["producto_id"], p["codigo_barras"], p["nombre"], p["unidad"],
              int(p["vendido_por_peso"]), p["categoria_id"], p["categoria_nombre"],
              p["impuesto_id"],
              None if p["tarifa_impuesto"] is None else Decimal(p["tarifa_impuesto"]),
              Decimal(p["precio"]), Decimal(p["costo"]), p["actualizado_en"]) for p in prods])
        self._conn.executemany(
            "INSERT INTO promo_replica (id, producto_id, tipo_valor, valor, tipo_duracion, "
            "activa, desde, hasta, unidades_limite, unidades_restantes, actualizado_en) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            [(pr["id"], pr["producto_id"], pr["tipo_valor"], Decimal(pr["valor"]),
              pr["tipo_duracion"], int(pr["activa"]), pr["desde"], pr["hasta"],
              None if pr["unidades_limite"] is None else Decimal(pr["unidades_limite"]),
              None if pr["unidades_restantes"] is None else Decimal(pr["unidades_restantes"]),
              pr["actualizado_en"]) for pr in promos])
        ahora = datetime.now(timezone.utc).isoformat()
        for p in prods:
            previo = anteriores.get(p["producto_id"])
            nuevo = Decimal(p["precio"])
            if previo is not None and previo != nuevo:   # solo cambios, no la primera carga
                self._conn.execute(
                    "INSERT INTO novedades_catalogo "
                    "(producto_id, nombre, precio_anterior, precio_nuevo, detectado_en) "
                    "VALUES (?,?,?,?,?)",
                    (p["producto_id"], p["nombre"], previo, nuevo, ahora))
        if prods:
            cursor = max(p["actualizado_en"] for p in prods)
            self._conn.execute(
                "INSERT INTO sync_cursor (clave, valor) VALUES ('catalogo', ?) "
                "ON CONFLICT (clave) DO UPDATE SET valor=excluded.valor", (cursor,))
        self._conn.commit()

    def novedades_pendientes(self) -> list[dict]:
        return [dict(f) for f in self._conn.execute(
            "SELECT id, producto_id, nombre, precio_anterior, precio_nuevo, detectado_en "
            "FROM novedades_catalogo WHERE visto = 0 ORDER BY detectado_en, id")]

    def marcar_novedades_vistas(self) -> None:
        self._conn.execute("UPDATE novedades_catalogo SET visto = 1 WHERE visto = 0")
        self._conn.commit()

    def precio_de(self, producto_id: int) -> Decimal | None:
        f = self._conn.execute(
            "SELECT precio FROM catalogo_replica WHERE producto_id=?", (producto_id,)).fetchone()
        return f["precio"] if f else None

    def producto(self, producto_id: int) -> dict | None:
        f = self._conn.execute(
            "SELECT * FROM catalogo_replica WHERE producto_id=?", (producto_id,)).fetchone()
        return dict(f) if f else None

    def listar(self) -> list[dict]:
        return [dict(f) for f in self._conn.execute(
            "SELECT * FROM catalogo_replica WHERE activo ORDER BY nombre").fetchall()]


class RepositorioProductosConReplica:
    """Envuelve un RepositorioProductos: el precio de venta sale de la réplica RO
    cuando existe; si no (primer arranque sin sync, o id sin correspondencia), cae
    al precio local (offline-first). El resto de métodos se delega al repo interno."""

    def __init__(self, interno, replica: RepositorioReplicaSQLite) -> None:
        self._interno = interno
        self._replica = replica

    def por_codigo(self, codigo_barras: str):
        return self._con_precio(self._interno.por_codigo(codigo_barras))

    def por_id(self, id: int):
        return self._con_precio(self._interno.por_id(id))

    def listar(self):
        return [self._con_precio(p) for p in self._interno.listar()]

    def _con_precio(self, producto):
        if producto is None or producto.id is None:
            return producto
        precio = self._replica.precio_de(producto.id)
        return replace(producto, precio=precio) if precio is not None else producto

    def __getattr__(self, nombre):
        return getattr(self._interno, nombre)   # guardar/actualizar/listar delegados
