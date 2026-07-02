"""Servicio de apertura/cierre y arqueo de caja. Python puro: solo conoce puertos."""
from __future__ import annotations
from dataclasses import replace
from datetime import datetime
from decimal import Decimal
from core.calculos import calcular_arqueo
from core.entidades import Arqueo, CajaSesion, MovimientoCaja
from core.puertos import RepositorioCajaSesiones, RepositorioMovimientosCaja, RepositorioVentas

CERO = Decimal("0")


class CajaYaAbierta(RuntimeError):
    pass


class CajaNoEncontrada(ValueError):
    pass


class CajaNoAbierta(ValueError):
    pass


class EfectivoInsuficiente(ValueError):
    pass


class ServicioCaja:
    def __init__(self, sesiones: RepositorioCajaSesiones, ventas: RepositorioVentas,
                 efectivo_medio_pago_id: int = 1, *,
                 movimientos: RepositorioMovimientosCaja | None = None) -> None:
        self._sesiones = sesiones
        self._ventas = ventas
        self._efectivo_id = efectivo_medio_pago_id
        self._movimientos = movimientos

    def abrir(self, *, fecha: datetime, monto_inicial: Decimal,
              usuario_id: int | None = None) -> CajaSesion:
        if self._sesiones.abierta() is not None:
            raise CajaYaAbierta("ya existe una sesion de caja abierta")
        return self._sesiones.abrir(CajaSesion(
            apertura_fecha=fecha, monto_inicial=monto_inicial, usuario_id=usuario_id))

    def _arqueo(self, sesion: CajaSesion, monto_contado: Decimal) -> Arqueo:
        totales = self._ventas.totales_por_medio(sesion.id)
        ingresos, egresos = self._totales_movimientos(sesion.id)
        return calcular_arqueo(sesion.monto_inicial, totales.get(self._efectivo_id, CERO),
                               monto_contado, ingresos, egresos)

    def _totales_movimientos(self, sesion_id: int) -> tuple[Decimal, Decimal]:
        if self._movimientos is None:
            return CERO, CERO
        movs = self._movimientos.de_sesion(sesion_id)
        ingresos = sum((m.monto for m in movs if m.tipo == "ingreso"), CERO)
        egresos = sum((m.monto for m in movs if m.tipo == "egreso"), CERO)
        return ingresos, egresos

    def registrar_movimiento(self, *, tipo: str, monto: Decimal, motivo: str,
                             fecha: datetime, usuario_id: int | None = None) -> MovimientoCaja:
        if self._movimientos is None:
            raise RuntimeError("ServicioCaja sin repositorio de movimientos")
        sesion = self._sesiones.abierta()
        if sesion is None:
            raise CajaNoAbierta("no hay una sesion de caja abierta")
        movimiento = MovimientoCaja(caja_sesion_id=sesion.id, tipo=tipo, monto=monto,
                                    motivo=motivo, fecha=fecha, usuario_id=usuario_id)
        if tipo == "egreso":
            disponible = self._arqueo(sesion, CERO).esperado
            if monto > disponible:
                raise EfectivoInsuficiente(
                    f"el egreso ({monto}) supera el efectivo esperado en caja ({disponible})")
        return self._movimientos.registrar(movimiento)

    def arqueo(self, sesion_id: int, monto_contado: Decimal) -> Arqueo:
        sesion = self._sesiones.por_id(sesion_id)
        if sesion is None:
            raise CajaNoEncontrada(f"sesion de caja inexistente: {sesion_id}")
        if sesion.estado != "abierta":
            raise CajaNoAbierta(f"la sesion {sesion_id} no esta abierta")
        return self._arqueo(sesion, monto_contado)

    def cerrar(self, *, sesion_id: int, fecha: datetime,
               monto_contado: Decimal) -> tuple[CajaSesion, Arqueo]:
        sesion = self._sesiones.por_id(sesion_id)
        if sesion is None:
            raise CajaNoEncontrada(f"sesion de caja inexistente: {sesion_id}")
        if sesion.estado != "abierta":
            raise CajaNoAbierta(f"la sesion {sesion_id} no esta abierta")
        arqueo = self._arqueo(sesion, monto_contado)
        cerrada = self._sesiones.cerrar(replace(
            sesion, cierre_fecha=fecha, monto_contado=monto_contado, estado="cerrada"))
        return cerrada, arqueo
