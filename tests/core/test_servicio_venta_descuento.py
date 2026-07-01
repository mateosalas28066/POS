from datetime import datetime
from decimal import Decimal

import pytest

from core.entidades import Impuesto, Producto
from core.servicio_venta import ServicioVenta


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


def _servicio():
    arroz = Producto(codigo_barras="7700006", nombre="Arroz", precio=Decimal("2500"),
                     impuesto_id=1, id=1)
    iva = Impuesto(nombre="IVA 19%", tarifa=Decimal("0.19"), id=1)
    return ServicioVenta(FakeProductos([arroz]), FakeImpuestos([iva]))


def test_sin_descuento_subtotal_bruto():
    s = _servicio()
    linea = s.agregar("7700006", cantidad=2)
    assert linea.subtotal == Decimal("5000")


def test_descuento_aplica_por_linea():
    s = _servicio()
    s.establecer_descuento(Decimal("0.1"))
    linea = s.agregar("7700006", cantidad=2)
    assert linea.subtotal == Decimal("4500")  # round(5000 * 0.9)


def test_descuento_recalcula_iva_incluido():
    s = _servicio()
    s.establecer_descuento(Decimal("0.1"))
    linea = s.agregar("7700006", cantidad=2)
    # IVA contenido en 4500 al 19%: round(4500 * 0.19 / 1.19) = 718 (718.487... → ROUND_HALF_UP)
    assert linea.impuesto == Decimal("718")


def test_establecer_descuento_recomputa_lineas_existentes():
    s = _servicio()
    s.agregar("7700006", cantidad=2)
    s.establecer_descuento(Decimal("0.1"))
    assert s.total == Decimal("4500")


def test_confirmar_incluye_descuento_pct():
    s = _servicio()
    s.establecer_descuento(Decimal("0.1"))
    s.agregar("7700006", cantidad=1)
    venta = s.confirmar(fecha=datetime.now())
    assert venta.descuento_pct == Decimal("0.1")


def test_establecer_descuento_rechaza_fuera_de_rango():
    s = _servicio()
    with pytest.raises(ValueError):
        s.establecer_descuento(Decimal("1"))
