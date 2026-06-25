from datetime import datetime
from decimal import Decimal

from core.entidades import (
    Categoria, Cliente, Impuesto, LineaVenta, Pago, Producto, Venta,
)
from inventario.repositorio_sqlite import (
    RepositorioCategoriasSQLite,
    RepositorioImpuestosSQLite,
    RepositorioProductosSQLite,
)
from ventas.repositorio_sqlite import (
    RepositorioClientesSQLite,
    RepositorioMediosPagoSQLite,
    RepositorioVentasSQLite,
)


def _producto(conn) -> Producto:
    cat = RepositorioCategoriasSQLite(conn).guardar(Categoria(nombre="Bebidas"))
    imp = RepositorioImpuestosSQLite(conn).guardar(Impuesto(nombre="IVA", tarifa=Decimal("0.19")))
    return RepositorioProductosSQLite(conn).guardar(
        Producto(codigo_barras="B", nombre="Gaseosa", precio=Decimal("3500"),
                 categoria_id=cat.id, impuesto_id=imp.id))


def test_migracion_002_crea_tablas_de_venta(conn):
    tablas = {f["name"] for f in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"usuarios", "clientes", "medios_pago", "caja_sesiones",
            "ventas", "venta_lineas", "pagos"} <= tablas


def test_medios_pago_semilla(conn):
    nombres = {f["nombre"] for f in conn.execute("SELECT nombre FROM medios_pago")}
    assert {"Efectivo", "Tarjeta", "Transferencia"} <= nombres


def test_impuesto_por_id(conn):
    repo = RepositorioImpuestosSQLite(conn)
    guardado = repo.guardar(Impuesto(nombre="IVA", tarifa=Decimal("0.19")))
    leido = repo.por_id(guardado.id)
    assert leido.tarifa == Decimal("0.19")
    assert repo.por_id(999) is None


def test_cliente_guardar_y_buscar(conn):
    repo = RepositorioClientesSQLite(conn)
    c = repo.guardar(Cliente(identificacion="900123", nombre="ACME"))
    assert c.id is not None
    assert repo.por_identificacion("900123").nombre == "ACME"
    assert repo.por_id(c.id).identificacion == "900123"
    assert repo.por_identificacion("nope") is None
    assert len(repo.listar()) == 1


def test_medios_pago_listar_y_por_id(conn):
    repo = RepositorioMediosPagoSQLite(conn)
    assert {m.nombre for m in repo.listar()} >= {"Efectivo", "Tarjeta", "Transferencia"}
    assert repo.por_id(1).nombre == "Efectivo"
    assert repo.por_id(999) is None


def test_guardar_venta_persiste_lineas_y_pagos_y_se_relee(conn):
    p = _producto(conn)
    linea = LineaVenta(producto_id=p.id, descripcion="Gaseosa", cantidad_o_peso=Decimal("2"),
                       precio_unit=Decimal("3500"), impuesto=Decimal("1118"),
                       subtotal=Decimal("7000"))
    venta = Venta(fecha=datetime(2026, 6, 25, 10, 30), lineas=(linea,),
                  total=Decimal("7000"), total_impuestos=Decimal("1118"))
    pagos = [Pago(medio_pago_id=1, monto=Decimal("10000"), referencia="caja")]
    repo = RepositorioVentasSQLite(conn)

    guardada = repo.guardar(venta, pagos)
    assert guardada.id is not None

    releida = repo.por_id(guardada.id)
    assert releida.total == Decimal("7000")
    assert releida.total_impuestos == Decimal("1118")
    assert releida.fecha == datetime(2026, 6, 25, 10, 30)
    assert len(releida.lineas) == 1
    assert releida.lineas[0].subtotal == Decimal("7000")
    assert releida.lineas[0].descripcion == "Gaseosa"

    pagos_releidos = repo.pagos_de(guardada.id)
    assert len(pagos_releidos) == 1
    assert pagos_releidos[0].monto == Decimal("10000")


def test_por_id_inexistente_es_none(conn):
    assert RepositorioVentasSQLite(conn).por_id(999) is None


def test_anular_cambia_estado_a_anulada(conn):
    p = _producto(conn)
    linea = LineaVenta(producto_id=p.id, descripcion="Gaseosa", cantidad_o_peso=Decimal("1"),
                       precio_unit=Decimal("1000"), impuesto=Decimal("0"),
                       subtotal=Decimal("1000"))
    venta = Venta(fecha=datetime(2026, 6, 25, 10, 0), lineas=(linea,),
                  total=Decimal("1000"), total_impuestos=Decimal("0"))
    pagos = [Pago(medio_pago_id=1, monto=Decimal("1000"))]
    repo = RepositorioVentasSQLite(conn)

    guardada = repo.guardar(venta, pagos)

    repo.anular(guardada.id)

    assert repo.por_id(guardada.id).estado == "anulada"
