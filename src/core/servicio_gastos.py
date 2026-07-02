"""Servicio de gastos. Python puro: solo conoce puertos."""
from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from core.entidades import CategoriaGasto, Gasto
from core.puertos import RepositorioCategoriasGasto, RepositorioGastos
from core.servicio_caja import ServicioCaja

CERO = Decimal("0")


class ServicioGastos:
    def __init__(self, gastos: RepositorioGastos, categorias: RepositorioCategoriasGasto,
                 caja: ServicioCaja, *, efectivo_medio_pago_id: int = 1) -> None:
        self._gastos = gastos
        self._categorias = categorias
        self._caja = caja
        self._efectivo_id = efectivo_medio_pago_id

    def registrar(self, *, categoria_gasto_id: int, monto: Decimal, medio_pago_id: int,
                  fecha: datetime, descripcion: str | None = None,
                  usuario_id: int | None = None) -> Gasto:
        """Registra un gasto. Si es en efectivo, lo saca de caja como egreso (exige caja
        abierta vía ServicioCaja; si no, propaga CajaNoAbierta)."""
        caja_sesion_id = None
        if medio_pago_id == self._efectivo_id:
            mov = self._caja.registrar_movimiento(
                tipo="egreso", monto=monto,
                motivo=f"Gasto {descripcion or categoria_gasto_id}",
                fecha=fecha, usuario_id=usuario_id)
            caja_sesion_id = mov.caja_sesion_id
        return self._gastos.guardar(Gasto(
            fecha=fecha, categoria_gasto_id=categoria_gasto_id, monto=monto,
            descripcion=descripcion, medio_pago_id=medio_pago_id,
            caja_sesion_id=caja_sesion_id, usuario_id=usuario_id))

    def listar(self, desde: datetime, hasta: datetime) -> list[Gasto]:
        return self._gastos.gastos_en(desde, hasta)

    # Gestión de categorías (lista fija administrable, decisión 4)
    def listar_categorias(self) -> list[CategoriaGasto]:
        return self._categorias.listar()

    def crear_categoria(self, nombre: str) -> CategoriaGasto:
        return self._categorias.guardar(CategoriaGasto(nombre=nombre))

    def actualizar_categoria(self, categoria: CategoriaGasto) -> CategoriaGasto:
        return self._categorias.actualizar(categoria)
