# E3.b — Anulación de venta (sin dinero) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir anular una venta `pagada`, reponiendo el inventario que descontó y marcándola `anulada`, sin mover dinero.

**Architecture:** Anular es la inversa de registrar. Una función pura `entradas_de_anulacion` (espejo de `salidas_de_venta`) genera movimientos `entrada`; `ServicioAnulacion` carga la venta vía puerto, valida, marca `anulada` y registra esas entradas. Nada de UI, ni reembolsos, ni migración (la columna `ventas.estado` y el estado `"anulada"` ya existen).

**Tech Stack:** Python 3.11+, sqlite3 (stdlib), pytest. Arquitectura hexagonal: `core/` sin Qt ni SQLite; SQL solo en el adaptador de repositorio.

## Global Constraints

- `src/core/` NO conoce Qt ni SQLite: solo entidades, reglas y puertos.
- Acceso a datos solo por puertos `RepositorioX`; SQL únicamente en `src/ventas/repositorio_sqlite.py`.
- Dinero y cantidades con `Decimal` exacto; nunca `float` ni `SUM()` de SQL para dinero.
- Ponytail: mínimo código, stdlib primero, YAGNI. Sin entidad ni migración nuevas.
- Tests: `test_*.py`, estructura espejo por módulo. Excepciones de dominio son subclases de `ValueError` (como `ProductoNoEncontrado`).
- Referencia: [spec E3.b](../specs/2026-06-25-e3b-anulacion-venta-design.md).

---

### Task 1: Función pura `entradas_de_anulacion`

**Files:**
- Modify: `src/core/servicio_venta.py` (añadir función junto a `salidas_de_venta`, ~línea 89-99)
- Test: `tests/core/test_anulacion.py` (crear)

**Interfaces:**
- Consumes: `Venta`, `MovimientoInventario` (de `core.entidades`), ya importados en `servicio_venta.py`.
- Produces: `entradas_de_anulacion(venta: Venta) -> list[MovimientoInventario]` — una `entrada` por línea, `cantidad=linea.cantidad_o_peso`, `ref=f"anulacion:{venta.id}"`, `fecha=venta.fecha`.

- [ ] **Step 1: Write the failing test**

Crear `tests/core/test_anulacion.py`:

```python
from datetime import datetime
from decimal import Decimal
from core.entidades import LineaVenta, Venta
from core.servicio_venta import entradas_de_anulacion


def _venta(id=77) -> Venta:
    lineas = (
        LineaVenta(producto_id=1, descripcion="Gaseosa", cantidad_o_peso=Decimal("2"),
                   precio_unit=Decimal("3500"), impuesto=Decimal("1118"), subtotal=Decimal("7000")),
        LineaVenta(producto_id=2, descripcion="Manzana", cantidad_o_peso=Decimal("1.5"),
                   precio_unit=Decimal("4000"), impuesto=Decimal("0"), subtotal=Decimal("6000")),
    )
    return Venta(fecha=datetime(2026, 6, 25, 10, 0), lineas=lineas,
                 total=Decimal("13000"), total_impuestos=Decimal("1118"), id=id)


def test_entradas_de_anulacion_una_por_linea():
    entradas = entradas_de_anulacion(_venta(id=77))
    assert len(entradas) == 2
    assert all(m.tipo == "entrada" for m in entradas)
    assert entradas[0].producto_id == 1
    assert entradas[0].cantidad == Decimal("2")
    assert entradas[1].cantidad == Decimal("1.5")
    assert all(m.ref == "anulacion:77" for m in entradas)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/core/test_anulacion.py -v`
Expected: FAIL con `ImportError: cannot import name 'entradas_de_anulacion'`.

- [ ] **Step 3: Write minimal implementation**

En `src/core/servicio_venta.py`, justo debajo de `salidas_de_venta` (después de la línea 99):

```python
def entradas_de_anulacion(venta: Venta) -> list[MovimientoInventario]:
    return [
        MovimientoInventario(
            producto_id=linea.producto_id,
            tipo="entrada",
            cantidad=linea.cantidad_o_peso,
            fecha=venta.fecha,
            ref=f"anulacion:{venta.id}",
        )
        for linea in venta.lineas
    ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/core/test_anulacion.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/core/servicio_venta.py tests/core/test_anulacion.py
git commit -m "feat(core): entradas_de_anulacion (inversa de salidas_de_venta)"
```

---

### Task 2: `ServicioAnulacion` + excepciones + puerto `anular`

**Files:**
- Modify: `src/core/servicio_venta.py` (añadir `from dataclasses import replace` arriba; excepciones y clase al final)
- Modify: `src/core/puertos.py` (añadir método `anular` al Protocol `RepositorioVentas`, líneas 45-49)
- Test: `tests/core/test_anulacion.py` (añadir tests con fakes)

**Interfaces:**
- Consumes: `entradas_de_anulacion` (Task 1); `RepositorioVentas` con `por_id(id) -> Venta | None` y nuevo `anular(venta_id: int) -> None`; `RepositorioInventario.registrar(movimiento)`.
- Produces:
  - `VentaNoEncontrada(ValueError)`, `VentaYaAnulada(ValueError)`.
  - `ServicioAnulacion(ventas: RepositorioVentas, inventario: RepositorioInventario)` con `anular(venta_id: int) -> Venta` que devuelve la venta con `estado="anulada"`.

- [ ] **Step 1: Write the failing test**

Añadir a `tests/core/test_anulacion.py`:

```python
import pytest
from dataclasses import replace
from core.entidades import MovimientoInventario
from core.servicio_venta import ServicioAnulacion, VentaNoEncontrada, VentaYaAnulada


class _FakeVentas:
    def __init__(self, venta):
        self._venta = venta
        self.anulada_id = None
    def por_id(self, id):
        return self._venta if self._venta and self._venta.id == id else None
    def anular(self, venta_id):
        self.anulada_id = venta_id
        self._venta = replace(self._venta, estado="anulada")


class _FakeInventario:
    def __init__(self):
        self.movimientos = []
    def registrar(self, m):
        self.movimientos.append(m)
        return m


def test_anular_marca_estado_y_repone_inventario():
    ventas = _FakeVentas(_venta(id=77))
    inventario = _FakeInventario()
    anulada = ServicioAnulacion(ventas, inventario).anular(77)
    assert anulada.estado == "anulada"
    assert ventas.anulada_id == 77
    assert [m.tipo for m in inventario.movimientos] == ["entrada", "entrada"]
    assert [m.cantidad for m in inventario.movimientos] == [Decimal("2"), Decimal("1.5")]
    assert all(m.ref == "anulacion:77" for m in inventario.movimientos)


def test_anular_venta_inexistente_falla():
    ventas = _FakeVentas(None)
    with pytest.raises(VentaNoEncontrada):
        ServicioAnulacion(ventas, _FakeInventario()).anular(999)


def test_anular_venta_ya_anulada_falla_y_no_repone():
    ventas = _FakeVentas(replace(_venta(id=77), estado="anulada"))
    inventario = _FakeInventario()
    with pytest.raises(VentaYaAnulada):
        ServicioAnulacion(ventas, inventario).anular(77)
    assert inventario.movimientos == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/core/test_anulacion.py -v`
Expected: FAIL con `ImportError: cannot import name 'ServicioAnulacion'`.

- [ ] **Step 3: Write minimal implementation**

En `src/core/servicio_venta.py`, cambiar la cabecera de imports para añadir `replace`:

```python
from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from decimal import Decimal
```

Al final del archivo, después de `ServicioRegistroVenta`:

```python
class VentaNoEncontrada(ValueError):
    pass


class VentaYaAnulada(ValueError):
    pass


class ServicioAnulacion:
    """Reversa una venta: repone inventario y la marca 'anulada'. No mueve dinero."""

    def __init__(self, ventas: RepositorioVentas, inventario: RepositorioInventario) -> None:
        self._ventas = ventas
        self._inventario = inventario

    def anular(self, venta_id: int) -> Venta:
        venta = self._ventas.por_id(venta_id)
        if venta is None:
            raise VentaNoEncontrada(f"venta inexistente: {venta_id}")
        if venta.estado == "anulada":
            raise VentaYaAnulada(f"venta {venta_id} ya estaba anulada")
        self._ventas.anular(venta_id)
        for movimiento in entradas_de_anulacion(venta):
            self._inventario.registrar(movimiento)
        return replace(venta, estado="anulada")
```

En `src/core/puertos.py`, añadir el método al Protocol `RepositorioVentas` (después de `pagos_de`, antes o después de `totales_por_medio`):

```python
class RepositorioVentas(Protocol):
    def guardar(self, venta: Venta, pagos: list[Pago]) -> Venta: ...
    def por_id(self, id: int) -> Venta | None: ...
    def pagos_de(self, venta_id: int) -> list[Pago]: ...
    def anular(self, venta_id: int) -> None: ...
    def totales_por_medio(self, caja_sesion_id: int) -> dict[int, Decimal]: ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/core/test_anulacion.py -v`
Expected: PASS (los 4 tests).

- [ ] **Step 5: Commit**

```bash
git add src/core/servicio_venta.py src/core/puertos.py tests/core/test_anulacion.py
git commit -m "feat(core): ServicioAnulacion (repone stock, marca anulada) y puerto anular"
```

---

### Task 3: Adaptador SQLite `RepositorioVentasSQLite.anular`

**Files:**
- Modify: `src/ventas/repositorio_sqlite.py` (método dentro de `RepositorioVentasSQLite`, junto a `por_id`/`pagos_de`)
- Test: `tests/ventas/test_repositorio_ventas.py` (añadir test)

**Interfaces:**
- Consumes: conexión SQLite con esquema de `002_ventas.sql` (tabla `ventas` con columna `estado`).
- Produces: `RepositorioVentasSQLite.anular(venta_id: int) -> None` que ejecuta `UPDATE ventas SET estado='anulada'`.

- [ ] **Step 1: Write the failing test**

Añadir a `tests/ventas/test_repositorio_ventas.py` (usa la fixture `conn` de `tests/ventas/conftest.py`; el archivo ya prueba `RepositorioVentasSQLite`, reutilizar su forma de armar una `Venta` — si no hay helper, este test es autocontenido):

```python
def test_anular_cambia_estado_a_anulada(conn):
    from datetime import datetime
    from decimal import Decimal
    from core.entidades import LineaVenta, Pago, Venta
    from ventas.repositorio_sqlite import RepositorioVentasSQLite

    repo = RepositorioVentasSQLite(conn)
    venta = Venta(
        fecha=datetime(2026, 6, 25, 10, 0),
        lineas=(LineaVenta(producto_id=1, descripcion="X", cantidad_o_peso=Decimal("1"),
                           precio_unit=Decimal("1000"), impuesto=Decimal("0"),
                           subtotal=Decimal("1000")),),
        total=Decimal("1000"), total_impuestos=Decimal("0"), caja_sesion_id=1,
    )
    guardada = repo.guardar(venta, [Pago(medio_pago_id=1, monto=Decimal("1000"))])

    repo.anular(guardada.id)

    assert repo.por_id(guardada.id).estado == "anulada"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/ventas/test_repositorio_ventas.py::test_anular_cambia_estado_a_anulada -v`
Expected: FAIL con `AttributeError: 'RepositorioVentasSQLite' object has no attribute 'anular'`.

- [ ] **Step 3: Write minimal implementation**

En `src/ventas/repositorio_sqlite.py`, dentro de `RepositorioVentasSQLite`, después de `pagos_de` (antes de `totales_por_medio`):

```python
    def anular(self, venta_id: int) -> None:
        self._conn.execute(
            "UPDATE ventas SET estado = 'anulada' WHERE id = ?", (venta_id,))
        self._conn.commit()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/ventas/test_repositorio_ventas.py::test_anular_cambia_estado_a_anulada -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/ventas/repositorio_sqlite.py tests/ventas/test_repositorio_ventas.py
git commit -m "feat(ventas): adaptador SQLite RepositorioVentasSQLite.anular"
```

---

### Task 4: Flujo crítico #3 — test de integración de anulación

**Files:**
- Test: `tests/ventas/test_flujo_anulacion.py` (crear)

**Interfaces:**
- Consumes: `ServicioAnulacion` (Task 2), `RepositorioVentasSQLite.anular` (Task 3), `ServicioRegistroVenta`/`ServicioVenta` existentes, repos SQLite de inventario/ventas, fixture `conn`.
- Produces: nada (es la prueba de cierre del flujo crítico #3).

- [ ] **Step 1: Write the failing test**

Crear `tests/ventas/test_flujo_anulacion.py` (mismo `_seed` que `test_flujo_cierre_caja.py`):

```python
from datetime import datetime
from decimal import Decimal
from core.entidades import Categoria, Impuesto, MovimientoInventario, Pago, Producto
from core.servicio_venta import ServicioAnulacion, ServicioRegistroVenta, ServicioVenta
from inventario.repositorio_sqlite import (
    RepositorioCategoriasSQLite,
    RepositorioImpuestosSQLite,
    RepositorioInventarioSQLite,
    RepositorioProductosSQLite,
)
from ventas.repositorio_sqlite import RepositorioVentasSQLite


def _seed(conn):
    cat = RepositorioCategoriasSQLite(conn).guardar(Categoria(nombre="Surtido"))
    iva = RepositorioImpuestosSQLite(conn).guardar(Impuesto(nombre="IVA", tarifa=Decimal("0.19")))
    prods = RepositorioProductosSQLite(conn)
    gaseosa = prods.guardar(Producto(codigo_barras="B", nombre="Gaseosa", precio=Decimal("3500"),
                                     categoria_id=cat.id, impuesto_id=iva.id))
    inv = RepositorioInventarioSQLite(conn)
    inv.registrar(MovimientoInventario(producto_id=gaseosa.id, tipo="entrada",
                                       cantidad=Decimal("10"), fecha=datetime(2026, 6, 25, 8, 0)))
    return gaseosa, inv


def test_anular_repone_stock_y_sale_del_arqueo(conn):
    gaseosa, inv = _seed(conn)
    ventas = RepositorioVentasSQLite(conn)
    registro = ServicioRegistroVenta(ventas, inv)

    s = ServicioVenta(RepositorioProductosSQLite(conn), RepositorioImpuestosSQLite(conn))
    s.agregar("B", cantidad=2)
    venta = s.confirmar(fecha=datetime(2026, 6, 25, 10, 0), caja_sesion_id=1)
    guardada = registro.registrar(venta, [Pago(medio_pago_id=1, monto=Decimal("7000"))])

    assert inv.stock_de(gaseosa.id) == Decimal("8")
    assert ventas.totales_por_medio(1) == {1: Decimal("7000")}

    anulada = ServicioAnulacion(ventas, inv).anular(guardada.id)

    assert anulada.estado == "anulada"
    assert inv.stock_de(gaseosa.id) == Decimal("10")   # stock repuesto
    assert ventas.totales_por_medio(1) == {}           # ya no cuenta en el arqueo
```

- [ ] **Step 2: Run test to verify it fails (o pasa directo)**

Run: `python -m pytest tests/ventas/test_flujo_anulacion.py -v`
Expected: PASS si Tasks 1-3 están completas. (Si falla, es señal de regresión en esos tasks: corregir antes de seguir.)

- [ ] **Step 3: Run full suite**

Run: `python -m pytest -q`
Expected: toda la suite verde (los 85+ previos más los nuevos de anulación).

- [ ] **Step 4: Commit**

```bash
git add tests/ventas/test_flujo_anulacion.py
git commit -m "test(ventas): flujo critico #3 anulacion repone stock y sale del arqueo"
```

---

## Self-Review

**Spec coverage:**
- `entradas_de_anulacion` → Task 1. ✓
- `ServicioAnulacion` + `VentaNoEncontrada`/`VentaYaAnulada` → Task 2. ✓
- Puerto `RepositorioVentas.anular` → Task 2. ✓
- Adaptador SQLite `anular`, sin migración → Task 3. ✓
- Venta anulada desaparece de `totales_por_medio` (sin tocar dinero) → verificado en Task 4. ✓
- Flujo crítico #3 (vender → anular → stock repuesto + fuera del arqueo) → Task 4. ✓
- Tests de dominio (doble anulación, inexistente, una entrada por línea) → Tasks 1-2. ✓
- Decisión "permitir anular sobre sesión cerrada": ningún task añade guard de sesión → consistente con el default del spec. ✓

**Placeholder scan:** sin TBD/TODO; todo el código está completo en cada step. ✓

**Type consistency:** `entradas_de_anulacion(venta) -> list[MovimientoInventario]`, `ServicioAnulacion.anular(venta_id) -> Venta`, `RepositorioVentas.anular(venta_id) -> None` usados igual en Tasks 1-4. El fake `_FakeVentas` de Task 2 implementa `por_id` y `anular` (la firma del puerto). ✓
