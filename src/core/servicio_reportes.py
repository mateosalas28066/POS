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
