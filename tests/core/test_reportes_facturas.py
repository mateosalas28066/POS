from datetime import datetime
from decimal import Decimal

from core.entidades import LineaVenta, Venta
from core.servicio_reportes import ServicioReportes

DESDE = datetime(2026, 6, 25, 0, 0)
HASTA = datetime(2026, 6, 26, 0, 0)


def _venta(id, hora, estado="pagada"):
    total = Decimal("1000")
    linea = LineaVenta(producto_id=1, descripcion="X", cantidad_o_peso=Decimal("1"),
                       precio_unit=total, impuesto=Decimal("0"), subtotal=total,
                       venta_id=id, id=id)
    return Venta(fecha=datetime(2026, 6, 25, hora, 0), lineas=(linea,), total=total,
                 total_impuestos=Decimal("0"), estado=estado, id=id)


class _FakeVentas:
    def __init__(self, ventas):
        self._ventas = ventas
    def ventas_en(self, desde, hasta):
        return list(self._ventas)


class _FakeDevoluciones:
    def devoluciones_en(self, desde, hasta):
        return []


def test_facturas_delega_en_ventas_en_y_ordena_por_fecha():
    ventas = [_venta(2, 11), _venta(1, 10, estado="devuelta_parcial")]
    svc = ServicioReportes(_FakeVentas(ventas), _FakeDevoluciones(), None, None)
    r = svc.facturas(DESDE, HASTA)
    assert [v.id for v in r] == [1, 2]
    assert r[0].estado == "devuelta_parcial"          # no filtra por estado (solo ordena)
    assert isinstance(r, tuple)
