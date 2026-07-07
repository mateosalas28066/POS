from datetime import datetime
from decimal import Decimal

import pytest

from core.entidades import LineaVenta, Pago, Venta
from core.servicio_venta import ServicioRegistroVentaConOutbox
from sync_pdv.outbox import serializar_venta


class _RegistroFake:
    def registrar(self, venta, pagos):
        return venta  # devuelve la misma venta como "guardada"


class _OutboxFake:
    def __init__(self):
        self.eventos = []

    def encolar(self, ev):
        self.eventos.append(ev)


@pytest.fixture()
def venta_min():
    return Venta(
        fecha=datetime(2026, 7, 6, 10, 0, 0),
        lineas=(LineaVenta(producto_id=1, descripcion="Lomo",
                           cantidad_o_peso=Decimal("2"), precio_unit=Decimal("50"),
                           impuesto=Decimal("0"), subtotal=Decimal("100")),),
        total=Decimal("100"), total_impuestos=Decimal("0"), usuario_id=3, id=5)


@pytest.fixture()
def pagos_min():
    return [Pago(medio_pago_id=1, monto=Decimal("100"), venta_id=5)]


def test_registrar_encola_evento_venta(venta_min, pagos_min):
    outbox = _OutboxFake()
    svc = ServicioRegistroVentaConOutbox(_RegistroFake(), outbox, almacen_id=7,
                                         local_id="local-01", serializar=serializar_venta)
    svc.registrar(venta_min, pagos_min)
    assert len(outbox.eventos) == 1
    assert outbox.eventos[0].tipo == "venta"
    assert outbox.eventos[0].payload["almacen_id"] == 7


def test_registrar_devuelve_la_venta_guardada(venta_min, pagos_min):
    svc = ServicioRegistroVentaConOutbox(_RegistroFake(), _OutboxFake(), almacen_id=7,
                                         local_id="local-01", serializar=serializar_venta)
    assert svc.registrar(venta_min, pagos_min) is venta_min
