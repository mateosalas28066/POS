from dataclasses import replace
from decimal import Decimal

import pytest

from core.entidades import Promocion
from core.servicio_promociones import PromocionActivaExiste, ServicioPromociones


class FakePromos:
    def __init__(self):
        self.items = {}
        self._next = 1

    def guardar(self, promo):
        pid = self._next
        self._next += 1
        guardada = replace(promo, id=pid)
        self.items[pid] = guardada
        return guardada

    def actualizar(self, promo):
        self.items[promo.id] = promo

    def por_id(self, id):
        return self.items.get(id)

    def activa_por_producto(self, producto_id):
        for p in self.items.values():
            if p.producto_id == producto_id and p.activa:
                return p
        return None

    def listar(self):
        return list(self.items.values())


def _promo(**kw):
    base = dict(producto_id=1, tipo_valor="precio_fijo", valor=Decimal("8000"),
                tipo_duracion="manual")
    base.update(kw)
    return Promocion(**base)


def test_crear_guarda_y_devuelve_con_id():
    svc = ServicioPromociones(FakePromos())
    guardada = svc.crear(_promo())
    assert guardada.id == 1


def test_crear_rechaza_segunda_promo_activa_del_mismo_producto():
    svc = ServicioPromociones(FakePromos())
    svc.crear(_promo())
    with pytest.raises(PromocionActivaExiste):
        svc.crear(_promo(valor=Decimal("7000")))


def test_desactivar_libera_el_producto():
    repo = FakePromos()
    svc = ServicioPromociones(repo)
    p = svc.crear(_promo())
    svc.desactivar(p.id)
    assert repo.por_id(p.id).activa is False
    svc.crear(_promo(valor=Decimal("7000")))  # ya no colisiona


def test_activar_vuelve_a_marcar_activa():
    repo = FakePromos()
    svc = ServicioPromociones(repo)
    p = svc.crear(_promo())
    svc.desactivar(p.id)
    svc.activar(p.id)
    assert repo.por_id(p.id).activa is True
