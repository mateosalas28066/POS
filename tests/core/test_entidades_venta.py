from datetime import datetime
from decimal import Decimal

import pytest

from core.entidades import Cliente, LineaVenta, MedioPago, Pago, Venta


def _linea() -> LineaVenta:
    return LineaVenta(producto_id=1, descripcion="Gaseosa", cantidad_o_peso=Decimal("2"),
                      precio_unit=Decimal("3500"), impuesto=Decimal("1118"),
                      subtotal=Decimal("7000"))


def test_medio_pago_minimo():
    assert MedioPago(nombre="Efectivo").nombre == "Efectivo"


def test_cliente_reserva_campos_dian():
    c = Cliente(identificacion="900123", nombre="ACME")
    assert c.bloqueado_edicion is False
    assert c.tipo_documento is None and c.regimen is None


def test_pago_monto_no_positivo_falla():
    with pytest.raises(ValueError):
        Pago(medio_pago_id=1, monto=Decimal("0"))


def test_linea_venta_se_construye():
    assert _linea().subtotal == Decimal("7000")


def test_venta_valida_se_construye():
    v = Venta(fecha=datetime(2026, 6, 25), lineas=(_linea(),),
              total=Decimal("7000"), total_impuestos=Decimal("1118"))
    assert v.estado == "pagada"
    assert v.id is None


def test_venta_estado_invalido_falla():
    with pytest.raises(ValueError):
        Venta(fecha=datetime(2026, 6, 25), lineas=(_linea(),),
              total=Decimal("7000"), total_impuestos=Decimal("1118"), estado="regalo")
