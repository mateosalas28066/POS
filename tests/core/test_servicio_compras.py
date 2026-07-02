from dataclasses import replace
from datetime import datetime
from decimal import Decimal
import pytest
from core.entidades import Compra, LineaCompra, Producto, MovimientoInventario
from core.servicio_compras import ServicioCompras


class _FakeCompras:
    def __init__(self) -> None:
        self._por_id: dict[int, Compra] = {}
        self._siguiente = 1

    def guardar(self, compra: Compra) -> Compra:
        guardada = replace(compra, id=self._siguiente)
        self._por_id[self._siguiente] = guardada
        self._siguiente += 1
        return guardada

    def por_id(self, id: int) -> Compra | None:
        return self._por_id.get(id)

    def compras_en(self, desde: datetime, hasta: datetime) -> list[Compra]:
        return [c for c in self._por_id.values() if desde <= c.fecha <= hasta]

    def compras_de_proveedor(self, proveedor_id: int) -> list[Compra]:
        return [c for c in self._por_id.values() if c.proveedor_id == proveedor_id]


class _FakeInventario:
    def __init__(self) -> None:
        self._movimientos: list[MovimientoInventario] = []

    def registrar(self, movimiento: MovimientoInventario) -> MovimientoInventario:
        guardado = replace(movimiento, id=len(self._movimientos) + 1)
        self._movimientos.append(guardado)
        return guardado

    def stock_de(self, producto_id: int) -> Decimal:
        total = Decimal("0")
        for m in self._movimientos:
            if m.producto_id == producto_id:
                if m.tipo == "entrada":
                    total += m.cantidad
                else:
                    total -= m.cantidad
        return total

    def movimientos_en(self, desde: datetime, hasta: datetime) -> list[MovimientoInventario]:
        return [m for m in self._movimientos if desde <= m.fecha <= hasta]


class _FakeProductos:
    def __init__(self) -> None:
        self._por_id: dict[int, Producto] = {}
        self._datos = {
            1: Producto(
                codigo_barras="001", nombre="Carne molida",
                precio=Decimal("15000"), costo=Decimal("8000"), id=1
            ),
        }
        self._por_id.update(self._datos)

    def guardar(self, producto: Producto) -> Producto:
        self._por_id[producto.id] = producto
        return producto

    def actualizar(self, producto: Producto) -> Producto:
        self._por_id[producto.id] = producto
        return producto

    def por_id(self, id: int) -> Producto | None:
        return self._por_id.get(id)

    def por_codigo(self, codigo_barras: str) -> Producto | None:
        for p in self._por_id.values():
            if p.codigo_barras == codigo_barras:
                return p
        return None

    def listar(self) -> list[Producto]:
        return list(self._por_id.values())


def _servicio() -> ServicioCompras:
    return ServicioCompras(_FakeCompras(), _FakeInventario(), _FakeProductos())


def test_registrar_compra_con_una_linea_alimenta_stock():
    serv = _servicio()
    linea = LineaCompra(
        producto_id=1,
        descripcion="Carne molida",
        cantidad=Decimal("10"),
        costo_unit=Decimal("8500"),
        subtotal=Decimal("85000"),
    )
    compra = Compra(
        proveedor_id=1,
        fecha=datetime(2026, 7, 1, 10, 0),
        lineas=(linea,),
        total=Decimal("85000"),
    )
    guardada = serv.registrar(compra)
    assert guardada.id is not None
    assert guardada.id == 1
    # Verificar que el inventario registró una entrada
    inventario = serv._inventario
    movimientos = inventario.movimientos_en(
        datetime(2026, 7, 1, 0, 0), datetime(2026, 7, 2, 0, 0)
    )
    assert len(movimientos) == 1
    assert movimientos[0].tipo == "entrada"
    assert movimientos[0].cantidad == Decimal("10")
    assert movimientos[0].producto_id == 1
    assert f"compra:{guardada.id}" in movimientos[0].ref


def test_registrar_compra_actualiza_costo_producto():
    serv = _servicio()
    linea = LineaCompra(
        producto_id=1,
        descripcion="Carne molida",
        cantidad=Decimal("5"),
        costo_unit=Decimal("9000"),
        subtotal=Decimal("45000"),
    )
    compra = Compra(
        proveedor_id=1,
        fecha=datetime(2026, 7, 1, 10, 0),
        lineas=(linea,),
        total=Decimal("45000"),
    )
    serv.registrar(compra)
    # Verificar que el producto se actualizó
    productos = serv._productos
    producto = productos.por_id(1)
    assert producto is not None
    assert producto.costo == Decimal("9000")


def test_registrar_compra_sin_lineas_falla():
    serv = _servicio()
    compra = Compra(
        proveedor_id=1,
        fecha=datetime(2026, 7, 1, 10, 0),
        lineas=(),
        total=Decimal("0"),
    )
    with pytest.raises(ValueError, match="no se puede registrar una compra sin líneas"):
        serv.registrar(compra)


def test_registrar_compra_credito_no_hace_nada_especial():
    """El estado de crédito se guarda pero no requiere lógica adicional en este task."""
    serv = _servicio()
    linea = LineaCompra(
        producto_id=1,
        descripcion="Carne molida",
        cantidad=Decimal("8"),
        costo_unit=Decimal("8700"),
        subtotal=Decimal("69600"),
    )
    compra = Compra(
        proveedor_id=1,
        fecha=datetime(2026, 7, 1, 10, 0),
        lineas=(linea,),
        total=Decimal("69600"),
        estado="credito",
    )
    guardada = serv.registrar(compra)
    assert guardada.estado == "credito"
    # Se debe registrar inventario igualmente
    inventario = serv._inventario
    movimientos = inventario.movimientos_en(
        datetime(2026, 7, 1, 0, 0), datetime(2026, 7, 2, 0, 0)
    )
    assert len(movimientos) == 1
    assert movimientos[0].cantidad == Decimal("8")


def test_registrar_compra_con_multiples_lineas():
    """Registra múltiples líneas y actualiza costos de múltiples productos."""
    serv = _servicio()
    # Agregar segundo producto
    prod2 = Producto(
        codigo_barras="002", nombre="Carne de res",
        precio=Decimal("20000"), costo=Decimal("10000"), id=2
    )
    serv._productos.guardar(prod2)

    linea1 = LineaCompra(
        producto_id=1,
        descripcion="Carne molida",
        cantidad=Decimal("5"),
        costo_unit=Decimal("9000"),
        subtotal=Decimal("45000"),
    )
    linea2 = LineaCompra(
        producto_id=2,
        descripcion="Carne de res",
        cantidad=Decimal("3"),
        costo_unit=Decimal("11000"),
        subtotal=Decimal("33000"),
    )
    compra = Compra(
        proveedor_id=1,
        fecha=datetime(2026, 7, 1, 10, 0),
        lineas=(linea1, linea2),
        total=Decimal("78000"),
    )
    guardada = serv.registrar(compra)
    # Verificar inventario: dos movimientos
    inventario = serv._inventario
    movimientos = inventario.movimientos_en(
        datetime(2026, 7, 1, 0, 0), datetime(2026, 7, 2, 0, 0)
    )
    assert len(movimientos) == 2
    assert movimientos[0].producto_id == 1
    assert movimientos[0].cantidad == Decimal("5")
    assert movimientos[1].producto_id == 2
    assert movimientos[1].cantidad == Decimal("3")

    # Verificar costos actualizados
    productos = serv._productos
    p1 = productos.por_id(1)
    p2 = productos.por_id(2)
    assert p1.costo == Decimal("9000")
    assert p2.costo == Decimal("11000")
