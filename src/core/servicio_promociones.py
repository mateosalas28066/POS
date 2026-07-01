"""Servicio de gestión de promociones. Python puro: solo conoce el puerto."""
from __future__ import annotations

from dataclasses import replace

from core.entidades import Promocion
from core.puertos import RepositorioPromociones


class PromocionActivaExiste(ValueError):
    pass


class PromocionNoEncontrada(ValueError):
    pass


class ServicioPromociones:
    def __init__(self, promociones: RepositorioPromociones) -> None:
        self._promociones = promociones

    def crear(self, promo: Promocion) -> Promocion:
        if promo.activa and self._promociones.activa_por_producto(promo.producto_id) is not None:
            raise PromocionActivaExiste(
                f"el producto {promo.producto_id} ya tiene una promoción activa")
        return self._promociones.guardar(promo)

    def activar(self, promocion_id: int) -> None:
        self._set_activa(promocion_id, True)

    def desactivar(self, promocion_id: int) -> None:
        self._set_activa(promocion_id, False)

    def _set_activa(self, promocion_id: int, activa: bool) -> None:
        promo = self._promociones.por_id(promocion_id)
        if promo is None:
            raise PromocionNoEncontrada(f"promoción inexistente: {promocion_id}")
        self._promociones.actualizar(replace(promo, activa=activa))

    def listar(self) -> list[Promocion]:
        return self._promociones.listar()
