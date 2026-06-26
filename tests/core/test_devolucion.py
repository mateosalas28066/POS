from datetime import datetime
from decimal import Decimal

import pytest

from core.entidades import Devolucion, ItemDevolucion, LineaVenta, Pago, Venta
from core.servicio_venta import (
    CantidadDevueltaExcede, LineaNoEncontrada,
    construir_lineas_devolucion, entradas_de_devolucion,
)


def _venta() -> Venta:
    lineas = (
        LineaVenta(producto_id=1, descripcion="Gaseosa", cantidad_o_peso=Decimal("2"),
                   precio_unit=Decimal("3500"), impuesto=Decimal("1118"),
                   subtotal=Decimal("7000"), venta_id=77, id=10),
        LineaVenta(producto_id=2, descripcion="Manzana", cantidad_o_peso=Decimal("1.5"),
                   precio_unit=Decimal("4000"), impuesto=Decimal("0"),
                   subtotal=Decimal("6000"), venta_id=77, id=20),
    )
    return Venta(fecha=datetime(2026, 6, 25, 10, 0), lineas=lineas,
                 total=Decimal("13000"), total_impuestos=Decimal("1118"), id=77)


def test_devolver_linea_completa_da_valores_exactos():
    lineas = construir_lineas_devolucion(
        _venta(), [ItemDevolucion(venta_linea_id=10, cantidad_o_peso=Decimal("2"))], {})
    assert len(lineas) == 1
    assert lineas[0].producto_id == 1
    assert lineas[0].cantidad_o_peso == Decimal("2")
    assert lineas[0].subtotal == Decimal("7000")   # ratio 1 -> exacto
    assert lineas[0].impuesto == Decimal("1118")
    assert lineas[0].venta_linea_id == 10


def test_devolver_parcial_prorratea_subtotal_e_impuesto():
    lineas = construir_lineas_devolucion(
        _venta(), [ItemDevolucion(venta_linea_id=10, cantidad_o_peso=Decimal("1"))], {})
    assert lineas[0].subtotal == Decimal("3500")    # 7000 * 1/2
    assert lineas[0].impuesto == Decimal("559")     # 1118 * 1/2


def test_devolver_mas_que_lo_vendido_falla():
    with pytest.raises(CantidadDevueltaExcede):
        construir_lineas_devolucion(
            _venta(), [ItemDevolucion(venta_linea_id=10, cantidad_o_peso=Decimal("3"))], {})


def test_devolver_respeta_lo_ya_devuelto():
    # ya se devolvió 1 de 2; pedir 2 más excede el remanente (1)
    with pytest.raises(CantidadDevueltaExcede):
        construir_lineas_devolucion(
            _venta(), [ItemDevolucion(venta_linea_id=10, cantidad_o_peso=Decimal("2"))],
            {10: Decimal("1")})


def test_devolver_linea_inexistente_falla():
    with pytest.raises(LineaNoEncontrada):
        construir_lineas_devolucion(
            _venta(), [ItemDevolucion(venta_linea_id=999, cantidad_o_peso=Decimal("1"))], {})


def test_entradas_de_devolucion_una_por_linea_con_ref():
    dev = Devolucion(
        venta_id=77, fecha=datetime(2026, 6, 25, 11, 0),
        lineas=tuple(construir_lineas_devolucion(
            _venta(),
            [ItemDevolucion(venta_linea_id=10, cantidad_o_peso=Decimal("2")),
             ItemDevolucion(venta_linea_id=20, cantidad_o_peso=Decimal("1.5"))], {})),
        total=Decimal("13000"), total_impuestos=Decimal("1118"),
        reembolsos=(Pago(medio_pago_id=1, monto=Decimal("13000")),), id=5)
    entradas = entradas_de_devolucion(dev)
    assert [m.tipo for m in entradas] == ["entrada", "entrada"]
    assert [m.cantidad for m in entradas] == [Decimal("2"), Decimal("1.5")]
    assert all(m.ref == "devolucion:5" for m in entradas)
