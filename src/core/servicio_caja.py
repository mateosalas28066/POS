from __future__ import annotations
from dataclasses import replace
from datetime import datetime
from decimal import Decimal
from core.calculos import calcular_arqueo
from core.entidades import Arqueo, CajaSesion
from core.puertos import RepositorioCajaSesiones, RepositorioVentas

CERO = Decimal("0")

class CajaYaAbierta(RuntimeError):
    pass

class CajaNoEncontrada(ValueError):
    pass

class CajaNoAbierta(ValueError):
    pass

class ServicioCaja:
    def __init__(self, sesiones: RepositorioCajaSesiones, ventas: RepositorioVentas,
                 efectivo_medio_pago_id: int = 1) -> None:
        self._sesiones = sesiones
        self._ventas = ventas
        self._efectivo_id = efectivo_medio_pago_id

    def abrir(self, *, fecha: datetime, monto_inicial: Decimal,
              usuario_id: int | None = None) -> CajaSesion:
        if self._sesiones.abierta() is not None:
            raise CajaYaAbierta("ya existe una sesion de caja abierta")
        return self._sesiones.abrir(CajaSesion(
            apertura_fecha=fecha, monto_inicial=monto_inicial, usuario_id=usuario_id))

    def _arqueo(self, sesion: CajaSesion, monto_contado: Decimal) -> Arqueo:
        totales = self._ventas.totales_por_medio(sesion.id)
        return calcular_arqueo(sesion.monto_inicial, totales.get(self._efectivo_id, CERO),
                               monto_contado)

    def arqueo(self, sesion_id: int, monto_contado: Decimal) -> Arqueo:
        sesion = self._sesiones.por_id(sesion_id)
        if sesion is None:
            raise CajaNoEncontrada(f"sesion de caja inexistente: {sesion_id}")
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
