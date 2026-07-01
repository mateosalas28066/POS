# tests/core/test_servicio_venta_promocion.py
from datetime import datetime
from decimal import Decimal

from core.entidades import Impuesto, Producto, Promocion
from core.servicio_venta import ServicioVenta

AHORA = datetime(2026, 7, 1, 12, 0)


class FakeProductos:
    def __init__(self, productos):
        self._por_codigo = {p.codigo_barras: p for p in productos}

    def por_codigo(self, codigo):
        return self._por_codigo.get(codigo)


class FakeImpuestos:
    def __init__(self, impuestos):
        self._por_id = {i.id: i for i in impuestos}

    def por_id(self, id):
        return self._por_id.get(id)


class FakePromos:
    def __init__(self, promo=None):
        self._promo = promo

    def activa_por_producto(self, producto_id):
        return self._promo if self._promo and self._promo.producto_id == producto_id else None


def _servicio(promo=None):
    lomo = Producto(codigo_barras="1", nombre="Lomo", precio=Decimal("20000"),
                    vendido_por_peso=True, unidad="kg", impuesto_id=1, id=1)
    iva = Impuesto(nombre="IVA 0%", tarifa=Decimal("0"), id=1)
    return ServicioVenta(FakeProductos([lomo]), FakeImpuestos([iva]), FakePromos(promo))


def _promo(**kw):
    base = dict(producto_id=1, tipo_valor="precio_fijo", valor=Decimal("15000"),
                tipo_duracion="manual", id=1)
    base.update(kw)
    return Promocion(**base)


def test_promo_fija_baja_el_precio_de_la_linea():
    s = _servicio(_promo())
    linea = s.agregar("1", peso_kg=Decimal("2"), ahora=AHORA)
    assert linea.subtotal == Decimal("30000")  # 15000 * 2
    assert linea.promocion_id == 1


def test_sin_promo_precio_normal():
    s = _servicio(None)
    linea = s.agregar("1", peso_kg=Decimal("2"), ahora=AHORA)
    assert linea.subtotal == Decimal("40000")
    assert linea.promocion_id is None


def test_promo_no_vigente_no_aplica():
    vencida = _promo(tipo_duracion="tiempo",
                     desde=datetime(2026, 6, 1), hasta=datetime(2026, 6, 30))
    s = _servicio(vencida)
    linea = s.agregar("1", peso_kg=Decimal("2"), ahora=AHORA)
    assert linea.subtotal == Decimal("40000")
    assert linea.promocion_id is None


def test_promo_se_acumula_con_descuento_de_cliente():
    s = _servicio(_promo())            # precio promo 15000/kg
    s.establecer_descuento(Decimal("0.1"))
    linea = s.agregar("1", peso_kg=Decimal("2"), ahora=AHORA)
    # 15000*2 = 30000 → descuento 10% → 27000
    assert linea.subtotal == Decimal("27000")


def test_promo_porcentaje_recalcula_iva_incluido():
    lomo = Producto(codigo_barras="1", nombre="Lomo", precio=Decimal("2500"),
                    impuesto_id=1, id=1)
    iva = Impuesto(nombre="IVA 19%", tarifa=Decimal("0.19"), id=1)
    s = ServicioVenta(FakeProductos([lomo]), FakeImpuestos([iva]),
                      FakePromos(_promo(tipo_valor="porcentaje", valor=Decimal("0.2"))))
    linea = s.agregar("1", cantidad=2, ahora=AHORA)
    # precio 2500*0.8=2000; subtotal 4000; IVA incluido round(4000*0.19/1.19)=639
    assert linea.subtotal == Decimal("4000")
    assert linea.impuesto == Decimal("639")


def test_gs1_con_importe_embebido_ignora_promo():
    s = _servicio(_promo())
    linea = s.agregar("1", peso_kg=Decimal("2"), importe=Decimal("40000"), ahora=AHORA)
    assert linea.subtotal == Decimal("40000")  # el importe manda
    assert linea.promocion_id is None
