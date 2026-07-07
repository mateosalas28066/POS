from datetime import datetime
from decimal import Decimal

from core.entidades import LineaVenta, Pago, Venta
from inventario.db import aplicar_migraciones, conectar
from sync_pdv.outbox import EventoSync, RepositorioOutboxSQLite, serializar_venta


def _conn():
    c = conectar(":memory:")
    aplicar_migraciones(c)
    return c


def test_encolar_y_listar_pendientes():
    repo = RepositorioOutboxSQLite(_conn())
    ev = EventoSync(uuid="u1", local_id="local-01", tipo="venta",
                    payload={"total": "100"}, creado_en="2026-07-06T10:00:00")
    repo.encolar(ev)
    pend = repo.pendientes()
    assert [e.uuid for e in pend] == ["u1"]
    assert pend[0].payload["total"] == "100"


def test_marcar_enviados_saca_de_pendientes():
    repo = RepositorioOutboxSQLite(_conn())
    repo.encolar(EventoSync("u1", "local-01", "venta", {}, "2026-07-06T10:00:00"))
    repo.marcar_enviados(["u1"])
    assert repo.pendientes() == []


def test_serializar_venta_dinero_como_strings():
    venta = Venta(
        fecha=datetime(2026, 7, 6, 10, 0, 0),
        lineas=(LineaVenta(producto_id=1, descripcion="Lomo",
                           cantidad_o_peso=Decimal("2"), precio_unit=Decimal("50"),
                           impuesto=Decimal("0"), subtotal=Decimal("100")),),
        total=Decimal("100"), total_impuestos=Decimal("0"),
        usuario_id=3, id=5)
    pagos = [Pago(medio_pago_id=1, monto=Decimal("100"), venta_id=5)]
    ev = serializar_venta(venta, pagos, almacen_id=7, local_id="local-01")
    assert ev.tipo == "venta"
    assert ev.payload["almacen_id"] == 7
    assert ev.payload["total"] == str(venta.total)         # string, no float
    assert ev.payload["fecha"] == "2026-07-06T10:00:00"
    assert ev.payload["lineas"][0]["cantidad"] == "2"
    assert ev.payload["pagos"][0]["monto"] == "100"
