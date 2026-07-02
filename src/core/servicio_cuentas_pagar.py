"""Servicio de cuentas por pagar (proveedores). Python puro: solo conoce puertos."""
from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from core.entidades import PagoProveedor
from core.puertos import RepositorioCompras, RepositorioCuentasPagar
from core.servicio_caja import ServicioCaja

CERO = Decimal("0")


class ServicioCuentasPagar:
    def __init__(self, cuentas: RepositorioCuentasPagar, compras: RepositorioCompras,
                 caja: ServicioCaja, *, efectivo_medio_pago_id: int = 1) -> None:
        self._cuentas = cuentas
        self._compras = compras
        self._caja = caja
        self._efectivo_id = efectivo_medio_pago_id

    def saldo(self, proveedor_id: int) -> Decimal:
        credito = self._compras.credito_por_proveedor().get(proveedor_id, CERO)
        pagos = self._cuentas.pagos_por_proveedor().get(proveedor_id, CERO)
        return credito - pagos

    def pendientes(self) -> dict[int, Decimal]:
        credito = self._compras.credito_por_proveedor()
        pagos = self._cuentas.pagos_por_proveedor()
        saldos: dict[int, Decimal] = {}
        for pid in set(credito) | set(pagos):
            s = credito.get(pid, CERO) - pagos.get(pid, CERO)
            if s > CERO:
                saldos[pid] = s
        return saldos

    def pagar(self, *, proveedor_id: int, monto: Decimal, medio_pago_id: int,
              fecha: datetime, usuario_id: int | None = None) -> PagoProveedor:
        """Registra un pago a proveedor. Si es en efectivo, lo saca de caja como egreso
        (exige caja abierta vía ServicioCaja; si no, propaga CajaNoAbierta)."""
        caja_sesion_id = None
        if medio_pago_id == self._efectivo_id:
            mov = self._caja.registrar_movimiento(
                tipo="egreso", monto=monto, motivo=f"Pago proveedor {proveedor_id}",
                fecha=fecha, usuario_id=usuario_id)
            caja_sesion_id = mov.caja_sesion_id
        return self._cuentas.guardar(PagoProveedor(
            proveedor_id=proveedor_id, monto=monto, fecha=fecha, medio_pago_id=medio_pago_id,
            caja_sesion_id=caja_sesion_id, usuario_id=usuario_id))
