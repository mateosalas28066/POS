# tests/core/test_registro_venta_promocion.py
from dataclasses import replace
from datetime import datetime
from decimal import Decimal

from core.entidades import LineaVenta, Pago, Promocion, Venta
from core.servicio_venta import ServicioRegistroVenta


class _FakeVentas:
    def guardar(self, venta, pagos):
        return replace(venta, id=77)


class _FakeInventario:
    def registrar(self, m):
        return m


class _FakePromos:
    def __init__(self, promo):
        self.items = {promo.id: promo}

    def por_id(self, id):
        return self.items.get(id)

    def actualizar(self, promo):
        self.items[promo.id] = promo


def _venta_con_promo(promocion_id):
    linea = LineaVenta(producto_id=1, descripcion="Lomo", cantidad_o_peso=Decimal("2"),
                       precio_unit=Decimal("15000"), impuesto=Decimal("0"),
                       subtotal=Decimal("30000"), promocion_id=promocion_id)
    return Venta(fecha=datetime(2026, 7, 1, 10, 0), lineas=(linea,),
                 total=Decimal("30000"), total_impuestos=Decimal("0"))


def test_registrar_consume_unidades_de_la_promo():
    promo = Promocion(producto_id=1, tipo_valor="precio_fijo", valor=Decimal("15000"),
                      tipo_duracion="unidades", unidades_limite=Decimal("5"), id=9)
    promos = _FakePromos(promo)
    svc = ServicioRegistroVenta(_FakeVentas(), _FakeInventario(), promos)
    svc.registrar(_venta_con_promo(9), [Pago(medio_pago_id=1, monto=Decimal("30000"))])
    assert promos.por_id(9).unidades_restantes == Decimal("3")


def test_registrar_sin_promo_no_falla():
    svc = ServicioRegistroVenta(_FakeVentas(), _FakeInventario())
    guardada = svc.registrar(_venta_con_promo(None),
                             [Pago(medio_pago_id=1, monto=Decimal("30000"))])
    assert guardada.id == 77
