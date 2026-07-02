"""Servicio de cuentas por cobrar (fiado). Python puro: solo conoce puertos."""
from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from core.entidades import AbonoCliente
from core.puertos import RepositorioCuentasCobrar, RepositorioVentas
from core.servicio_caja import ServicioCaja

CERO = Decimal("0")


class ServicioCuentasCobrar:
    def __init__(self, cuentas: RepositorioCuentasCobrar, ventas: RepositorioVentas,
                 caja: ServicioCaja, *, medio_fiado_id: int = 4,
                 efectivo_medio_pago_id: int = 1) -> None:
        self._cuentas = cuentas
        self._ventas = ventas
        self._caja = caja
        self._medio_fiado_id = medio_fiado_id
        self._efectivo_id = efectivo_medio_pago_id

    def saldo(self, cliente_id: int) -> Decimal:
        fiado = self._ventas.fiado_por_cliente(self._medio_fiado_id).get(cliente_id, CERO)
        abonos = self._cuentas.abonos_por_cliente().get(cliente_id, CERO)
        return fiado - abonos

    def pendientes(self) -> dict[int, Decimal]:
        fiado = self._ventas.fiado_por_cliente(self._medio_fiado_id)
        abonos = self._cuentas.abonos_por_cliente()
        saldos: dict[int, Decimal] = {}
        for cid in set(fiado) | set(abonos):
            s = fiado.get(cid, CERO) - abonos.get(cid, CERO)
            if s > CERO:
                saldos[cid] = s
        return saldos

    def abonar(self, *, cliente_id: int, monto: Decimal, medio_pago_id: int,
               fecha: datetime, usuario_id: int | None = None) -> AbonoCliente:
        """Registra un abono. Si es en efectivo, primero lo mete a caja como ingreso
        (exige caja abierta vía ServicioCaja; si no, propaga CajaNoAbierta)."""
        caja_sesion_id = None
        if medio_pago_id == self._efectivo_id:
            mov = self._caja.registrar_movimiento(
                tipo="ingreso", monto=monto, motivo=f"Abono cliente {cliente_id}",
                fecha=fecha, usuario_id=usuario_id)
            caja_sesion_id = mov.caja_sesion_id
        return self._cuentas.guardar(AbonoCliente(
            cliente_id=cliente_id, monto=monto, fecha=fecha, medio_pago_id=medio_pago_id,
            caja_sesion_id=caja_sesion_id, usuario_id=usuario_id))
