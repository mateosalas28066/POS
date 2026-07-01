from datetime import datetime
from decimal import Decimal

from core.entidades import Cliente, LineaVenta, Venta
from ventas.repositorio_sqlite import RepositorioClientesSQLite, RepositorioVentasSQLite


def test_cliente_persiste_descuento_pct(conn):
    repo = RepositorioClientesSQLite(conn)
    c = repo.guardar(Cliente(identificacion="900", nombre="Mayorista", descuento_pct=Decimal("0.1")))
    assert repo.por_id(c.id).descuento_pct == Decimal("0.1")


def test_venta_persiste_descuento_pct(conn):
    linea = LineaVenta(producto_id=1, descripcion="Arroz", cantidad_o_peso=Decimal("1"),
                       precio_unit=Decimal("2500"), impuesto=Decimal("0"), subtotal=Decimal("2250"))
    conn.execute("INSERT INTO categorias (id, nombre) VALUES (1, 'X')")
    conn.execute("INSERT INTO impuestos (id, nombre, tarifa) VALUES (1, 'IVA 0%', '0')")
    conn.execute(
        "INSERT INTO productos (id, codigo_barras, nombre, precio, costo, categoria_id, "
        "impuesto_id, vendido_por_peso, unidad) VALUES (1, '1', 'Arroz', '2500', '0', 1, 1, 0, 'und')")
    venta = Venta(fecha=datetime.now(), lineas=(linea,), total=Decimal("2250"),
                  total_impuestos=Decimal("0"), descuento_pct=Decimal("0.1"))
    repo = RepositorioVentasSQLite(conn)
    guardada = repo.guardar(venta, [])
    assert repo.por_id(guardada.id).descuento_pct == Decimal("0.1")
