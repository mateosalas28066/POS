from datetime import datetime
from decimal import Decimal

import pytest

from core.entidades import MovimientoInventario, Producto
from core.servicio_despiece import (
    ServicioDespiece, StockCanalInsuficiente, prorratear_costeo_despiece,
)


class _FakeDespieces:
    def __init__(self) -> None:
        self._por_id = {}
        self._siguiente = 1

    def guardar(self, despiece):
        from dataclasses import replace
        guardado = replace(despiece, id=self._siguiente)
        self._por_id[self._siguiente] = guardado
        self._siguiente += 1
        return guardado

    def por_id(self, id: int):
        return self._por_id.get(id)


class _FakeInventario:
    def __init__(self, stock: dict[int, Decimal] | None = None) -> None:
        self._stock = dict(stock or {})
        self.movimientos: list[MovimientoInventario] = []

    def registrar(self, movimiento: MovimientoInventario) -> MovimientoInventario:
        self.movimientos.append(movimiento)
        actual = self._stock.get(movimiento.producto_id, Decimal("0"))
        if movimiento.tipo == "entrada":
            self._stock[movimiento.producto_id] = actual + movimiento.cantidad
        else:
            self._stock[movimiento.producto_id] = actual - movimiento.cantidad
        return movimiento

    def stock_de(self, producto_id: int) -> Decimal:
        return self._stock.get(producto_id, Decimal("0"))

    def movimientos_en(self, desde, hasta):
        return list(self.movimientos)


class _FakeProductos:
    def __init__(self, productos: dict[int, Producto] | None = None) -> None:
        self._por_id = dict(productos or {})

    def guardar(self, producto):
        raise NotImplementedError

    def actualizar(self, producto):
        self._por_id[producto.id] = producto
        return producto

    def por_id(self, id: int):
        return self._por_id.get(id)

    def por_codigo(self, codigo_barras: str):
        raise NotImplementedError

    def listar(self):
        return list(self._por_id.values())


def _servicio(stock_canal: Decimal, productos: dict[int, Producto]):
    inventario = _FakeInventario(stock={1: stock_canal})
    fake_productos = _FakeProductos(productos)
    servicio = ServicioDespiece(_FakeDespieces(), inventario, fake_productos)
    return servicio, inventario, fake_productos


# --- prorratear_costeo_despiece (función pura) ---

def test_prorratea_por_valor_de_venta_cuando_todos_tienen_precio():
    lineas = prorratear_costeo_despiece(
        Decimal("100000"),
        [
            (10, Decimal("6"), Decimal("5000")),   # valor 30000
            (20, Decimal("4"), Decimal("20000")),  # valor 80000
        ],
    )
    linea_a, linea_b = lineas
    assert linea_a.costo_asignado == Decimal("100000") * Decimal("30000") / Decimal("110000")
    assert linea_b.costo_asignado == Decimal("100000") * Decimal("80000") / Decimal("110000")
    # el corte de mayor valor de venta recibe proporcionalmente más costo
    assert linea_b.costo_asignado > linea_a.costo_asignado
    assert linea_a.costo_asignado + linea_b.costo_asignado == Decimal("100000")
    assert linea_a.costo_unit == linea_a.costo_asignado / Decimal("6")
    assert linea_b.costo_unit == linea_b.costo_asignado / Decimal("4")


def test_fallback_a_prorrateo_por_peso_si_algun_corte_no_tiene_precio():
    lineas = prorratear_costeo_despiece(
        Decimal("100000"),
        [
            (10, Decimal("6"), Decimal("0")),      # sin precio -> fallback para TODOS
            (20, Decimal("4"), Decimal("20000")),
        ],
    )
    linea_a, linea_b = lineas
    # prorrateo por peso: A 6/10, B 4/10
    assert linea_a.costo_asignado == Decimal("60000")
    assert linea_a.costo_unit == Decimal("10000")
    assert linea_b.costo_asignado == Decimal("40000")
    assert linea_b.costo_unit == Decimal("10000")


def test_prorratear_sin_cortes_falla():
    with pytest.raises(ValueError):
        prorratear_costeo_despiece(Decimal("100000"), [])


# --- ServicioDespiece.registrar (end-to-end con fakes) ---

def test_registrar_salida_canal_y_entradas_de_cortes():
    productos = {
        2: Producto(codigo_barras="LOMO", nombre="Lomo", precio=Decimal("10000"), id=2,
                    vendido_por_peso=True, unidad="kg"),
        3: Producto(codigo_barras="MOLIDA", nombre="Molida", precio=Decimal("20000"), id=3,
                    vendido_por_peso=True, unidad="kg"),
    }
    servicio, inventario, _ = _servicio(Decimal("50"), productos)

    despiece = servicio.registrar(
        producto_canal_id=1,
        peso_canal=Decimal("10"),
        costo_canal=Decimal("100000"),
        cortes=[(2, Decimal("2")), (3, Decimal("3"))],
        fecha=datetime(2026, 7, 1, 10, 0),
    )

    assert despiece.id is not None
    salidas = [m for m in inventario.movimientos if m.tipo == "salida"]
    entradas = [m for m in inventario.movimientos if m.tipo == "entrada"]

    assert len(salidas) == 1
    assert salidas[0].producto_id == 1
    assert salidas[0].cantidad == Decimal("10")
    assert salidas[0].ref == f"despiece:{despiece.id}"

    assert len(entradas) == 2
    entrada_lomo = next(m for m in entradas if m.producto_id == 2)
    entrada_molida = next(m for m in entradas if m.producto_id == 3)
    assert entrada_lomo.cantidad == Decimal("2")
    assert entrada_molida.cantidad == Decimal("3")


def test_registrar_actualiza_costo_de_cada_corte():
    productos = {
        2: Producto(codigo_barras="LOMO", nombre="Lomo", precio=Decimal("10000"), id=2,
                    vendido_por_peso=True, unidad="kg"),
        3: Producto(codigo_barras="MOLIDA", nombre="Molida", precio=Decimal("20000"), id=3,
                    vendido_por_peso=True, unidad="kg"),
    }
    servicio, _, fake_productos = _servicio(Decimal("50"), productos)

    despiece = servicio.registrar(
        producto_canal_id=1,
        peso_canal=Decimal("10"),
        costo_canal=Decimal("100000"),
        cortes=[(2, Decimal("2")), (3, Decimal("3"))],
        fecha=datetime(2026, 7, 1, 10, 0),
    )

    # valor A = 2*10000=20000, valor B = 3*20000=60000, total=80000
    linea_a = next(l for l in despiece.lineas if l.producto_corte_id == 2)
    linea_b = next(l for l in despiece.lineas if l.producto_corte_id == 3)
    assert linea_a.costo_unit == Decimal("12500.00")
    assert linea_b.costo_unit == Decimal("25000.00")

    assert fake_productos.por_id(2).costo == linea_a.costo_unit
    assert fake_productos.por_id(3).costo == linea_b.costo_unit


def test_stock_canal_insuficiente_lanza_excepcion():
    productos = {
        2: Producto(codigo_barras="LOMO", nombre="Lomo", precio=Decimal("10000"), id=2,
                    vendido_por_peso=True, unidad="kg"),
    }
    servicio, _, _ = _servicio(Decimal("5"), productos)

    with pytest.raises(StockCanalInsuficiente):
        servicio.registrar(
            producto_canal_id=1,
            peso_canal=Decimal("10"),
            costo_canal=Decimal("100000"),
            cortes=[(2, Decimal("10"))],
            fecha=datetime(2026, 7, 1, 10, 0),
        )
