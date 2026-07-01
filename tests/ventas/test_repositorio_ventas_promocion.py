from datetime import datetime
from decimal import Decimal

import pytest

from core.entidades import LineaVenta, Pago, Venta
from inventario.db import aplicar_migraciones, conectar
from ventas.repositorio_sqlite import RepositorioVentasSQLite


@pytest.fixture
def conn():
    c = conectar()
    aplicar_migraciones(c)
    c.execute("INSERT INTO productos (codigo_barras, nombre, precio, costo, "
              "vendido_por_peso, unidad) VALUES ('1','Lomo','20000','0',1,'kg')")
    c.execute("INSERT INTO promociones (producto_id, tipo_valor, valor, tipo_duracion, activa) "
              "VALUES (1,'precio_fijo','15000','manual',1)")
    c.commit()
    yield c
    c.close()


def _venta(promocion_id):
    linea = LineaVenta(producto_id=1, descripcion="Lomo", cantidad_o_peso=Decimal("2"),
                       precio_unit=Decimal("15000"), impuesto=Decimal("0"),
                       subtotal=Decimal("30000"), promocion_id=promocion_id)
    return Venta(fecha=datetime(2026, 7, 1, 10, 0), lineas=(linea,),
                 total=Decimal("30000"), total_impuestos=Decimal("0"))


def test_guardar_y_leer_promocion_id(conn):
    repo = RepositorioVentasSQLite(conn)
    guardada = repo.guardar(_venta(1), [Pago(medio_pago_id=1, monto=Decimal("30000"))])
    leida = repo.por_id(guardada.id)
    assert leida.lineas[0].promocion_id == 1


def test_linea_sin_promo_queda_none(conn):
    repo = RepositorioVentasSQLite(conn)
    guardada = repo.guardar(_venta(None), [Pago(medio_pago_id=1, monto=Decimal("30000"))])
    assert repo.por_id(guardada.id).lineas[0].promocion_id is None
