# tests/core/test_servicio_venta.py
from datetime import datetime
from decimal import Decimal

import pytest

from core.entidades import Impuesto, Producto
from core.perifericos.gs1 import FormatoGS1
from core.servicio_venta import ProductoNoEncontrado, PesoRequerido, ServicioVenta


class _FakeProductos:
    def __init__(self, *productos: Producto) -> None:
        self._por_codigo = {p.codigo_barras: p for p in productos}

    def por_codigo(self, codigo_barras: str):
        return self._por_codigo.get(codigo_barras)


class _FakeImpuestos:
    def __init__(self, *impuestos: Impuesto) -> None:
        self._por_id = {i.id: i for i in impuestos}

    def por_id(self, id: int):
        return self._por_id.get(id)


IVA = Impuesto(nombre="IVA", tarifa=Decimal("0.19"), id=10)
EXCLUIDO = Impuesto(nombre="Excluido", tarifa=Decimal("0"), id=20)
GASEOSA = Producto(codigo_barras="B", nombre="Gaseosa", precio=Decimal("3500"),
                   impuesto_id=10, id=1)
MANZANA = Producto(codigo_barras="A", nombre="Manzana", precio=Decimal("4000"),
                   vendido_por_peso=True, unidad="kg", impuesto_id=20, id=2)
# PLU de balanza: codigo_barras de 5 dígitos que coincide con el embebido en la etiqueta GS1
PESAJE = Producto(codigo_barras="01234", nombre="Carne", precio=Decimal("4000"),
                  vendido_por_peso=True, unidad="kg", impuesto_id=20, id=3)


def _servicio() -> ServicioVenta:
    return ServicioVenta(_FakeProductos(GASEOSA, MANZANA, PESAJE),
                         _FakeImpuestos(IVA, EXCLUIDO))


def test_agregar_por_unidad_calcula_subtotal_e_iva_contenido():
    s = _servicio()
    linea = s.agregar("B", cantidad=2)
    assert linea.subtotal == Decimal("7000")
    assert linea.impuesto == Decimal("1118")
    assert linea.descripcion == "Gaseosa"
    assert s.total == Decimal("7000")
    assert s.total_impuestos == Decimal("1118")


def test_agregar_por_peso_usa_precio_por_kg():
    s = _servicio()
    linea = s.agregar("A", peso_kg=Decimal("1.5"))
    assert linea.subtotal == Decimal("6000")
    assert linea.impuesto == Decimal("0")  # excluido
    assert linea.cantidad_o_peso == Decimal("1.5")


def test_producto_por_peso_sin_peso_falla():
    with pytest.raises(PesoRequerido):
        _servicio().agregar("A")


def test_codigo_inexistente_falla():
    with pytest.raises(ProductoNoEncontrado):
        _servicio().agregar("ZZZ")


def test_confirmar_vacio_falla():
    with pytest.raises(ValueError):
        _servicio().confirmar(fecha=datetime(2026, 6, 25))


def test_confirmar_arma_venta_con_totales():
    s = _servicio()
    s.agregar("B", cantidad=2)
    s.agregar("A", peso_kg=Decimal("1.5"))
    venta = s.confirmar(fecha=datetime(2026, 6, 25))
    assert venta.estado == "pagada"
    assert len(venta.lineas) == 2
    assert venta.total == Decimal("13000")
    assert venta.total_impuestos == Decimal("1118")


def test_agregar_por_peso_con_importe_usa_importe_como_subtotal():
    s = _servicio()
    linea = s.agregar("01234", peso_kg=Decimal("1.234"), importe=Decimal("1234"))
    assert linea.subtotal == Decimal("1234")          # usa el importe, no precio×peso
    assert linea.cantidad_o_peso == Decimal("1.234")  # el peso sigue rigiendo el inventario


def test_agregar_escaneado_peso_variable_agrega_por_peso():
    s = _servicio()
    linea = s.agregar_escaneado("2012340012344")  # codigo 01234, 1.234 kg
    assert linea.cantidad_o_peso == Decimal("1.234")
    assert linea.subtotal == Decimal("4936")  # 4000 * 1.234


def test_agregar_escaneado_codigo_normal_agrega_unidad():
    s = _servicio()
    linea = s.agregar_escaneado("B")  # Gaseosa: no es peso variable
    assert linea.cantidad_o_peso == Decimal("1")
    assert linea.subtotal == Decimal("3500")


def test_agregar_escaneado_precio_embebido_usa_importe():
    carne = Producto(codigo_barras="01234", nombre="Carne", precio=Decimal("2000"),
                     vendido_por_peso=True, unidad="kg", impuesto_id=20, id=3)
    s = ServicioVenta(_FakeProductos(carne), _FakeImpuestos(EXCLUIDO))
    linea = s.agregar_escaneado("2012340012344", FormatoGS1(valor_es_precio=True))
    assert linea.subtotal == Decimal("1234")           # importe embebido (valor crudo)
    assert linea.cantidad_o_peso == Decimal("0.617")   # 1234 / 2000


def test_agregar_escaneado_producto_inexistente_falla():
    s = ServicioVenta(_FakeProductos(), _FakeImpuestos(EXCLUIDO))
    with pytest.raises(ProductoNoEncontrado):
        s.agregar_escaneado("2012340012344")


def test_agregar_escaneado_digito_control_invalido_falla():
    s = _servicio()
    with pytest.raises(ValueError):
        s.agregar_escaneado("2012340012340")  # último dígito correcto sería 4, no 0
