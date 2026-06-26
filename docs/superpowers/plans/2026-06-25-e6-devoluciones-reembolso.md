# E6 Devoluciones con reembolso — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir devolver una venta `pagada` (parcial por línea/cantidad o total) **moviendo dinero**: registrar la salida de dinero por medio de pago (reembolso), reponer el inventario de las líneas devueltas y reflejar el efectivo devuelto en el arqueo de la caja. Cierra el resto del flujo crítico #3 ("devolución/anulación") de `testing-pos`.

**Architecture:** Hexagonal estricta, igual que E3/E3.b. La devolución se modela como un **documento `Devolucion`** en `core` (entidades frozen) que referencia la venta original (inmutable) con sus líneas devueltas y sus reembolsos. Funciones puras (`construir_lineas_devolucion`, `entradas_de_devolucion`) + `ServicioDevolucion` que solo conoce puertos (`RepositorioVentas`, `RepositorioDevoluciones`, `RepositorioInventario`). La persistencia es un adaptador SQLite en `src/ventas/`. El arqueo se mantiene en `core`: la única costura es netear los reembolsos dentro de `RepositorioVentas.totales_por_medio` (en el adaptador), de modo que `ServicioCaja`/`calcular_arqueo` no cambian.

**Tech Stack:** Python 3.11+, stdlib `sqlite3` + `decimal` + `dataclasses` + `typing.Protocol`, `pytest`. Sin Qt en este epic (la `PantallaDevoluciones` se difiere, como E3.b dejó la anulación sin UI).

## Decisiones de diseño (revisar antes de ejecutar)

Resumen del spec [2026-06-25-e6-devoluciones-reembolso-design.md](../specs/2026-06-25-e6-devoluciones-reembolso-design.md):

1. **Documento `Devolucion`, no "venta negativa".** `LineaVenta`, `MovimientoInventario` y `Pago` exigen cantidades/montos **positivos**; una venta de signo negativo rompería invariantes en cascada. La venta original queda **inmutable** (`total` no se reescribe); solo se actualiza un marcador `estado`.

2. **Estados nuevos `devuelta_parcial`/`devuelta` son marcador denormalizado.** La verdad de "cuánto se devolvió" vive en la tabla `devoluciones` (`devuelto_por_linea`). El arqueo **no** depende del marcador: `totales_por_medio` excluye solo `anulada` y netea los reembolsos aparte, así el cuadre es robusto sin importar el estado.

3. **El reembolso golpea el arqueo de la sesión donde sale el dinero**, no el de la sesión original de la venta. El efectivo sale del cajón de *hoy*; por eso `Devolucion.caja_sesion_id` es la sesión abierta al reembolsar, y el neteo de egresos se hace por `devoluciones.caja_sesion_id`.

4. **Prorrateo desde la `LineaVenta` capturada**, no del producto/impuesto vivo: respeta el snapshot de la venta y su redondeo a pesos enteros. Devolución de línea completa ⇒ `ratio = 1` ⇒ subtotal/impuesto exactos.

5. **El reembolso debe cuadrar con lo devuelto:** `Σ reembolsos.monto == Σ subtotales devueltos`. El cajero elige el/los medios de salida (libremente; el arqueo netea por medio). Restringir al medio original es regla futura.

6. **No se fusiona `ServicioAnulacion` con `ServicioDevolucion`.** Anulación (E3.b) **prohíbe** mover dinero; devolución **exige** reembolso cuadrado. E3.b ya está implementada y testeada → Ponytail = no churn. Se reutiliza el patrón, la función pura de entradas y el puerto de inventario.

7. **Nota crédito DIAN: solo costura, sin código en E6.** El puerto `EmisorDIAN` (hoy solo docstring) y el armado del payload llegan con el epic DIAN. El único artefacto concreto es la columna reservada `devoluciones.cufe_nota` (patrón "reservado DIAN" de `clientes`/`impuestos`). No se añade un `Protocol` sin implementador (YAGNI).

## Global Constraints

- **Python ≥ 3.11** — sintaxis `X | None`, `tuple[...]`, `dict[int, Decimal]` nativas.
- **`src/core/` NO importa Qt ni SQLite ni pyserial.** Prohibido `import sqlite3` / `from PySide6` / `import serial` bajo `src/core/`. Los servicios reciben repositorios por inyección (objetos que cumplen los `Protocol`).
- **SQL solo en adaptadores de repositorio** (`src/inventario/`, `src/ventas/`). Nada de SQL en `core`/`caja`.
- **Dinero y cantidades con `decimal.Decimal`**, nunca `float`. Columnas SQLite declaradas `DECIMAL`. **Las sumas se hacen en Python**, nunca con `SUM()` de SQL.
- **Redondeo a peso colombiano entero** con `ROUND_HALF_UP` en cifras monetarias prorrateadas.
- **Nombres de dominio en español** (`Devolucion`, `LineaDevolucion`, `ItemDevolucion`, `ServicioDevolucion`, `devolver`, `reembolsos`).
- **Entidades/valores del dominio = `@dataclass(frozen=True)`**; puertos = `typing.Protocol`. Mutar = `dataclasses.replace`.
- **Tests:** `pytest`, `pythonpath = src` (ya en `pytest.ini`); archivos `test_*.py`, estructura espejo por módulo. Imports tipo `from core.servicio_venta import ServicioDevolucion`.
- **Migraciones versionadas** en `scripts/migraciones/NNN_*.sql`; las aplica `aplicar_migraciones` por `glob` ordenado (auto-descubre `004_*.sql`). Integridad referencial activa (`PRAGMA foreign_keys = ON`).
- **No romper E3/E3.b:** `totales_por_medio` debe seguir excluyendo ventas `anulada`; `RepositorioVentas.anular` se conserva.
- **Suite base: 104 passed, 2 skipped.** Ningún test existente puede romperse.

---

## File Structure

**Core (dominio puro)**
- `src/core/entidades.py` — *extender* `ESTADOS_VENTA`; *añadir* `ItemDevolucion`, `LineaDevolucion`, `Devolucion`, `ESTADOS_DEVOLUCION`.
- `src/core/servicio_venta.py` — *añadir* `construir_lineas_devolucion`, `entradas_de_devolucion`, `_todo_devuelto`, `ServicioDevolucion` + excepciones.
- `src/core/puertos.py` — *extender* `RepositorioVentas` (`marcar_estado`); *añadir* `RepositorioDevoluciones`.

**Persistencia (adaptadores SQLite)**
- `scripts/migraciones/004_devoluciones.sql` — **nuevo**: tablas `devoluciones`, `devolucion_lineas`, `devolucion_reembolsos`.
- `src/ventas/repositorio_sqlite.py` — *añadir* `RepositorioDevolucionesSQLite`; *añadir* `RepositorioVentasSQLite.marcar_estado`; *reescribir* `RepositorioVentasSQLite.totales_por_medio` (netea reembolsos).

**Tests**
- `tests/core/test_entidades_devolucion.py` — **nuevo**: invariantes de `ItemDevolucion`/`LineaDevolucion`/`Devolucion` y estados nuevos de `Venta`.
- `tests/core/test_devolucion.py` — **nuevo**: `construir_lineas_devolucion`, `entradas_de_devolucion` (puras).
- `tests/core/test_servicio_devolucion.py` — **nuevo**: `ServicioDevolucion` con fakes.
- `tests/ventas/test_repositorio_devoluciones.py` — **nuevo**: adaptador + `devuelto_por_linea` + `totales_por_medio` neto + atribución por sesión.
- `tests/ventas/test_flujo_devolucion.py` — **nuevo**: flujo crítico #3 (integración).

**Docs**
- `docs/README-pos.md` — marcar E6 implementado.

---

### Task E6.1: Entidades de devolución + estados de venta

**Files:**
- Modify: `src/core/entidades.py`
- Test: `tests/core/test_entidades_devolucion.py`

**Interfaces:**
- Consumes: `dataclass`, `datetime`, `Decimal`, `CERO`, `Pago` (ya en el módulo).
- Produces:
  - `ESTADOS_VENTA = ("pagada", "anulada", "devuelta_parcial", "devuelta")`.
  - `ESTADOS_DEVOLUCION = ("emitida",)`.
  - `ItemDevolucion(venta_linea_id: int, cantidad_o_peso: Decimal)` — input del cajero; `cantidad_o_peso > 0`.
  - `LineaDevolucion(producto_id: int, cantidad_o_peso: Decimal, impuesto: Decimal, subtotal: Decimal, venta_linea_id: int | None = None, devolucion_id: int | None = None, id: int | None = None)` — `cantidad_o_peso > 0`; `subtotal ≥ 0`; `impuesto ≥ 0`.
  - `Devolucion(venta_id: int, fecha: datetime, lineas: tuple[LineaDevolucion, ...], total: Decimal, total_impuestos: Decimal, reembolsos: tuple[Pago, ...], caja_sesion_id: int | None = None, usuario_id: int | None = None, estado: str = "emitida", id: int | None = None)` — `estado ∈ ESTADOS_DEVOLUCION`.

- [ ] **Step 1: Write the failing test**

```python
# tests/core/test_entidades_devolucion.py
from datetime import datetime
from decimal import Decimal

import pytest

from core.entidades import Devolucion, ItemDevolucion, LineaDevolucion, Pago, Venta


def test_item_devolucion_cantidad_no_positiva_falla():
    with pytest.raises(ValueError):
        ItemDevolucion(venta_linea_id=1, cantidad_o_peso=Decimal("0"))


def test_linea_devolucion_minima():
    l = LineaDevolucion(producto_id=1, cantidad_o_peso=Decimal("1.5"),
                        impuesto=Decimal("0"), subtotal=Decimal("6000"))
    assert l.devolucion_id is None
    assert l.id is None


def test_linea_devolucion_valores_negativos_fallan():
    with pytest.raises(ValueError):
        LineaDevolucion(producto_id=1, cantidad_o_peso=Decimal("1"),
                        impuesto=Decimal("0"), subtotal=Decimal("-1"))
    with pytest.raises(ValueError):
        LineaDevolucion(producto_id=1, cantidad_o_peso=Decimal("0"),
                        impuesto=Decimal("0"), subtotal=Decimal("0"))


def test_devolucion_minima_estado_emitida():
    d = Devolucion(
        venta_id=77, fecha=datetime(2026, 6, 25, 11, 0),
        lineas=(LineaDevolucion(producto_id=1, cantidad_o_peso=Decimal("1"),
                                impuesto=Decimal("0"), subtotal=Decimal("3500")),),
        total=Decimal("3500"), total_impuestos=Decimal("0"),
        reembolsos=(Pago(medio_pago_id=1, monto=Decimal("3500")),))
    assert d.estado == "emitida"
    assert d.caja_sesion_id is None
    assert d.id is None


def test_devolucion_estado_invalido_falla():
    with pytest.raises(ValueError):
        Devolucion(venta_id=77, fecha=datetime(2026, 6, 25, 11, 0), lineas=(),
                   total=Decimal("0"), total_impuestos=Decimal("0"),
                   reembolsos=(), estado="pendiente")


def test_venta_admite_estados_de_devolucion():
    from core.entidades import LineaVenta
    linea = LineaVenta(producto_id=1, descripcion="Gaseosa", cantidad_o_peso=Decimal("2"),
                       precio_unit=Decimal("3500"), impuesto=Decimal("1118"), subtotal=Decimal("7000"))
    for estado in ("devuelta_parcial", "devuelta"):
        v = Venta(fecha=datetime(2026, 6, 25, 10, 0), lineas=(linea,),
                  total=Decimal("7000"), total_impuestos=Decimal("1118"), estado=estado)
        assert v.estado == estado
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_entidades_devolucion.py -v`
Expected: FAIL con `ImportError: cannot import name 'Devolucion' from 'core.entidades'`.

- [ ] **Step 3: Extend `ESTADOS_VENTA` and append the entities**

En `src/core/entidades.py`, reemplazar la línea de `ESTADOS_VENTA` existente:

```python
ESTADOS_VENTA = ("pagada", "anulada", "devuelta_parcial", "devuelta")
```

Y añadir al final del archivo (las importaciones `dataclass`, `datetime`, `Decimal`, `CERO` y la clase `Pago` ya existen en el módulo):

```python
ESTADOS_DEVOLUCION = ("emitida",)


@dataclass(frozen=True)
class ItemDevolucion:
    """Input del cajero: qué línea y cuánto se devuelve. Lo demás lo deriva el dominio."""
    venta_linea_id: int
    cantidad_o_peso: Decimal

    def __post_init__(self) -> None:
        if self.cantidad_o_peso <= CERO:
            raise ValueError("cantidad_o_peso a devolver debe ser positiva")


@dataclass(frozen=True)
class LineaDevolucion:
    producto_id: int
    cantidad_o_peso: Decimal   # cuánto se devuelve de la línea (>0; unidad o kg)
    impuesto: Decimal          # IVA contenido devuelto (prorrateado)
    subtotal: Decimal          # dinero devuelto por esta línea (IVA incluido)
    venta_linea_id: int | None = None
    devolucion_id: int | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        if self.subtotal < CERO or self.impuesto < CERO:
            raise ValueError("valores monetarios de LineaDevolucion deben ser no negativos")
        if self.cantidad_o_peso <= CERO:
            raise ValueError("cantidad_o_peso debe ser positiva")


@dataclass(frozen=True)
class Devolucion:
    venta_id: int
    fecha: datetime
    lineas: tuple[LineaDevolucion, ...]
    total: Decimal             # Σ subtotales devueltos = dinero a reembolsar
    total_impuestos: Decimal
    reembolsos: tuple[Pago, ...]   # salida de dinero por medio (reusa Pago; monto>0)
    caja_sesion_id: int | None = None   # sesión donde SALE el dinero (la abierta hoy)
    usuario_id: int | None = None
    estado: str = "emitida"
    id: int | None = None

    def __post_init__(self) -> None:
        if self.estado not in ESTADOS_DEVOLUCION:
            raise ValueError(f"estado de devolución inválido: {self.estado!r}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_entidades_devolucion.py -v`
Expected: PASS (6 passed).

- [ ] **Step 5: Run the existing suite to confirm no regression**

Run: `pytest tests/core/test_entidades_venta.py tests/core/test_anulacion.py -v`
Expected: PASS (los estados nuevos son aditivos; `Venta`/`anulación` intactos).

- [ ] **Step 6: Commit**

```bash
git add src/core/entidades.py tests/core/test_entidades_devolucion.py
git commit -m "feat(core): entidades de devolucion (Item/Linea/Devolucion) y estados de venta"
```

---

### Task E6.2: Funciones puras de devolución (`construir_lineas_devolucion`, `entradas_de_devolucion`)

**Files:**
- Modify: `src/core/servicio_venta.py`
- Test: `tests/core/test_devolucion.py`

**Interfaces:**
- Consumes: `Venta`, `LineaVenta`, `ItemDevolucion`, `LineaDevolucion`, `Devolucion`, `MovimientoInventario` (E6.1/E1.1); `Decimal`, `ROUND_HALF_UP`.
- Produces (en `core.servicio_venta`):
  - Excepciones `LineaNoEncontrada(ValueError)`, `CantidadDevueltaExcede(ValueError)`.
  - `construir_lineas_devolucion(venta: Venta, items: list[ItemDevolucion], ya_devuelto: dict[int, Decimal]) -> list[LineaDevolucion]` — por cada item: localiza su `LineaVenta` (por `venta_linea_id == LineaVenta.id`; `LineaNoEncontrada` si no existe), valida `cantidad ≤ vendida − ya_devuelto[id]` (`CantidadDevueltaExcede` si la supera), y prorratea `subtotal`/`impuesto` de la línea original con `ratio = cantidad / linea.cantidad_o_peso`, cuantizado a peso entero (`ROUND_HALF_UP`).
  - `entradas_de_devolucion(dev: Devolucion) -> list[MovimientoInventario]` — una `entrada` por línea: `cantidad = cantidad_o_peso`, `fecha = dev.fecha`, `ref = f"devolucion:{dev.id}"`.
  - `_todo_devuelto(venta: Venta, ya_devuelto: dict[int, Decimal], lineas_dev: list[LineaDevolucion]) -> bool` — `True` si, sumando esta devolución a lo ya devuelto, **toda** línea de la venta queda completa.

- [ ] **Step 1: Write the failing test**

```python
# tests/core/test_devolucion.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_devolucion.py -v`
Expected: FAIL con `ImportError: cannot import name 'construir_lineas_devolucion' from 'core.servicio_venta'`.

- [ ] **Step 3: Add the pure functions**

En `src/core/servicio_venta.py`, ampliar el import de `decimal` (arriba del módulo):

```python
from decimal import Decimal, ROUND_HALF_UP
```

Ampliar el import de `core.entidades` para incluir las entidades nuevas:

```python
from core.entidades import (
    Devolucion, ItemDevolucion, LineaDevolucion, LineaVenta, MovimientoInventario, Pago, Venta,
)
```

Y añadir al final del archivo:

```python
_PESO = Decimal("1")  # cuantización a peso colombiano entero


class LineaNoEncontrada(ValueError):
    pass


class CantidadDevueltaExcede(ValueError):
    pass


def _prorratear(valor: Decimal, ratio: Decimal) -> Decimal:
    return (valor * ratio).quantize(_PESO, rounding=ROUND_HALF_UP)


def construir_lineas_devolucion(
    venta: Venta, items: list[ItemDevolucion], ya_devuelto: dict[int, Decimal],
) -> list[LineaDevolucion]:
    """Valida cada item contra (vendido − ya_devuelto) y prorratea desde la línea original."""
    por_linea = {linea.id: linea for linea in venta.lineas}
    resultado: list[LineaDevolucion] = []
    for item in items:
        linea = por_linea.get(item.venta_linea_id)
        if linea is None:
            raise LineaNoEncontrada(
                f"la línea {item.venta_linea_id} no pertenece a la venta {venta.id}")
        remanente = linea.cantidad_o_peso - ya_devuelto.get(item.venta_linea_id, CERO)
        if item.cantidad_o_peso > remanente:
            raise CantidadDevueltaExcede(
                f"línea {item.venta_linea_id}: se devuelve {item.cantidad_o_peso} de {remanente}")
        ratio = item.cantidad_o_peso / linea.cantidad_o_peso
        resultado.append(LineaDevolucion(
            producto_id=linea.producto_id,
            cantidad_o_peso=item.cantidad_o_peso,
            impuesto=_prorratear(linea.impuesto, ratio),
            subtotal=_prorratear(linea.subtotal, ratio),
            venta_linea_id=linea.id,
        ))
    return resultado


def entradas_de_devolucion(dev: Devolucion) -> list[MovimientoInventario]:
    return [
        MovimientoInventario(
            producto_id=linea.producto_id,
            tipo="entrada",
            cantidad=linea.cantidad_o_peso,
            fecha=dev.fecha,
            ref=f"devolucion:{dev.id}",
        )
        for linea in dev.lineas
    ]


def _todo_devuelto(venta: Venta, ya_devuelto: dict[int, Decimal],
                   lineas_dev: list[LineaDevolucion]) -> bool:
    acumulado = dict(ya_devuelto)
    for linea in lineas_dev:
        acumulado[linea.venta_linea_id] = (
            acumulado.get(linea.venta_linea_id, CERO) + linea.cantidad_o_peso)
    return all(acumulado.get(linea.id, CERO) == linea.cantidad_o_peso for linea in venta.lineas)
```

> Nota: `Pago` ya estaba importado en este módulo (lo usa `ServicioRegistroVenta`); el import ampliado solo añade `Devolucion`, `ItemDevolucion`, `LineaDevolucion`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_devolucion.py -v`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add src/core/servicio_venta.py tests/core/test_devolucion.py
git commit -m "feat(core): funciones puras de devolucion (prorrateo + entradas de inventario)"
```

---

### Task E6.3: Puertos + `ServicioDevolucion`

**Files:**
- Modify: `src/core/puertos.py`
- Modify: `src/core/servicio_venta.py`
- Test: `tests/core/test_servicio_devolucion.py`

**Interfaces:**
- Consumes: `construir_lineas_devolucion`, `entradas_de_devolucion`, `_todo_devuelto` (E6.2); `VentaNoEncontrada` (E3.b, ya en el módulo); `Devolucion`, `ItemDevolucion`, `Pago`, `Venta` (E6.1).
- Produces (puertos en `core.puertos`):
  - `RepositorioVentas.marcar_estado(venta_id: int, estado: str) -> None` (añadido al `Protocol`; `anular` se conserva).
  - `RepositorioDevoluciones`: `guardar(devolucion: Devolucion) -> Devolucion`, `por_id(id: int) -> Devolucion | None`, `de_venta(venta_id: int) -> list[Devolucion]`, `devuelto_por_linea(venta_id: int) -> dict[int, Decimal]`.
- Produces (servicio en `core.servicio_venta`):
  - `VentaNoDevolvible(ValueError)`, `ReembolsoDescuadrado(ValueError)`.
  - `ServicioDevolucion(ventas: RepositorioVentas, devoluciones: RepositorioDevoluciones, inventario: RepositorioInventario)`:
    - `devolver(self, venta_id: int, items: list[ItemDevolucion], reembolsos: list[Pago], *, fecha: datetime, caja_sesion_id: int | None = None, usuario_id: int | None = None) -> Devolucion`.

- [ ] **Step 1: Write the failing test**

```python
# tests/core/test_servicio_devolucion.py
from dataclasses import replace
from datetime import datetime
from decimal import Decimal

import pytest

from core.entidades import Devolucion, ItemDevolucion, LineaVenta, Pago, Venta
from core.servicio_venta import (
    ReembolsoDescuadrado, ServicioDevolucion, VentaNoDevolvible, VentaNoEncontrada,
)


def _venta(estado="pagada") -> Venta:
    lineas = (
        LineaVenta(producto_id=1, descripcion="Gaseosa", cantidad_o_peso=Decimal("2"),
                   precio_unit=Decimal("3500"), impuesto=Decimal("1118"),
                   subtotal=Decimal("7000"), venta_id=77, id=10),
    )
    return Venta(fecha=datetime(2026, 6, 25, 10, 0), lineas=lineas,
                 total=Decimal("7000"), total_impuestos=Decimal("1118"), estado=estado, id=77)


class _FakeVentas:
    def __init__(self, venta):
        self._venta = venta
        self.estado_marcado = None
    def por_id(self, id):
        return self._venta if self._venta and self._venta.id == id else None
    def marcar_estado(self, venta_id, estado):
        self.estado_marcado = (venta_id, estado)
        self._venta = replace(self._venta, estado=estado)


class _FakeDevoluciones:
    def __init__(self, ya_devuelto=None):
        self._ya = ya_devuelto or {}
        self.guardada = None
    def guardar(self, devolucion):
        self.guardada = replace(devolucion, id=5)
        return self.guardada
    def devuelto_por_linea(self, venta_id):
        return dict(self._ya)


class _FakeInventario:
    def __init__(self):
        self.movimientos = []
    def registrar(self, m):
        self.movimientos.append(m)
        return m


def test_devolucion_parcial_marca_parcial_y_repone():
    ventas, devs, inv = _FakeVentas(_venta()), _FakeDevoluciones(), _FakeInventario()
    dev = ServicioDevolucion(ventas, devs, inv).devolver(
        77, [ItemDevolucion(venta_linea_id=10, cantidad_o_peso=Decimal("1"))],
        [Pago(medio_pago_id=1, monto=Decimal("3500"))],
        fecha=datetime(2026, 6, 25, 11, 0), caja_sesion_id=1)
    assert dev.id == 5
    assert dev.total == Decimal("3500")
    assert ventas.estado_marcado == (77, "devuelta_parcial")
    assert [m.tipo for m in inv.movimientos] == ["entrada"]
    assert inv.movimientos[0].cantidad == Decimal("1")
    assert inv.movimientos[0].ref == "devolucion:5"


def test_devolucion_total_marca_devuelta():
    ventas, devs, inv = _FakeVentas(_venta()), _FakeDevoluciones(), _FakeInventario()
    ServicioDevolucion(ventas, devs, inv).devolver(
        77, [ItemDevolucion(venta_linea_id=10, cantidad_o_peso=Decimal("2"))],
        [Pago(medio_pago_id=1, monto=Decimal("7000"))],
        fecha=datetime(2026, 6, 25, 11, 0), caja_sesion_id=1)
    assert ventas.estado_marcado == (77, "devuelta")


def test_reembolso_descuadrado_falla_y_no_repone():
    ventas, devs, inv = _FakeVentas(_venta()), _FakeDevoluciones(), _FakeInventario()
    with pytest.raises(ReembolsoDescuadrado):
        ServicioDevolucion(ventas, devs, inv).devolver(
            77, [ItemDevolucion(venta_linea_id=10, cantidad_o_peso=Decimal("1"))],
            [Pago(medio_pago_id=1, monto=Decimal("3000"))],   # debería ser 3500
            fecha=datetime(2026, 6, 25, 11, 0))
    assert inv.movimientos == []
    assert ventas.estado_marcado is None


def test_devolver_venta_inexistente_falla():
    with pytest.raises(VentaNoEncontrada):
        ServicioDevolucion(_FakeVentas(None), _FakeDevoluciones(), _FakeInventario()).devolver(
            999, [], [], fecha=datetime(2026, 6, 25, 11, 0))


def test_devolver_venta_anulada_falla():
    ventas = _FakeVentas(_venta(estado="anulada"))
    with pytest.raises(VentaNoDevolvible):
        ServicioDevolucion(ventas, _FakeDevoluciones(), _FakeInventario()).devolver(
            77, [ItemDevolucion(venta_linea_id=10, cantidad_o_peso=Decimal("1"))],
            [Pago(medio_pago_id=1, monto=Decimal("3500"))],
            fecha=datetime(2026, 6, 25, 11, 0))


def test_devolver_venta_ya_devuelta_falla():
    ventas = _FakeVentas(_venta(estado="devuelta"))
    with pytest.raises(VentaNoDevolvible):
        ServicioDevolucion(ventas, _FakeDevoluciones(), _FakeInventario()).devolver(
            77, [ItemDevolucion(venta_linea_id=10, cantidad_o_peso=Decimal("1"))],
            [Pago(medio_pago_id=1, monto=Decimal("3500"))],
            fecha=datetime(2026, 6, 25, 11, 0))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_servicio_devolucion.py -v`
Expected: FAIL con `ImportError: cannot import name 'ServicioDevolucion' from 'core.servicio_venta'`.

- [ ] **Step 3a: Extend the ports**

En `src/core/puertos.py`, añadir `Devolucion` al import de `core.entidades`:

```python
from core.entidades import (
    CajaSesion, Categoria, Cliente, Devolucion, Impuesto, MedioPago,
    MovimientoInventario, Pago, Producto, Venta,
)
```

Reemplazar el `RepositorioVentas` existente por (añade `marcar_estado`, conserva `anular`):

```python
class RepositorioVentas(Protocol):
    def guardar(self, venta: Venta, pagos: list[Pago]) -> Venta: ...
    def por_id(self, id: int) -> Venta | None: ...
    def pagos_de(self, venta_id: int) -> list[Pago]: ...
    def anular(self, venta_id: int) -> None: ...
    def marcar_estado(self, venta_id: int, estado: str) -> None: ...
    def totales_por_medio(self, caja_sesion_id: int) -> dict[int, Decimal]: ...
```

Y añadir al final del archivo:

```python
class RepositorioDevoluciones(Protocol):
    def guardar(self, devolucion: Devolucion) -> Devolucion: ...
    def por_id(self, id: int) -> Devolucion | None: ...
    def de_venta(self, venta_id: int) -> list[Devolucion]: ...
    def devuelto_por_linea(self, venta_id: int) -> dict[int, Decimal]: ...  # venta_linea_id -> cant.
```

- [ ] **Step 3b: Add the service**

En `src/core/servicio_venta.py`, ampliar el import de `core.puertos`:

```python
from core.puertos import (
    RepositorioDevoluciones, RepositorioImpuestos, RepositorioInventario,
    RepositorioProductos, RepositorioVentas,
)
```

Y añadir al final del archivo (`datetime` ya está importado en el módulo):

```python
class VentaNoDevolvible(ValueError):
    pass


class ReembolsoDescuadrado(ValueError):
    pass


class ServicioDevolucion:
    """Devuelve líneas de una venta: repone inventario y reembolsa dinero. Solo puertos."""

    def __init__(self, ventas: RepositorioVentas, devoluciones: RepositorioDevoluciones,
                 inventario: RepositorioInventario) -> None:
        self._ventas = ventas
        self._devoluciones = devoluciones
        self._inventario = inventario

    def devolver(self, venta_id: int, items: list[ItemDevolucion], reembolsos: list[Pago], *,
                 fecha: datetime, caja_sesion_id: int | None = None,
                 usuario_id: int | None = None) -> Devolucion:
        venta = self._ventas.por_id(venta_id)
        if venta is None:
            raise VentaNoEncontrada(f"venta inexistente: {venta_id}")
        if venta.estado in ("anulada", "devuelta"):
            raise VentaNoDevolvible(f"venta {venta_id} en estado {venta.estado!r}")
        ya_devuelto = self._devoluciones.devuelto_por_linea(venta_id)
        lineas = construir_lineas_devolucion(venta, items, ya_devuelto)
        total = sum((l.subtotal for l in lineas), CERO)
        total_impuestos = sum((l.impuesto for l in lineas), CERO)
        if sum((r.monto for r in reembolsos), CERO) != total:
            raise ReembolsoDescuadrado(
                f"reembolso {sum((r.monto for r in reembolsos), CERO)} ≠ devuelto {total}")
        dev = Devolucion(
            venta_id=venta_id, fecha=fecha, lineas=tuple(lineas),
            total=total, total_impuestos=total_impuestos, reembolsos=tuple(reembolsos),
            caja_sesion_id=caja_sesion_id, usuario_id=usuario_id)
        guardada = self._devoluciones.guardar(dev)
        for movimiento in entradas_de_devolucion(guardada):
            self._inventario.registrar(movimiento)
        nuevo_estado = "devuelta" if _todo_devuelto(venta, ya_devuelto, lineas) else "devuelta_parcial"
        self._ventas.marcar_estado(venta_id, nuevo_estado)
        return guardada
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_servicio_devolucion.py -v`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add src/core/puertos.py src/core/servicio_venta.py tests/core/test_servicio_devolucion.py
git commit -m "feat(core): puerto RepositorioDevoluciones y ServicioDevolucion (reembolso cuadrado)"
```

---

### Task E6.4: Migración + adaptador SQLite + neteo de arqueo

**Files:**
- Create: `scripts/migraciones/004_devoluciones.sql`
- Modify: `src/ventas/repositorio_sqlite.py`
- Test: `tests/ventas/test_repositorio_devoluciones.py`

**Interfaces:**
- Consumes: `Devolucion`, `LineaDevolucion`, `Pago` (E6.1); `sqlite3`, `replace`, `datetime`, `Decimal` (ya en el módulo); fixture `conn` (aplica todas las migraciones); `RepositorioCategoriasSQLite`, `RepositorioImpuestosSQLite`, `RepositorioProductosSQLite` (E2.3); `RepositorioVentasSQLite`, `RepositorioCajaSesionesSQLite` (E1.5/E3.4).
- Produces (en `ventas.repositorio_sqlite`):
  - `RepositorioDevolucionesSQLite(conn)` — `guardar` (cabecera + líneas + reembolsos), `por_id`, `de_venta`, `devuelto_por_linea`.
  - `RepositorioVentasSQLite.marcar_estado(venta_id, estado)`; `anular` reimplementado como `marcar_estado(id, "anulada")`.
  - `RepositorioVentasSQLite.totales_por_medio(caja_sesion_id)` reescrito: ingresos (pagos de ventas `estado != 'anulada'`) **menos** egresos (reembolsos de devoluciones de **esa** sesión).

- [ ] **Step 1: Write the failing tests**

```python
# tests/ventas/test_repositorio_devoluciones.py
from datetime import datetime
from decimal import Decimal

from core.entidades import (
    CajaSesion, Categoria, Devolucion, Impuesto, LineaDevolucion, LineaVenta, Pago, Producto, Venta,
)
from inventario.repositorio_sqlite import (
    RepositorioCategoriasSQLite,
    RepositorioImpuestosSQLite,
    RepositorioProductosSQLite,
)
from ventas.repositorio_sqlite import (
    RepositorioCajaSesionesSQLite,
    RepositorioDevolucionesSQLite,
    RepositorioVentasSQLite,
)


def _seed_producto(conn):
    cat = RepositorioCategoriasSQLite(conn).guardar(Categoria(nombre="Bebidas"))
    imp = RepositorioImpuestosSQLite(conn).guardar(Impuesto(nombre="IVA", tarifa=Decimal("0.19")))
    return RepositorioProductosSQLite(conn).guardar(
        Producto(codigo_barras="B", nombre="Gaseosa", precio=Decimal("3500"),
                 categoria_id=cat.id, impuesto_id=imp.id))


def _venta_guardada(conn, sesion_id, producto_id, pagos):
    linea = LineaVenta(producto_id=producto_id, descripcion="Gaseosa",
                       cantidad_o_peso=Decimal("2"), precio_unit=Decimal("3500"),
                       impuesto=Decimal("1118"), subtotal=Decimal("7000"))
    venta = Venta(fecha=datetime(2026, 6, 25, 10, 0), lineas=(linea,),
                  total=Decimal("7000"), total_impuestos=Decimal("1118"), caja_sesion_id=sesion_id)
    return RepositorioVentasSQLite(conn).guardar(venta, pagos)


def _devolucion(conn, venta_id, venta_linea_id, producto_id, sesion_id, cantidad, monto):
    linea = LineaDevolucion(producto_id=producto_id, cantidad_o_peso=cantidad,
                            impuesto=Decimal("0"), subtotal=monto, venta_linea_id=venta_linea_id)
    dev = Devolucion(venta_id=venta_id, fecha=datetime(2026, 6, 25, 12, 0), lineas=(linea,),
                     total=monto, total_impuestos=Decimal("0"),
                     reembolsos=(Pago(medio_pago_id=1, monto=monto),), caja_sesion_id=sesion_id)
    return RepositorioDevolucionesSQLite(conn).guardar(dev)


def test_guardar_y_leer_devolucion(conn):
    prod = _seed_producto(conn)
    sesion = RepositorioCajaSesionesSQLite(conn).abrir(
        CajaSesion(apertura_fecha=datetime(2026, 6, 25, 9, 0), monto_inicial=Decimal("0")))
    venta = _venta_guardada(conn, sesion.id, prod.id, [Pago(medio_pago_id=1, monto=Decimal("7000"))])
    linea_id = RepositorioVentasSQLite(conn).por_id(venta.id).lineas[0].id

    guardada = _devolucion(conn, venta.id, linea_id, prod.id, sesion.id, Decimal("1"), Decimal("3500"))
    assert guardada.id is not None

    leida = RepositorioDevolucionesSQLite(conn).por_id(guardada.id)
    assert leida.venta_id == venta.id
    assert leida.total == Decimal("3500")
    assert leida.lineas[0].cantidad_o_peso == Decimal("1")
    assert leida.reembolsos[0].monto == Decimal("3500")
    assert leida.caja_sesion_id == sesion.id


def test_de_venta_y_devuelto_por_linea(conn):
    prod = _seed_producto(conn)
    sesion = RepositorioCajaSesionesSQLite(conn).abrir(
        CajaSesion(apertura_fecha=datetime(2026, 6, 25, 9, 0), monto_inicial=Decimal("0")))
    venta = _venta_guardada(conn, sesion.id, prod.id, [Pago(medio_pago_id=1, monto=Decimal("7000"))])
    linea_id = RepositorioVentasSQLite(conn).por_id(venta.id).lineas[0].id
    _devolucion(conn, venta.id, linea_id, prod.id, sesion.id, Decimal("1"), Decimal("3500"))

    repo = RepositorioDevolucionesSQLite(conn)
    assert len(repo.de_venta(venta.id)) == 1
    assert repo.devuelto_por_linea(venta.id) == {linea_id: Decimal("1")}


def test_totales_por_medio_netea_reembolso_misma_sesion(conn):
    prod = _seed_producto(conn)
    sesion = RepositorioCajaSesionesSQLite(conn).abrir(
        CajaSesion(apertura_fecha=datetime(2026, 6, 25, 9, 0), monto_inicial=Decimal("0")))
    venta = _venta_guardada(conn, sesion.id, prod.id, [Pago(medio_pago_id=1, monto=Decimal("7000"))])
    linea_id = RepositorioVentasSQLite(conn).por_id(venta.id).lineas[0].id
    _devolucion(conn, venta.id, linea_id, prod.id, sesion.id, Decimal("1"), Decimal("3500"))

    # ingreso 7000 efectivo - reembolso 3500 efectivo = 3500 neto
    assert RepositorioVentasSQLite(conn).totales_por_medio(sesion.id) == {1: Decimal("3500")}


def test_reembolso_afecta_la_sesion_del_reembolso_no_la_de_la_venta(conn):
    prod = _seed_producto(conn)
    sesiones = RepositorioCajaSesionesSQLite(conn)
    s1 = sesiones.abrir(CajaSesion(apertura_fecha=datetime(2026, 6, 25, 9, 0),
                                   monto_inicial=Decimal("0")))
    venta = _venta_guardada(conn, s1.id, prod.id, [Pago(medio_pago_id=1, monto=Decimal("7000"))])
    linea_id = RepositorioVentasSQLite(conn).por_id(venta.id).lineas[0].id
    # se cierra s1 y se abre s2; el reembolso ocurre en s2
    sesiones.cerrar(__import__("dataclasses").replace(
        s1, cierre_fecha=datetime(2026, 6, 25, 20, 0), monto_contado=Decimal("7000"), estado="cerrada"))
    s2 = sesiones.abrir(CajaSesion(apertura_fecha=datetime(2026, 6, 26, 9, 0),
                                   monto_inicial=Decimal("0")))
    _devolucion(conn, venta.id, linea_id, prod.id, s2.id, Decimal("1"), Decimal("3500"))

    ventas = RepositorioVentasSQLite(conn)
    assert ventas.totales_por_medio(s1.id) == {1: Decimal("7000")}   # venta intacta en s1
    assert ventas.totales_por_medio(s2.id) == {1: Decimal("-3500")}  # egreso en s2


def test_marcar_estado_actualiza_la_venta(conn):
    prod = _seed_producto(conn)
    sesion = RepositorioCajaSesionesSQLite(conn).abrir(
        CajaSesion(apertura_fecha=datetime(2026, 6, 25, 9, 0), monto_inicial=Decimal("0")))
    venta = _venta_guardada(conn, sesion.id, prod.id, [Pago(medio_pago_id=1, monto=Decimal("7000"))])
    repo = RepositorioVentasSQLite(conn)
    repo.marcar_estado(venta.id, "devuelta_parcial")
    assert repo.por_id(venta.id).estado == "devuelta_parcial"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/ventas/test_repositorio_devoluciones.py -v`
Expected: FAIL con `ImportError: cannot import name 'RepositorioDevolucionesSQLite' from 'ventas.repositorio_sqlite'`.

- [ ] **Step 3a: Create the migration**

Crear `scripts/migraciones/004_devoluciones.sql`:

```sql
-- scripts/migraciones/004_devoluciones.sql
-- Devoluciones con reembolso (E6). La venta original queda inmutable; aquí vive el documento
-- de devolución (cabecera + líneas devueltas + reembolsos por medio de pago).

CREATE TABLE IF NOT EXISTS devoluciones (
    id              INTEGER PRIMARY KEY,
    venta_id        INTEGER NOT NULL REFERENCES ventas(id),
    fecha           TEXT NOT NULL,                        -- ISO-8601
    caja_sesion_id  INTEGER REFERENCES caja_sesiones(id), -- sesión del reembolso (NULLABLE)
    usuario_id      INTEGER REFERENCES usuarios(id),
    total           DECIMAL NOT NULL,
    total_impuestos DECIMAL NOT NULL,
    estado          TEXT NOT NULL DEFAULT 'emitida',
    cufe_nota       TEXT                                  -- reservado DIAN (nota crédito), sin uso fiscal hoy
);

CREATE TABLE IF NOT EXISTS devolucion_lineas (
    id              INTEGER PRIMARY KEY,
    devolucion_id   INTEGER NOT NULL REFERENCES devoluciones(id),
    venta_linea_id  INTEGER REFERENCES venta_lineas(id),
    producto_id     INTEGER NOT NULL REFERENCES productos(id),
    cantidad_o_peso DECIMAL NOT NULL,
    impuesto        DECIMAL NOT NULL,
    subtotal        DECIMAL NOT NULL
);

CREATE TABLE IF NOT EXISTS devolucion_reembolsos (
    id            INTEGER PRIMARY KEY,
    devolucion_id INTEGER NOT NULL REFERENCES devoluciones(id),
    medio_pago_id INTEGER NOT NULL REFERENCES medios_pago(id),
    monto         DECIMAL NOT NULL,
    referencia    TEXT
);
```

- [ ] **Step 3b: Rewrite `totales_por_medio` and add `marcar_estado`**

En `src/ventas/repositorio_sqlite.py`, añadir `Devolucion` y `LineaDevolucion` al import de `core.entidades`:

```python
from core.entidades import (
    CajaSesion, Cliente, Devolucion, LineaDevolucion, LineaVenta, MedioPago, Pago, Venta,
)
```

Reemplazar el método `anular` existente de `RepositorioVentasSQLite` por (conserva `anular`, ahora vía `marcar_estado`):

```python
    def marcar_estado(self, venta_id: int, estado: str) -> None:
        self._conn.execute(
            "UPDATE ventas SET estado = ? WHERE id = ?", (estado, venta_id))
        self._conn.commit()

    def anular(self, venta_id: int) -> None:
        self.marcar_estado(venta_id, "anulada")
```

Reemplazar el método `totales_por_medio` existente por (ingresos − egresos de reembolso de la sesión):

```python
    def totales_por_medio(self, caja_sesion_id: int) -> dict[int, Decimal]:
        ingresos = self._conn.execute(
            "SELECT p.medio_pago_id AS medio_pago_id, p.monto AS monto "
            "FROM pagos p JOIN ventas v ON v.id = p.venta_id "
            "WHERE v.caja_sesion_id = ? AND v.estado != 'anulada'",
            (caja_sesion_id,)).fetchall()
        egresos = self._conn.execute(
            "SELECT r.medio_pago_id AS medio_pago_id, r.monto AS monto "
            "FROM devolucion_reembolsos r JOIN devoluciones d ON d.id = r.devolucion_id "
            "WHERE d.caja_sesion_id = ?",
            (caja_sesion_id,)).fetchall()
        totales: dict[int, Decimal] = {}
        for f in ingresos:
            totales[f["medio_pago_id"]] = totales.get(f["medio_pago_id"], Decimal("0")) + f["monto"]
        for f in egresos:
            totales[f["medio_pago_id"]] = totales.get(f["medio_pago_id"], Decimal("0")) - f["monto"]
        return totales
```

- [ ] **Step 3c: Add the devoluciones adapter**

Añadir al final de `src/ventas/repositorio_sqlite.py`:

```python
def _fila_a_linea_dev(f: sqlite3.Row) -> LineaDevolucion:
    return LineaDevolucion(
        producto_id=f["producto_id"],
        cantidad_o_peso=f["cantidad_o_peso"],
        impuesto=f["impuesto"],
        subtotal=f["subtotal"],
        venta_linea_id=f["venta_linea_id"],
        devolucion_id=f["devolucion_id"],
        id=f["id"],
    )


class RepositorioDevolucionesSQLite:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def guardar(self, d: Devolucion) -> Devolucion:
        cur = self._conn.execute(
            "INSERT INTO devoluciones "
            "(venta_id, fecha, caja_sesion_id, usuario_id, total, total_impuestos, estado) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (d.venta_id, d.fecha.isoformat(), d.caja_sesion_id, d.usuario_id,
             d.total, d.total_impuestos, d.estado))
        dev_id = cur.lastrowid
        for linea in d.lineas:
            self._conn.execute(
                "INSERT INTO devolucion_lineas "
                "(devolucion_id, venta_linea_id, producto_id, cantidad_o_peso, impuesto, subtotal) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (dev_id, linea.venta_linea_id, linea.producto_id, linea.cantidad_o_peso,
                 linea.impuesto, linea.subtotal))
        for r in d.reembolsos:
            self._conn.execute(
                "INSERT INTO devolucion_reembolsos (devolucion_id, medio_pago_id, monto, referencia) "
                "VALUES (?, ?, ?, ?)",
                (dev_id, r.medio_pago_id, r.monto, r.referencia))
        self._conn.commit()
        return replace(d, id=dev_id)

    def por_id(self, id: int) -> Devolucion | None:
        fd = self._conn.execute("SELECT * FROM devoluciones WHERE id = ?", (id,)).fetchone()
        if fd is None:
            return None
        lineas = self._conn.execute(
            "SELECT * FROM devolucion_lineas WHERE devolucion_id = ? ORDER BY id", (id,)).fetchall()
        reembolsos = self._conn.execute(
            "SELECT * FROM devolucion_reembolsos WHERE devolucion_id = ? ORDER BY id", (id,)).fetchall()
        return Devolucion(
            venta_id=fd["venta_id"],
            fecha=datetime.fromisoformat(fd["fecha"]),
            lineas=tuple(_fila_a_linea_dev(f) for f in lineas),
            total=fd["total"],
            total_impuestos=fd["total_impuestos"],
            reembolsos=tuple(Pago(medio_pago_id=r["medio_pago_id"], monto=r["monto"],
                                  referencia=r["referencia"], id=r["id"]) for r in reembolsos),
            caja_sesion_id=fd["caja_sesion_id"],
            usuario_id=fd["usuario_id"],
            estado=fd["estado"],
            id=fd["id"],
        )

    def de_venta(self, venta_id: int) -> list[Devolucion]:
        ids = self._conn.execute(
            "SELECT id FROM devoluciones WHERE venta_id = ? ORDER BY id", (venta_id,)).fetchall()
        return [self.por_id(f["id"]) for f in ids]

    def devuelto_por_linea(self, venta_id: int) -> dict[int, Decimal]:
        filas = self._conn.execute(
            "SELECT dl.venta_linea_id AS venta_linea_id, dl.cantidad_o_peso AS cantidad "
            "FROM devolucion_lineas dl JOIN devoluciones d ON d.id = dl.devolucion_id "
            "WHERE d.venta_id = ?",
            (venta_id,)).fetchall()
        acum: dict[int, Decimal] = {}
        for f in filas:
            acum[f["venta_linea_id"]] = acum.get(f["venta_linea_id"], Decimal("0")) + f["cantidad"]
        return acum
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/ventas/test_repositorio_devoluciones.py -v`
Expected: PASS (5 passed).

- [ ] **Step 5: Run E3/E3.b persistence tests to confirm no regression**

Run: `pytest tests/ventas/test_repositorio_caja.py tests/ventas/test_flujo_cierre_caja.py tests/ventas/test_flujo_anulacion.py -v`
Expected: PASS (`totales_por_medio` sigue excluyendo `anulada` y, sin devoluciones, los egresos son vacíos).

- [ ] **Step 6: Commit**

```bash
git add scripts/migraciones/004_devoluciones.sql src/ventas/repositorio_sqlite.py tests/ventas/test_repositorio_devoluciones.py
git commit -m "feat(ventas): adaptador SQLite de devoluciones + neteo de reembolsos en el arqueo"
```

---

### Task E6.5: Flujo crítico — devolución con reembolso de extremo a extremo

> Cierra el flujo crítico #3 de `testing-pos` ("devolución/anulación") con repos SQLite reales: vender, devolver parcial (reponiendo stock, reembolsando efectivo y reduciendo el arqueo), luego devolver el resto hasta dejar la venta `devuelta`.

**Files:**
- Test: `tests/ventas/test_flujo_devolucion.py`

**Interfaces:**
- Consumes: `RepositorioCategoriasSQLite`, `RepositorioImpuestosSQLite`, `RepositorioProductosSQLite`, `RepositorioInventarioSQLite` (E2.3); `RepositorioVentasSQLite`, `RepositorioCajaSesionesSQLite`, `RepositorioDevolucionesSQLite` (E1.5/E3.4/E6.4); `ServicioVenta`, `ServicioRegistroVenta`, `ServicioDevolucion` (E1.3/E3.5/E6.3); `ServicioCaja` (E3.3); `ItemDevolucion`, `Pago` (E6.1); fixture `conn` (E1.4).

- [ ] **Step 1: Write the test**

```python
# tests/ventas/test_flujo_devolucion.py
from datetime import datetime
from decimal import Decimal

from core.entidades import Categoria, Impuesto, ItemDevolucion, MovimientoInventario, Pago, Producto
from core.servicio_caja import ServicioCaja
from core.servicio_venta import ServicioDevolucion, ServicioRegistroVenta, ServicioVenta
from inventario.repositorio_sqlite import (
    RepositorioCategoriasSQLite,
    RepositorioImpuestosSQLite,
    RepositorioInventarioSQLite,
    RepositorioProductosSQLite,
)
from ventas.repositorio_sqlite import (
    RepositorioCajaSesionesSQLite,
    RepositorioDevolucionesSQLite,
    RepositorioVentasSQLite,
)


def _seed(conn):
    cat = RepositorioCategoriasSQLite(conn).guardar(Categoria(nombre="Bebidas"))
    iva = RepositorioImpuestosSQLite(conn).guardar(Impuesto(nombre="IVA", tarifa=Decimal("0.19")))
    gaseosa = RepositorioProductosSQLite(conn).guardar(
        Producto(codigo_barras="B", nombre="Gaseosa", precio=Decimal("3500"),
                 categoria_id=cat.id, impuesto_id=iva.id))
    inv = RepositorioInventarioSQLite(conn)
    inv.registrar(MovimientoInventario(producto_id=gaseosa.id, tipo="entrada",
                                       cantidad=Decimal("10"), fecha=datetime(2026, 6, 25, 8, 0)))
    return gaseosa, inv


def test_devolucion_parcial_y_luego_total(conn):
    gaseosa, inv = _seed(conn)
    ventas = RepositorioVentasSQLite(conn)
    devoluciones = RepositorioDevolucionesSQLite(conn)
    caja = ServicioCaja(RepositorioCajaSesionesSQLite(conn), ventas)
    registro = ServicioRegistroVenta(ventas, inv)
    servicio_dev = ServicioDevolucion(ventas, devoluciones, inv)

    sesion = caja.abrir(fecha=datetime(2026, 6, 25, 9, 0), monto_inicial=Decimal("100000"))

    # Vender 2 gaseosas en efectivo (subtotal 7000)
    s = ServicioVenta(RepositorioProductosSQLite(conn), RepositorioImpuestosSQLite(conn))
    s.agregar("B", cantidad=2)
    venta = s.confirmar(fecha=datetime(2026, 6, 25, 10, 0), caja_sesion_id=sesion.id)
    guardada = registro.registrar(venta, [Pago(medio_pago_id=1, monto=Decimal("7000"))])
    assert inv.stock_de(gaseosa.id) == Decimal("8")

    linea_id = ventas.por_id(guardada.id).lineas[0].id

    # Devolver 1 de 2 (reembolso 3500 efectivo)
    servicio_dev.devolver(
        guardada.id, [ItemDevolucion(venta_linea_id=linea_id, cantidad_o_peso=Decimal("1"))],
        [Pago(medio_pago_id=1, monto=Decimal("3500"))],
        fecha=datetime(2026, 6, 25, 11, 0), caja_sesion_id=sesion.id)

    assert inv.stock_de(gaseosa.id) == Decimal("9")                  # repuesto 1
    assert ventas.por_id(guardada.id).estado == "devuelta_parcial"
    arqueo_parcial = caja.arqueo(sesion.id, Decimal("103500"))
    assert arqueo_parcial.efectivo_ventas == Decimal("3500")        # 7000 - 3500 reembolsado
    assert arqueo_parcial.esperado == Decimal("103500")             # base 100000 + 3500
    assert arqueo_parcial.diferencia == Decimal("0")

    # Devolver el restante 1 (reembolso 3500 efectivo) -> venta devuelta
    servicio_dev.devolver(
        guardada.id, [ItemDevolucion(venta_linea_id=linea_id, cantidad_o_peso=Decimal("1"))],
        [Pago(medio_pago_id=1, monto=Decimal("3500"))],
        fecha=datetime(2026, 6, 25, 11, 30), caja_sesion_id=sesion.id)

    assert inv.stock_de(gaseosa.id) == Decimal("10")                # stock totalmente repuesto
    assert ventas.por_id(guardada.id).estado == "devuelta"
    assert len(devoluciones.de_venta(guardada.id)) == 2

    # Arqueo: efectivo neto de la venta = 0 (7000 cobrado - 7000 reembolsado)
    cerrada, arqueo = caja.cerrar(sesion_id=sesion.id, fecha=datetime(2026, 6, 25, 20, 0),
                                  monto_contado=Decimal("100000"))
    assert arqueo.efectivo_ventas == Decimal("0")
    assert arqueo.esperado == Decimal("100000")
    assert arqueo.diferencia == Decimal("0")
    assert cerrada.estado == "cerrada"
```

- [ ] **Step 2: Run the test**

Run: `pytest tests/ventas/test_flujo_devolucion.py -v`
Expected: PASS (1 passed).

- [ ] **Step 3: Run the full suite**

Run: `pytest -v`
Expected: PASS — la suite base (104 passed, 2 skipped) más los nuevos tests de E6 (~24 nuevos), sin regresiones. El smoke de Qt sigue pasando o saltándose según PySide6.

- [ ] **Step 4: Commit**

```bash
git add tests/ventas/test_flujo_devolucion.py
git commit -m "test(ventas): flujo critico de devolucion con reembolso y arqueo neto"
```

---

### Task E6.6: Housekeeping de documentación

**Files:**
- Modify: `docs/README-pos.md`

- [ ] **Step 1: Marcar E6 implementado**

En `docs/README-pos.md`, en la tabla "Estado actual", reemplazar la fila:

```markdown
| E6–E7 | Devoluciones (con dinero), reportes | pendiente |
```

por:

```markdown
| E6 | Devoluciones con reembolso: parcial/total, repone stock, reembolsa y netea el arqueo (sin UI Qt) | ✅ implementado |
| E7 | Reportes | pendiente |
```

Y actualizar la línea de la suite al conteo real reportado por `pytest` en E6.5, p. ej.:

```markdown
Suite: **128 passed, 2 skipped** (2026-06-25).
```

> Ajustar el número exacto al output de `pytest -v` del paso E6.5 Step 3.

- [ ] **Step 2: Commit**

```bash
git add docs/README-pos.md
git commit -m "docs: marca E6 (devoluciones con reembolso) implementado"
```

---

## Definición de "hecho" (E6)

- `pytest -v` en verde; sin SQL fuera de `src/inventario/` y `src/ventas/`; sin imports de Qt/SQLite/pyserial dentro de `src/core/`.
- Se puede devolver una venta `pagada` parcial (por línea/cantidad) o total: repone el stock de lo devuelto, registra el reembolso por medio de pago y exige que el reembolso cuadre con lo devuelto.
- El efectivo reembolsado **resta** del arqueo de la sesión en que se reembolsa (no de la sesión original de la venta), sin tocar `ServicioCaja`/`calcular_arqueo`.
- La venta original queda inmutable; su `estado` pasa a `devuelta_parcial`/`devuelta` según corresponda.
- E3/E3.b intactos: `anular` se conserva, `totales_por_medio` sigue excluyendo `anulada`.
- El flujo crítico #3 ("devolución/anulación") tiene test de integración verde.

## Self-Review (cobertura del spec E6)

| Requisito (spec) | Task |
|---|---|
| Documento `Devolucion` + `LineaDevolucion` (entidades) | E6.1 |
| `ItemDevolucion` (input del cajero) | E6.1 |
| Estados `devuelta_parcial`/`devuelta` en `Venta` | E6.1 |
| Devolución parcial por línea/cantidad (prorrateo desde la línea) | E6.2 |
| `entradas_de_devolucion` (reposición de inventario, `ref="devolucion:<id>"`) | E6.2 |
| Validación sobre-devolución (vendido − ya devuelto) | E6.2 (`construir_lineas_devolucion`) |
| Reembolso cuadrado (`Σ reembolsos == total`) | E6.3 (`ServicioDevolucion`) |
| Puerto `RepositorioDevoluciones` + `RepositorioVentas.marcar_estado` | E6.3 (puerto), E6.4 (adaptador) |
| Migración `004_devoluciones.sql` (+ columna reservada `cufe_nota`) | E6.4 |
| Reflejo en el arqueo (neteo de reembolsos por sesión del reembolso) | E6.4 (`totales_por_medio`) |
| Flujo crítico #3 con test de integración | E6.5 |
| Dinero/cantidades con `Decimal` exacto (sin `SUM()` de SQL) | Constraint global; E6.4 |
| `core` sin Qt/SQLite; servicios solo sobre puertos | Constraint global |

**Diferido a propósito (YAGNI / costura):**
- **UI Qt de devoluciones (`PantallaDevoluciones`):** el dominio queda completo y testeado; la pantalla (cáscara sobre `ServicioDevolucion`) entra como refinamiento de `src/caja/`, igual que la anulación de E3.b se quedó sin UI.
- **Nota crédito DIAN:** solo costura documentada en el spec (`EmisorDIAN.emitir_nota_credito` + armado en `core`). El único artefacto concreto en E6 es la columna reservada `devoluciones.cufe_nota`. Se cablea con el epic DIAN; no se añade un `Protocol` sin implementador.
- **Restringir el medio de reembolso al medio original** de pago: hoy libre; regla de negocio futura.
- **Bloquear devolución sin caja abierta:** coherente con E3.b (que permite anular con caja cerrada), el `core` no lo fuerza; el guard, si el negocio lo pide, va en el llamador/UI.
- **Atomicidad transaccional** (devolución + entradas + `marcar_estado` en una sola transacción): hoy cada repo hace `commit()` propio, aceptable para una caja offline de un cajón; envoltorio único = mismo refinamiento futuro ya anotado en E3/E3.b.
- **Generalizar `ServicioAnulacion`** como `ServicioDevolucion.devolver(total, reembolsos=[])`: costura anotada, no construida (no churn de E3.b).

## Nota de arquitectura

Este plan **no** introduce módulos nuevos: extiende `src/core/` (tres entidades, tres funciones puras, un servicio y un puerto) y `src/ventas/` (un adaptador, un método nuevo y el neteo de `totales_por_medio`), más una migración. Mantiene la frontera de E3/E3.b (persistencia no-UI del dominio venta/caja en `src/ventas/`, `src/caja/` solo Qt). **Recomendado pasar el subagente `arquitecto-pos`** antes de mergear para validar que la devolución respeta el aislamiento hexagonal y que el neteo del arqueo vive solo en el adaptador.
