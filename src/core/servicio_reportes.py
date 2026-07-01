"""Reportes de solo lectura: agrega en Python lo que los repos leen. Sin Qt ni SQLite."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from core.calculos import calcular_arqueo
from core.entidades import Arqueo, CajaSesion, MovimientoInventario
from core.puertos import (
    RepositorioCajaSesiones, RepositorioDevoluciones, RepositorioInventario, RepositorioVentas,
)

CERO = Decimal("0")


class SesionNoEncontrada(ValueError):
    pass


@dataclass(frozen=True)
class ReporteVentas:
    desde: datetime
    hasta: datetime
    num_ventas: int
    total: Decimal
    total_impuestos: Decimal
    por_medio: dict[int, Decimal]          # neto por medio: Σ pagos − Σ reembolsos
    total_devoluciones: Decimal
    total_devoluciones_impuestos: Decimal
    neto: Decimal                          # total − total_devoluciones


@dataclass(frozen=True)
class ReporteCajero:
    usuario_id: int | None
    num_ventas: int
    total: Decimal
    total_impuestos: Decimal
    total_devoluciones: Decimal
    neto: Decimal
    por_medio: dict[int, Decimal]


@dataclass(frozen=True)
class MovimientoProducto:
    producto_id: int
    entradas: Decimal
    salidas: Decimal
    neto: Decimal


@dataclass(frozen=True)
class ReporteInventario:
    desde: datetime
    hasta: datetime
    por_producto: tuple[MovimientoProducto, ...]
    movimientos: tuple[MovimientoInventario, ...]


@dataclass(frozen=True)
class ReporteCierre:
    sesion: CajaSesion
    arqueo: Arqueo
    por_medio: dict[int, Decimal]
    num_ventas: int
    total_devoluciones: Decimal


class ServicioReportes:
    def __init__(self, ventas: RepositorioVentas, devoluciones: RepositorioDevoluciones,
                 inventario: RepositorioInventario, sesiones: RepositorioCajaSesiones,
                 efectivo_medio_pago_id: int = 1) -> None:
        self._ventas = ventas
        self._devoluciones = devoluciones
        self._inventario = inventario
        self._sesiones = sesiones
        self._efectivo_id = efectivo_medio_pago_id

    def ventas(self, desde: datetime, hasta: datetime) -> ReporteVentas:
        vs = self._ventas.ventas_en(desde, hasta)
        pagos = self._ventas.pagos_en(desde, hasta)
        devs = self._devoluciones.devoluciones_en(desde, hasta)
        total = sum((v.total for v in vs), CERO)
        total_impuestos = sum((v.total_impuestos for v in vs), CERO)
        total_devoluciones = sum((d.total for d in devs), CERO)
        total_devoluciones_impuestos = sum((d.total_impuestos for d in devs), CERO)
        por_medio: dict[int, Decimal] = {}
        for p in pagos:
            por_medio[p.medio_pago_id] = por_medio.get(p.medio_pago_id, CERO) + p.monto
        for d in devs:
            for r in d.reembolsos:
                por_medio[r.medio_pago_id] = por_medio.get(r.medio_pago_id, CERO) - r.monto
        return ReporteVentas(
            desde=desde, hasta=hasta, num_ventas=len(vs), total=total,
            total_impuestos=total_impuestos, por_medio=por_medio,
            total_devoluciones=total_devoluciones,
            total_devoluciones_impuestos=total_devoluciones_impuestos,
            neto=total - total_devoluciones)

    def inventario(self, desde: datetime, hasta: datetime) -> ReporteInventario:
        movs = self._inventario.movimientos_en(desde, hasta)
        entradas: dict[int, Decimal] = {}
        salidas: dict[int, Decimal] = {}
        for m in movs:
            destino = entradas if m.tipo == "entrada" else salidas
            destino[m.producto_id] = destino.get(m.producto_id, CERO) + m.cantidad
        por_producto = tuple(
            MovimientoProducto(
                producto_id=pid,
                entradas=entradas.get(pid, CERO),
                salidas=salidas.get(pid, CERO),
                neto=entradas.get(pid, CERO) - salidas.get(pid, CERO))
            for pid in sorted(set(entradas) | set(salidas)))
        return ReporteInventario(desde=desde, hasta=hasta,
                                 por_producto=por_producto, movimientos=tuple(movs))

    def cierre(self, sesion_id: int) -> ReporteCierre:
        sesion = self._sesiones.por_id(sesion_id)
        if sesion is None:
            raise SesionNoEncontrada(f"sesion de caja inexistente: {sesion_id}")
        por_medio = self._ventas.totales_por_medio(sesion_id)
        efectivo = por_medio.get(self._efectivo_id, CERO)
        esperado = sesion.monto_inicial + efectivo
        contado = sesion.monto_contado if sesion.monto_contado is not None else esperado
        arqueo = calcular_arqueo(sesion.monto_inicial, efectivo, contado)
        num_ventas = len(self._ventas.ventas_de_sesion(sesion_id))
        total_devoluciones = sum((d.total for d in self._devoluciones.de_sesion(sesion_id)), CERO)
        return ReporteCierre(sesion=sesion, arqueo=arqueo, por_medio=por_medio,
                             num_ventas=num_ventas, total_devoluciones=total_devoluciones)

    def por_cajero(self, desde: datetime, hasta: datetime) -> tuple[ReporteCajero, ...]:
        vs = self._ventas.ventas_en(desde, hasta)
        usuario_de_venta = {v.id: v.usuario_id for v in vs}
        pagos = [(usuario_de_venta[p.venta_id], p)
                 for p in self._ventas.pagos_en(desde, hasta)
                 if p.venta_id in usuario_de_venta]
        devs = self._devoluciones.devoluciones_en(desde, hasta)
        return self._por_cajero(vs, pagos, devs)

    def por_cajero_de_sesion(self, sesion_id: int) -> tuple[ReporteCajero, ...]:
        if self._sesiones.por_id(sesion_id) is None:
            raise SesionNoEncontrada(f"sesion de caja inexistente: {sesion_id}")
        vs = self._ventas.ventas_de_sesion(sesion_id)
        pagos = [(v.usuario_id, p) for v in vs for p in self._ventas.pagos_de(v.id)]
        devs = self._devoluciones.de_sesion(sesion_id)
        return self._por_cajero(vs, pagos, devs)

    def _por_cajero(self, vs, pagos, devs) -> tuple[ReporteCajero, ...]:
        agg: dict[int | None, dict] = {}

        def bucket(uid: int | None) -> dict:
            return agg.setdefault(
                uid, {"num": 0, "total": CERO, "imp": CERO, "dev": CERO, "medio": {}})

        for v in vs:
            b = bucket(v.usuario_id)
            b["num"] += 1
            b["total"] += v.total
            b["imp"] += v.total_impuestos
        for uid, p in pagos:
            m = bucket(uid)["medio"]
            m[p.medio_pago_id] = m.get(p.medio_pago_id, CERO) + p.monto
        for d in devs:
            b = bucket(d.usuario_id)
            b["dev"] += d.total
            for r in d.reembolsos:
                m = b["medio"]
                m[r.medio_pago_id] = m.get(r.medio_pago_id, CERO) - r.monto
        reportes = [
            ReporteCajero(usuario_id=uid, num_ventas=b["num"], total=b["total"],
                          total_impuestos=b["imp"], total_devoluciones=b["dev"],
                          neto=b["total"] - b["dev"], por_medio=b["medio"])
            for uid, b in agg.items()]
        return tuple(sorted(reportes,
                            key=lambda r: (r.usuario_id is None, r.usuario_id or 0)))
