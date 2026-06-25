# E1 Caja / Venta — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir la venta en caja sobre el dominio estable de E2/E4: entidades `Venta`, `LineaVenta`, `Pago`, `MedioPago`, `Cliente`; un `ServicioVenta` puro en `core` (agregar por unidad o por peso, total con impuestos, cobro con vuelto); puertos + adaptadores SQLite para ventas/clientes/medios de pago; migración `002`; y un prototipo de pantalla de caja en PySide6 que es solo una cáscara sobre el servicio.

**Architecture:** Hexagonal estricta, igual que E2/E4. La lógica de venta vive en `src/core/` (entidades frozen, reglas en `calculos.py`, `ServicioVenta` que solo conoce puertos `RepositorioProductos`/`RepositorioImpuestos`). La persistencia de la venta vive en un **módulo nuevo `src/ventas/`** (adaptadores SQLite de `RepositorioVentas`/`RepositorioClientes`/`RepositorioMediosPago`), para no meter SQL en `src/caja/` (que es solo UI). La pantalla Qt (`src/caja/`) es una vista delgada que delega todo en `ServicioVenta`; por eso el dominio se prueba sin Qt y la ventana solo tiene un smoke test.

**Tech Stack:** Python 3.11+, stdlib `sqlite3` + `decimal` + `dataclasses` + `typing.Protocol`, `PySide6` (solo en `src/caja/` y `scripts/caja.py`; no en `core`), `pytest`.

## Decisiones de diseño (revisar antes de ejecutar)

1. **IVA incluido en el precio (precio al público).** `producto.precio` es el precio final que paga el cliente, IVA incluido (norma del retail colombiano y coherente con `subtotal_por_peso`, que ya devuelve `precio×peso` como subtotal cobrable). Por tanto: `total = Σ subtotales` (lo que paga el cliente) e `impuesto` por línea es el **IVA contenido** en ese subtotal, calculado como `subtotal × tarifa / (1 + tarifa)`. En carnicería/fruver mucho producto es excluido (tarifa `0`) y el modelo lo cubre sin casos especiales.
2. **`src/ventas/` es un módulo de persistencia nuevo** (mirror de `src/inventario/`). Razón: la regla "SQL solo en adaptadores de repositorio" prohíbe SQL en `src/caja/` (UI). Si se prefiere no abrir módulo nuevo, la alternativa es alojar estos adaptadores en `src/inventario/`; se eligió `ventas/` por frontera de dominio más limpia. **Recomendado: pasar el subagente `arquitecto-pos` antes de mergear** para bendecir el módulo y, si procede, actualizar el mapa de módulos en `CLAUDE.md`/`docs/README-pos.md`.
3. **FKs `usuario_id` y `caja_sesion_id` quedan NULLABLE** en `ventas`. E8 (usuarios) y E3 (sesiones de caja) aún no existen; sus tablas se crean ahora (esquema) para integridad referencial futura, pero E1 inserta ventas sin sesión/usuario. Mismo patrón que `lotes` en E2 (tabla ahora, repo después).
4. **El descuento de inventario al vender se difiere** (YAGNI para el prototipo de caja). El servicio arma y cobra la venta; emitir la `salida` de inventario al confirmar es el siguiente paso natural (se empareja con la devolución de E3). Ver sección "Diferido a propósito".

## Global Constraints

- **Python ≥ 3.11** — sintaxis `X | None` y `tuple[...]` nativas.
- **`src/core/` NO importa Qt ni SQLite ni pyserial.** Prohibido `import sqlite3` / `from PySide6` / `import serial` bajo `src/core/`. El servicio recibe repositorios por inyección (objetos que cumplen los `Protocol`).
- **SQL solo en adaptadores de repositorio** (`src/inventario/`, `src/ventas/`). Nada de SQL en `core`/`caja`.
- **Dinero y cantidades con `decimal.Decimal`**, nunca `float`. Columnas SQLite declaradas `DECIMAL` (adapter/converter ya registrados en `inventario/db.py`); las sumas de totales se hacen en Python.
- **Redondeo a peso colombiano entero** con `ROUND_HALF_UP` en toda cifra monetaria de salida.
- **Nombres de dominio en español** (`Venta`, `LineaVenta`, `Pago`, `MedioPago`, `Cliente`, `ServicioVenta`).
- **Entidades del dominio = `@dataclass(frozen=True)`**; puertos = `typing.Protocol`. Mutar = `dataclasses.replace`.
- **Tests:** `pytest`, `pythonpath = src` (ya en `pytest.ini`); archivos `test_*.py`, estructura espejo por módulo. Imports tipo `from core.servicio_venta import ServicioVenta`.
- **Ponytail/YAGNI:** mínimo código; no modelar anticipos, notas crédito, descuentos por línea, ni el descuento de inventario aún. No tocar `outbox` ni DIAN.
- **Migraciones versionadas** en `scripts/migraciones/NNN_*.sql`; integridad referencial activa (`PRAGMA foreign_keys = ON`, ya en `conectar`).

---

## File Structure

**Core (dominio puro)**
- `src/core/entidades.py` — *extender* con `MedioPago`, `Cliente`, `Pago`, `LineaVenta`, `Venta`.
- `src/core/calculos.py` — *extender* con `subtotal_por_unidad`, `impuesto_incluido`, `calcular_vuelto`.
- `src/core/puertos.py` — *extender* `RepositorioImpuestos` (`por_id`) y *añadir* `RepositorioClientes`, `RepositorioMediosPago`, `RepositorioVentas`.
- `src/core/servicio_venta.py` — **nuevo**: `ServicioVenta` + excepciones `ProductoNoEncontrado`, `PesoRequerido`.

**Persistencia de ventas (adaptadores SQLite, módulo nuevo)**
- `scripts/migraciones/002_ventas.sql` — **nuevo**: `usuarios`, `clientes`, `medios_pago`, `caja_sesiones`, `ventas`, `venta_lineas`, `pagos` (+ seed de medios de pago).
- `src/ventas/__init__.py` — **nuevo** (vacío).
- `src/ventas/repositorio_sqlite.py` — **nuevo**: `RepositorioClientesSQLite`, `RepositorioMediosPagoSQLite`, `RepositorioVentasSQLite`.
- `src/inventario/repositorio_sqlite.py` — *modificar*: añadir `por_id` a `RepositorioImpuestosSQLite`.

**UI de caja (cáscara Qt)**
- `src/caja/pantalla_venta.py` — **nuevo**: `PantallaVenta(QWidget)`, delega en `ServicioVenta`.
- `scripts/caja.py` — **nuevo**: composition root que lanza la pantalla.

**Tests**
- `tests/core/test_entidades_venta.py`, `tests/core/test_calculos_venta.py`, `tests/core/test_servicio_venta.py`.
- `tests/ventas/__init__.py`, `tests/ventas/conftest.py`, `tests/ventas/test_repositorio_ventas.py`.
- `tests/ventas/test_flujo_venta_simple.py` — flujo crítico #1 (integración).
- `tests/caja/test_pantalla_venta.py` — smoke test bajo `importorskip`.

---

### Task E1.1: Entidades de venta + invariantes

**Files:**
- Modify: `src/core/entidades.py`
- Test: `tests/core/test_entidades_venta.py`

**Interfaces:**
- Consumes: `Decimal`, `datetime` (ya importados en el módulo).
- Produces:
  - `MedioPago(nombre: str, id: int | None = None)`
  - `Cliente(identificacion: str, nombre: str, contacto: str | None = None, bloqueado_edicion: bool = False, tipo_documento: str | None = None, regimen: str | None = None, tipo_responsabilidad: str | None = None, id: int | None = None)`
  - `Pago(medio_pago_id: int, monto: Decimal, referencia: str | None = None, venta_id: int | None = None, id: int | None = None)` — `monto > 0`.
  - `LineaVenta(producto_id: int, descripcion: str, cantidad_o_peso: Decimal, precio_unit: Decimal, impuesto: Decimal, subtotal: Decimal, venta_id: int | None = None, id: int | None = None)`
  - `Venta(fecha: datetime, lineas: tuple[LineaVenta, ...], total: Decimal, total_impuestos: Decimal, usuario_id: int | None = None, caja_sesion_id: int | None = None, cliente_id: int | None = None, estado: str = "pagada", id: int | None = None)` — `estado ∈ {"pagada","anulada"}`.
  - Constante `ESTADOS_VENTA = ("pagada", "anulada")`.

- [ ] **Step 1: Write the failing test**

```python
# tests/core/test_entidades_venta.py
from datetime import datetime
from decimal import Decimal

import pytest

from core.entidades import Cliente, LineaVenta, MedioPago, Pago, Venta


def _linea() -> LineaVenta:
    return LineaVenta(producto_id=1, descripcion="Gaseosa", cantidad_o_peso=Decimal("2"),
                      precio_unit=Decimal("3500"), impuesto=Decimal("1118"),
                      subtotal=Decimal("7000"))


def test_medio_pago_minimo():
    assert MedioPago(nombre="Efectivo").nombre == "Efectivo"


def test_cliente_reserva_campos_dian():
    c = Cliente(identificacion="900123", nombre="ACME")
    assert c.bloqueado_edicion is False
    assert c.tipo_documento is None and c.regimen is None


def test_pago_monto_no_positivo_falla():
    with pytest.raises(ValueError):
        Pago(medio_pago_id=1, monto=Decimal("0"))


def test_linea_venta_se_construye():
    assert _linea().subtotal == Decimal("7000")


def test_venta_valida_se_construye():
    v = Venta(fecha=datetime(2026, 6, 25), lineas=(_linea(),),
              total=Decimal("7000"), total_impuestos=Decimal("1118"))
    assert v.estado == "pagada"
    assert v.id is None


def test_venta_estado_invalido_falla():
    with pytest.raises(ValueError):
        Venta(fecha=datetime(2026, 6, 25), lineas=(_linea(),),
              total=Decimal("7000"), total_impuestos=Decimal("1118"), estado="regalo")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_entidades_venta.py -v`
Expected: FAIL con `ImportError: cannot import name 'Venta' from 'core.entidades'`.

- [ ] **Step 3: Append the entities**

Añadir al final de `src/core/entidades.py` (las importaciones `dataclass`, `datetime`, `Decimal`, y `CERO` ya existen en el módulo):

```python
ESTADOS_VENTA = ("pagada", "anulada")


@dataclass(frozen=True)
class MedioPago:
    nombre: str
    id: int | None = None


@dataclass(frozen=True)
class Cliente:
    identificacion: str
    nombre: str
    contacto: str | None = None
    bloqueado_edicion: bool = False
    tipo_documento: str | None = None        # reservado DIAN
    regimen: str | None = None               # reservado DIAN
    tipo_responsabilidad: str | None = None  # reservado DIAN
    id: int | None = None


@dataclass(frozen=True)
class Pago:
    medio_pago_id: int
    monto: Decimal
    referencia: str | None = None
    venta_id: int | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        if self.monto <= CERO:
            raise ValueError("monto del pago debe ser positivo")


@dataclass(frozen=True)
class LineaVenta:
    producto_id: int
    descripcion: str          # nombre del producto al momento de vender (snapshot para recibo)
    cantidad_o_peso: Decimal  # unidades (entero) o kg (decimal)
    precio_unit: Decimal      # precio al público, IVA incluido
    impuesto: Decimal         # IVA contenido en el subtotal
    subtotal: Decimal         # lo que paga el cliente por esta línea
    venta_id: int | None = None
    id: int | None = None


@dataclass(frozen=True)
class Venta:
    fecha: datetime
    lineas: tuple[LineaVenta, ...]
    total: Decimal            # Σ subtotales (IVA incluido)
    total_impuestos: Decimal  # Σ IVA contenido
    usuario_id: int | None = None
    caja_sesion_id: int | None = None
    cliente_id: int | None = None
    estado: str = "pagada"
    id: int | None = None

    def __post_init__(self) -> None:
        if self.estado not in ESTADOS_VENTA:
            raise ValueError(f"estado inválido: {self.estado!r}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_entidades_venta.py -v`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add src/core/entidades.py tests/core/test_entidades_venta.py
git commit -m "feat(core): entidades de venta (Venta, LineaVenta, Pago, Cliente, MedioPago)"
```

---

### Task E1.2: Reglas de cálculo de venta (precio×unidad, IVA incluido, vuelto)

**Files:**
- Modify: `src/core/calculos.py`
- Test: `tests/core/test_calculos_venta.py`

**Interfaces:**
- Consumes: `Decimal`, `ROUND_HALF_UP`, `CERO` (ya en el módulo).
- Produces:
  - `subtotal_por_unidad(precio_unit: Decimal, cantidad: Decimal) -> Decimal` — `precio×cantidad`, redondeo COP `HALF_UP`; rechaza negativos.
  - `impuesto_incluido(subtotal: Decimal, tarifa: Decimal) -> Decimal` — IVA contenido en un subtotal con IVA incluido: `subtotal × tarifa / (1+tarifa)`, redondeo COP `HALF_UP`. `tarifa=0 → 0`.
  - `calcular_vuelto(total: Decimal, recibido: Decimal) -> Decimal` — `recibido − total`; lanza `ValueError` si `recibido < total`.

- [ ] **Step 1: Write the failing test**

```python
# tests/core/test_calculos_venta.py
from decimal import Decimal

import pytest

from core.calculos import calcular_vuelto, impuesto_incluido, subtotal_por_unidad


def test_subtotal_por_unidad_basico():
    assert subtotal_por_unidad(Decimal("3500"), Decimal("2")) == Decimal("7000")


def test_subtotal_por_unidad_negativo_falla():
    with pytest.raises(ValueError):
        subtotal_por_unidad(Decimal("3500"), Decimal("-1"))


def test_iva_incluido_19():
    # 11900 con IVA incluido al 19% -> IVA contenido 1900 exacto
    assert impuesto_incluido(Decimal("11900"), Decimal("0.19")) == Decimal("1900")


def test_iva_incluido_redondea_half_up():
    # 7000 * 0.19 / 1.19 = 1117.647... -> 1118
    assert impuesto_incluido(Decimal("7000"), Decimal("0.19")) == Decimal("1118")


def test_iva_incluido_tarifa_cero():
    assert impuesto_incluido(Decimal("6000"), Decimal("0")) == Decimal("0")


def test_vuelto_basico():
    assert calcular_vuelto(Decimal("13000"), Decimal("20000")) == Decimal("7000")


def test_vuelto_pago_insuficiente_falla():
    with pytest.raises(ValueError):
        calcular_vuelto(Decimal("13000"), Decimal("10000"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_calculos_venta.py -v`
Expected: FAIL con `ImportError: cannot import name 'subtotal_por_unidad' from 'core.calculos'`.

- [ ] **Step 3: Append the rules**

Añadir al final de `src/core/calculos.py` (`Decimal`, `ROUND_HALF_UP`, `CERO` ya importados):

```python
_PESO = Decimal("1")  # cuantización a peso colombiano entero


def subtotal_por_unidad(precio_unit: Decimal, cantidad: Decimal) -> Decimal:
    """Subtotal de una línea por unidad, redondeado a pesos colombianos (enteros)."""
    if precio_unit < CERO or cantidad < CERO:
        raise ValueError("precio y cantidad deben ser no negativos")
    return (precio_unit * cantidad).quantize(_PESO, rounding=ROUND_HALF_UP)


def impuesto_incluido(subtotal: Decimal, tarifa: Decimal) -> Decimal:
    """IVA contenido en un subtotal que ya lo incluye: subtotal * tarifa / (1 + tarifa)."""
    if subtotal < CERO or tarifa < CERO:
        raise ValueError("subtotal y tarifa deben ser no negativos")
    return (subtotal * tarifa / (Decimal("1") + tarifa)).quantize(_PESO, rounding=ROUND_HALF_UP)


def calcular_vuelto(total: Decimal, recibido: Decimal) -> Decimal:
    """Vuelto a entregar. Lanza si el dinero recibido no cubre el total."""
    if recibido < total:
        raise ValueError("pago insuficiente")
    return recibido - total
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_calculos_venta.py -v`
Expected: PASS (7 passed).

- [ ] **Step 5: Commit**

```bash
git add src/core/calculos.py tests/core/test_calculos_venta.py
git commit -m "feat(core): reglas de venta (precio x unidad, IVA incluido, vuelto)"
```

---

### Task E1.3: Puertos de venta + `ServicioVenta`

**Files:**
- Modify: `src/core/puertos.py`
- Create: `src/core/servicio_venta.py`
- Test: `tests/core/test_servicio_venta.py`

**Interfaces:**
- Consumes: `Producto`, `Impuesto`, `Cliente`, `MedioPago`, `Venta`, `LineaVenta`, `Pago` (E1.1); `subtotal_por_unidad`, `impuesto_incluido` (E1.2); `subtotal_por_peso` (E4.1); `RepositorioProductos.por_codigo` (E2.3).
- Produces (puertos en `core.puertos`):
  - `RepositorioImpuestos.por_id(id: int) -> Impuesto | None` (añadido al Protocol existente).
  - `RepositorioClientes`: `guardar(c: Cliente) -> Cliente`, `por_id(id: int) -> Cliente | None`, `por_identificacion(identificacion: str) -> Cliente | None`, `listar() -> list[Cliente]`.
  - `RepositorioMediosPago`: `listar() -> list[MedioPago]`, `por_id(id: int) -> MedioPago | None`.
  - `RepositorioVentas`: `guardar(venta: Venta, pagos: list[Pago]) -> Venta`, `por_id(id: int) -> Venta | None`, `pagos_de(venta_id: int) -> list[Pago]`.
- Produces (servicio en `core.servicio_venta`):
  - `ProductoNoEncontrado(ValueError)`, `PesoRequerido(ValueError)`.
  - `ServicioVenta(productos: RepositorioProductos, impuestos: RepositorioImpuestos)`:
    - `agregar(codigo_barras: str, *, cantidad: Decimal | int = 1, peso_kg: Decimal | None = None) -> LineaVenta`
    - propiedad `lineas -> tuple[LineaVenta, ...]`
    - propiedad `total -> Decimal`
    - propiedad `total_impuestos -> Decimal`
    - `confirmar(*, fecha: datetime, usuario_id: int | None = None, caja_sesion_id: int | None = None, cliente_id: int | None = None) -> Venta`

- [ ] **Step 1: Write the failing test**

```python
# tests/core/test_servicio_venta.py
from datetime import datetime
from decimal import Decimal

import pytest

from core.entidades import Impuesto, Producto
from core.servicio_venta import ProductoNoEncontrado, PesoRequerido, ServicioVenta


class _FakeProductos:
    def __init__(self, *productos: Producto) -> None:
        self._por_codigo = {p.codigo_barras: p for p in productos}

    def por_codigo(self, codigo_barras: str):
        return self._por_codigo.get(codigo_barras)


class _FakeImpuestos:
    def __init__(self, *impuestos: Impuesto) -> None:
        self._por_id = {i.id: i for i in impuestos}

    def por_id(self, id: int):
        return self._por_id.get(id)


IVA = Impuesto(nombre="IVA", tarifa=Decimal("0.19"), id=10)
EXCLUIDO = Impuesto(nombre="Excluido", tarifa=Decimal("0"), id=20)
GASEOSA = Producto(codigo_barras="B", nombre="Gaseosa", precio=Decimal("3500"),
                   impuesto_id=10, id=1)
MANZANA = Producto(codigo_barras="A", nombre="Manzana", precio=Decimal("4000"),
                   vendido_por_peso=True, unidad="kg", impuesto_id=20, id=2)


def _servicio() -> ServicioVenta:
    return ServicioVenta(_FakeProductos(GASEOSA, MANZANA), _FakeImpuestos(IVA, EXCLUIDO))


def test_agregar_por_unidad_calcula_subtotal_e_iva_contenido():
    s = _servicio()
    linea = s.agregar("B", cantidad=2)
    assert linea.subtotal == Decimal("7000")
    assert linea.impuesto == Decimal("1118")
    assert linea.descripcion == "Gaseosa"
    assert s.total == Decimal("7000")
    assert s.total_impuestos == Decimal("1118")


def test_agregar_por_peso_usa_precio_por_kg():
    s = _servicio()
    linea = s.agregar("A", peso_kg=Decimal("1.5"))
    assert linea.subtotal == Decimal("6000")
    assert linea.impuesto == Decimal("0")  # excluido
    assert linea.cantidad_o_peso == Decimal("1.5")


def test_producto_por_peso_sin_peso_falla():
    with pytest.raises(PesoRequerido):
        _servicio().agregar("A")


def test_codigo_inexistente_falla():
    with pytest.raises(ProductoNoEncontrado):
        _servicio().agregar("ZZZ")


def test_confirmar_vacio_falla():
    with pytest.raises(ValueError):
        _servicio().confirmar(fecha=datetime(2026, 6, 25))


def test_confirmar_arma_venta_con_totales():
    s = _servicio()
    s.agregar("B", cantidad=2)
    s.agregar("A", peso_kg=Decimal("1.5"))
    venta = s.confirmar(fecha=datetime(2026, 6, 25))
    assert venta.estado == "pagada"
    assert len(venta.lineas) == 2
    assert venta.total == Decimal("13000")
    assert venta.total_impuestos == Decimal("1118")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_servicio_venta.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'core.servicio_venta'`.

- [ ] **Step 3a: Extend the ports**

En `src/core/puertos.py`, añadir `Cliente`, `MedioPago`, `Pago`, `Venta` al import de `core.entidades`, añadir `por_id` a `RepositorioImpuestos`, y añadir los tres puertos nuevos:

```python
# src/core/puertos.py  (import existente ampliado)
from core.entidades import (
    Categoria, Cliente, Impuesto, MedioPago, MovimientoInventario, Pago, Producto, Venta,
)
```

Reemplazar el `RepositorioImpuestos` existente por:

```python
class RepositorioImpuestos(Protocol):
    def guardar(self, impuesto: Impuesto) -> Impuesto: ...
    def por_id(self, id: int) -> Impuesto | None: ...
```

Y añadir al final del archivo:

```python
class RepositorioClientes(Protocol):
    def guardar(self, cliente: Cliente) -> Cliente: ...
    def por_id(self, id: int) -> Cliente | None: ...
    def por_identificacion(self, identificacion: str) -> Cliente | None: ...
    def listar(self) -> list[Cliente]: ...


class RepositorioMediosPago(Protocol):
    def listar(self) -> list[MedioPago]: ...
    def por_id(self, id: int) -> MedioPago | None: ...


class RepositorioVentas(Protocol):
    def guardar(self, venta: Venta, pagos: list[Pago]) -> Venta: ...
    def por_id(self, id: int) -> Venta | None: ...
    def pagos_de(self, venta_id: int) -> list[Pago]: ...
```

- [ ] **Step 3b: Write the service**

```python
# src/core/servicio_venta.py
"""Servicio de venta en caja. Python puro: arma líneas y totales vía puertos."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from core.calculos import impuesto_incluido, subtotal_por_peso, subtotal_por_unidad
from core.entidades import LineaVenta, Venta
from core.puertos import RepositorioImpuestos, RepositorioProductos

CERO = Decimal("0")


class ProductoNoEncontrado(ValueError):
    pass


class PesoRequerido(ValueError):
    pass


class ServicioVenta:
    """Acumula líneas de una venta en curso y la confirma como `Venta`."""

    def __init__(self, productos: RepositorioProductos, impuestos: RepositorioImpuestos) -> None:
        self._productos = productos
        self._impuestos = impuestos
        self._lineas: list[LineaVenta] = []

    def agregar(self, codigo_barras: str, *, cantidad: Decimal | int = 1,
                peso_kg: Decimal | None = None) -> LineaVenta:
        producto = self._productos.por_codigo(codigo_barras)
        if producto is None:
            raise ProductoNoEncontrado(f"producto inexistente: {codigo_barras!r}")
        tarifa = CERO
        if producto.impuesto_id is not None:
            impuesto = self._impuestos.por_id(producto.impuesto_id)
            if impuesto is not None:
                tarifa = impuesto.tarifa
        if producto.vendido_por_peso:
            if peso_kg is None:
                raise PesoRequerido(f"{producto.nombre} se vende por peso")
            cantidad_o_peso = peso_kg
            subtotal = subtotal_por_peso(producto.precio, peso_kg)
        else:
            cantidad_o_peso = Decimal(cantidad)
            subtotal = subtotal_por_unidad(producto.precio, cantidad_o_peso)
        linea = LineaVenta(
            producto_id=producto.id,
            descripcion=producto.nombre,
            cantidad_o_peso=cantidad_o_peso,
            precio_unit=producto.precio,
            impuesto=impuesto_incluido(subtotal, tarifa),
            subtotal=subtotal,
        )
        self._lineas.append(linea)
        return linea

    # Nota: `subtotal_por_peso` vive en core.calculos junto a las demás reglas de cálculo.

    @property
    def lineas(self) -> tuple[LineaVenta, ...]:
        return tuple(self._lineas)

    @property
    def total(self) -> Decimal:
        return sum((l.subtotal for l in self._lineas), CERO)

    @property
    def total_impuestos(self) -> Decimal:
        return sum((l.impuesto for l in self._lineas), CERO)

    def confirmar(self, *, fecha: datetime, usuario_id: int | None = None,
                  caja_sesion_id: int | None = None, cliente_id: int | None = None) -> Venta:
        if not self._lineas:
            raise ValueError("no se puede confirmar una venta vacía")
        return Venta(
            fecha=fecha,
            lineas=self.lineas,
            total=self.total,
            total_impuestos=self.total_impuestos,
            usuario_id=usuario_id,
            caja_sesion_id=caja_sesion_id,
            cliente_id=cliente_id,
            estado="pagada",
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_servicio_venta.py -v`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add src/core/puertos.py src/core/servicio_venta.py tests/core/test_servicio_venta.py
git commit -m "feat(core): puertos de venta y ServicioVenta (unidad/peso, totales)"
```

---

### Task E1.4: Migración 002 (ventas, clientes, medios de pago) + esquema

**Files:**
- Create: `scripts/migraciones/002_ventas.sql`
- Test: `tests/ventas/__init__.py`, `tests/ventas/conftest.py`, *(test del esquema en)* `tests/ventas/test_repositorio_ventas.py` (solo el primer test de esquema en este task; el resto se añade en E1.5)

**Interfaces:**
- Consumes: `inventario.db.conectar`, `aplicar_migraciones` (E2.2). `aplicar_migraciones` ya aplica en orden todos los `*.sql`, así que `002_ventas.sql` se ejecuta tras `001_inventario.sql`.
- Produces (tablas): `usuarios`, `clientes`, `medios_pago`, `caja_sesiones`, `ventas`, `venta_lineas`, `pagos`; filas semilla en `medios_pago` (`Efectivo`, `Tarjeta`, `Transferencia`).
- Produces (fixture): `conn` en `tests/ventas/conftest.py` — conexión `:memory:` ya migrada.

- [ ] **Step 1: Write the schema**

```sql
-- scripts/migraciones/002_ventas.sql
-- Esquema de caja/venta (E1). DECIMAL declarado para Decimal exacto y portabilidad PostgreSQL.

-- Esquema ahora, repositorio diferido (E8 usuarios / E3 caja). Permite FK de ventas.
CREATE TABLE IF NOT EXISTS usuarios (
    id            INTEGER PRIMARY KEY,
    nombre        TEXT NOT NULL,
    rol           TEXT NOT NULL DEFAULT 'cajero',
    hash_password TEXT
);

CREATE TABLE IF NOT EXISTS clientes (
    id                   INTEGER PRIMARY KEY,
    identificacion       TEXT NOT NULL UNIQUE,
    nombre               TEXT NOT NULL,
    contacto             TEXT,
    bloqueado_edicion    INTEGER NOT NULL DEFAULT 0,  -- BOOL 0/1
    tipo_documento       TEXT,                        -- reservado DIAN
    regimen              TEXT,                        -- reservado DIAN
    tipo_responsabilidad TEXT                         -- reservado DIAN
);

CREATE TABLE IF NOT EXISTS medios_pago (
    id     INTEGER PRIMARY KEY,
    nombre TEXT NOT NULL UNIQUE
);

INSERT OR IGNORE INTO medios_pago (id, nombre) VALUES
    (1, 'Efectivo'), (2, 'Tarjeta'), (3, 'Transferencia');

-- Esquema ahora, repositorio diferido (E3 cierre/arqueo). Permite FK de ventas.
CREATE TABLE IF NOT EXISTS caja_sesiones (
    id             INTEGER PRIMARY KEY,
    usuario_id     INTEGER REFERENCES usuarios(id),
    apertura_fecha TEXT NOT NULL,
    monto_inicial  DECIMAL NOT NULL DEFAULT '0',
    cierre_fecha   TEXT,
    monto_contado  DECIMAL,
    estado         TEXT NOT NULL DEFAULT 'abierta'
);

CREATE TABLE IF NOT EXISTS ventas (
    id              INTEGER PRIMARY KEY,
    fecha           TEXT NOT NULL,                        -- ISO-8601
    usuario_id      INTEGER REFERENCES usuarios(id),      -- NULLABLE (E8)
    caja_sesion_id  INTEGER REFERENCES caja_sesiones(id), -- NULLABLE (E3)
    cliente_id      INTEGER REFERENCES clientes(id),      -- NULLABLE (consumidor final)
    total           DECIMAL NOT NULL,
    total_impuestos DECIMAL NOT NULL,
    estado          TEXT NOT NULL DEFAULT 'pagada'
);

CREATE TABLE IF NOT EXISTS venta_lineas (
    id              INTEGER PRIMARY KEY,
    venta_id        INTEGER NOT NULL REFERENCES ventas(id),
    producto_id     INTEGER NOT NULL REFERENCES productos(id),
    descripcion     TEXT NOT NULL,        -- snapshot del nombre para el recibo
    cantidad_o_peso DECIMAL NOT NULL,
    precio_unit     DECIMAL NOT NULL,
    impuesto        DECIMAL NOT NULL,
    subtotal        DECIMAL NOT NULL
);

CREATE TABLE IF NOT EXISTS pagos (
    id            INTEGER PRIMARY KEY,
    venta_id      INTEGER NOT NULL REFERENCES ventas(id),
    medio_pago_id INTEGER NOT NULL REFERENCES medios_pago(id),
    monto         DECIMAL NOT NULL,
    referencia    TEXT
);
```

- [ ] **Step 2: Write the test package marker + fixture**

```python
# tests/ventas/__init__.py
```
(archivo vacío)

```python
# tests/ventas/conftest.py
import pytest

from inventario.db import conectar, aplicar_migraciones


@pytest.fixture
def conn():
    c = conectar()  # :memory:
    aplicar_migraciones(c)
    yield c
    c.close()
```

- [ ] **Step 3: Write the schema test**

```python
# tests/ventas/test_repositorio_ventas.py
def test_migracion_002_crea_tablas_de_venta(conn):
    tablas = {f["name"] for f in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"usuarios", "clientes", "medios_pago", "caja_sesiones",
            "ventas", "venta_lineas", "pagos"} <= tablas


def test_medios_pago_semilla(conn):
    nombres = {f["nombre"] for f in conn.execute("SELECT nombre FROM medios_pago")}
    assert {"Efectivo", "Tarjeta", "Transferencia"} <= nombres
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/ventas/test_repositorio_ventas.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add scripts/migraciones/002_ventas.sql tests/ventas/__init__.py tests/ventas/conftest.py tests/ventas/test_repositorio_ventas.py
git commit -m "feat(ventas): migracion 002 (ventas, lineas, pagos, clientes, medios de pago)"
```

---

### Task E1.5: Adaptadores SQLite de venta, clientes y medios de pago

**Files:**
- Create: `src/ventas/__init__.py`
- Create: `src/ventas/repositorio_sqlite.py`
- Modify: `src/inventario/repositorio_sqlite.py` (añadir `por_id` a `RepositorioImpuestosSQLite`)
- Test: `tests/ventas/test_repositorio_ventas.py` (añadir casos a los de E1.4)

**Interfaces:**
- Consumes: `Cliente`, `MedioPago`, `Pago`, `Venta`, `LineaVenta` (E1.1); fixture `conn` (E1.4); `RepositorioProductosSQLite`, `RepositorioCategoriasSQLite`, `RepositorioImpuestosSQLite` (E2.3).
- Produces (en `ventas.repositorio_sqlite`), cada uno `__init__(self, conn: sqlite3.Connection)`:
  - `RepositorioClientesSQLite` — `guardar`, `por_id`, `por_identificacion`, `listar`.
  - `RepositorioMediosPagoSQLite` — `listar`, `por_id`.
  - `RepositorioVentasSQLite` — `guardar(venta, pagos)` (inserta venta + líneas + pagos en una transacción y devuelve la venta con `id`), `por_id` (reconstruye `Venta` con sus `LineaVenta`), `pagos_de`.
- Produces (en `inventario.repositorio_sqlite`): `RepositorioImpuestosSQLite.por_id(id) -> Impuesto | None`.

- [ ] **Step 1: Add the failing tests**

Añadir a `tests/ventas/test_repositorio_ventas.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/ventas/test_repositorio_ventas.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'ventas.repositorio_sqlite'`.

- [ ] **Step 3a: Add `por_id` to the impuestos adapter**

En `src/inventario/repositorio_sqlite.py`, añadir al final de la clase `RepositorioImpuestosSQLite`:

```python
    def por_id(self, id: int) -> Impuesto | None:
        f = self._conn.execute("SELECT * FROM impuestos WHERE id = ?", (id,)).fetchone()
        return Impuesto(nombre=f["nombre"], tarifa=f["tarifa"],
                        codigo_dian=f["codigo_dian"], id=f["id"]) if f else None
```

(`Impuesto` ya está importado en ese módulo.)

- [ ] **Step 3b: Create the sales adapters**

```python
# src/ventas/__init__.py
```
(archivo vacío)

```python
# src/ventas/repositorio_sqlite.py
"""Adaptadores SQLite de venta, clientes y medios de pago. Único lugar con su SQL."""
from __future__ import annotations

import sqlite3
from dataclasses import replace
from datetime import datetime

from core.entidades import Cliente, LineaVenta, MedioPago, Pago, Venta


def _fila_a_cliente(f: sqlite3.Row) -> Cliente:
    return Cliente(
        identificacion=f["identificacion"],
        nombre=f["nombre"],
        contacto=f["contacto"],
        bloqueado_edicion=bool(f["bloqueado_edicion"]),
        tipo_documento=f["tipo_documento"],
        regimen=f["regimen"],
        tipo_responsabilidad=f["tipo_responsabilidad"],
        id=f["id"],
    )


class RepositorioClientesSQLite:
    _COLS = ("identificacion, nombre, contacto, bloqueado_edicion, "
             "tipo_documento, regimen, tipo_responsabilidad")

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def guardar(self, cliente: Cliente) -> Cliente:
        cur = self._conn.execute(
            f"INSERT INTO clientes ({self._COLS}) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (cliente.identificacion, cliente.nombre, cliente.contacto,
             int(cliente.bloqueado_edicion), cliente.tipo_documento,
             cliente.regimen, cliente.tipo_responsabilidad))
        self._conn.commit()
        return replace(cliente, id=cur.lastrowid)

    def por_id(self, id: int) -> Cliente | None:
        f = self._conn.execute("SELECT * FROM clientes WHERE id = ?", (id,)).fetchone()
        return _fila_a_cliente(f) if f else None

    def por_identificacion(self, identificacion: str) -> Cliente | None:
        f = self._conn.execute(
            "SELECT * FROM clientes WHERE identificacion = ?", (identificacion,)).fetchone()
        return _fila_a_cliente(f) if f else None

    def listar(self) -> list[Cliente]:
        filas = self._conn.execute("SELECT * FROM clientes ORDER BY id").fetchall()
        return [_fila_a_cliente(f) for f in filas]


class RepositorioMediosPagoSQLite:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def listar(self) -> list[MedioPago]:
        filas = self._conn.execute("SELECT * FROM medios_pago ORDER BY id").fetchall()
        return [MedioPago(nombre=f["nombre"], id=f["id"]) for f in filas]

    def por_id(self, id: int) -> MedioPago | None:
        f = self._conn.execute("SELECT * FROM medios_pago WHERE id = ?", (id,)).fetchone()
        return MedioPago(nombre=f["nombre"], id=f["id"]) if f else None


def _fila_a_linea(f: sqlite3.Row) -> LineaVenta:
    return LineaVenta(
        producto_id=f["producto_id"],
        descripcion=f["descripcion"],
        cantidad_o_peso=f["cantidad_o_peso"],
        precio_unit=f["precio_unit"],
        impuesto=f["impuesto"],
        subtotal=f["subtotal"],
        venta_id=f["venta_id"],
        id=f["id"],
    )


class RepositorioVentasSQLite:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def guardar(self, venta: Venta, pagos: list[Pago]) -> Venta:
        cur = self._conn.execute(
            "INSERT INTO ventas "
            "(fecha, usuario_id, caja_sesion_id, cliente_id, total, total_impuestos, estado) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (venta.fecha.isoformat(), venta.usuario_id, venta.caja_sesion_id,
             venta.cliente_id, venta.total, venta.total_impuestos, venta.estado))
        venta_id = cur.lastrowid
        for l in venta.lineas:
            self._conn.execute(
                "INSERT INTO venta_lineas "
                "(venta_id, producto_id, descripcion, cantidad_o_peso, precio_unit, "
                "impuesto, subtotal) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (venta_id, l.producto_id, l.descripcion, l.cantidad_o_peso,
                 l.precio_unit, l.impuesto, l.subtotal))
        for pago in pagos:
            self._conn.execute(
                "INSERT INTO pagos (venta_id, medio_pago_id, monto, referencia) "
                "VALUES (?, ?, ?, ?)",
                (venta_id, pago.medio_pago_id, pago.monto, pago.referencia))
        self._conn.commit()
        return replace(venta, id=venta_id)

    def por_id(self, id: int) -> Venta | None:
        fv = self._conn.execute("SELECT * FROM ventas WHERE id = ?", (id,)).fetchone()
        if fv is None:
            return None
        filas = self._conn.execute(
            "SELECT * FROM venta_lineas WHERE venta_id = ? ORDER BY id", (id,)).fetchall()
        return Venta(
            fecha=datetime.fromisoformat(fv["fecha"]),
            lineas=tuple(_fila_a_linea(f) for f in filas),
            total=fv["total"],
            total_impuestos=fv["total_impuestos"],
            usuario_id=fv["usuario_id"],
            caja_sesion_id=fv["caja_sesion_id"],
            cliente_id=fv["cliente_id"],
            estado=fv["estado"],
            id=fv["id"],
        )

    def pagos_de(self, venta_id: int) -> list[Pago]:
        filas = self._conn.execute(
            "SELECT * FROM pagos WHERE venta_id = ? ORDER BY id", (venta_id,)).fetchall()
        return [Pago(medio_pago_id=f["medio_pago_id"], monto=f["monto"],
                     referencia=f["referencia"], venta_id=f["venta_id"], id=f["id"])
                for f in filas]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/ventas/test_repositorio_ventas.py -v`
Expected: PASS (7 passed — 2 de esquema + 5 nuevos).

- [ ] **Step 5: Commit**

```bash
git add src/ventas/__init__.py src/ventas/repositorio_sqlite.py src/inventario/repositorio_sqlite.py tests/ventas/test_repositorio_ventas.py
git commit -m "feat(ventas): adaptadores SQLite de venta, clientes y medios de pago"
```

---

### Task E1.6: Flujo crítico — venta simple de extremo a extremo

> Cierra el flujo crítico #1 de `testing-pos` ("venta simple: agregar ítems, calcular total con impuestos, cobrar") con `ServicioVenta` + adaptadores SQLite reales, incluyendo cobro con vuelto y persistencia.

**Files:**
- Test: `tests/ventas/test_flujo_venta_simple.py`

**Interfaces:**
- Consumes: `RepositorioProductosSQLite`, `RepositorioCategoriasSQLite`, `RepositorioImpuestosSQLite` (E2.3); `RepositorioVentasSQLite` (E1.5); `ServicioVenta` (E1.3); `calcular_vuelto` (E1.2); fixture `conn` (E1.4).

- [ ] **Step 1: Write the test**

```python
# tests/ventas/test_flujo_venta_simple.py
from datetime import datetime
from decimal import Decimal

from core.calculos import calcular_vuelto
from core.entidades import Categoria, Impuesto, Pago, Producto
from core.servicio_venta import ServicioVenta
from inventario.repositorio_sqlite import (
    RepositorioCategoriasSQLite,
    RepositorioImpuestosSQLite,
    RepositorioProductosSQLite,
)
from ventas.repositorio_sqlite import RepositorioVentasSQLite


def _seed(conn):
    cat = RepositorioCategoriasSQLite(conn).guardar(Categoria(nombre="Surtido"))
    imp = RepositorioImpuestosSQLite(conn)
    iva = imp.guardar(Impuesto(nombre="IVA", tarifa=Decimal("0.19")))
    excl = imp.guardar(Impuesto(nombre="Excluido", tarifa=Decimal("0")))
    prod = RepositorioProductosSQLite(conn)
    prod.guardar(Producto(codigo_barras="B", nombre="Gaseosa", precio=Decimal("3500"),
                          categoria_id=cat.id, impuesto_id=iva.id))
    prod.guardar(Producto(codigo_barras="A", nombre="Manzana", precio=Decimal("4000"),
                          categoria_id=cat.id, impuesto_id=excl.id,
                          vendido_por_peso=True, unidad="kg"))


def test_venta_simple_calcula_cobra_y_persiste(conn):
    _seed(conn)
    servicio = ServicioVenta(RepositorioProductosSQLite(conn), RepositorioImpuestosSQLite(conn))

    servicio.agregar("B", cantidad=2)              # 2 x 3500 = 7000, IVA contenido 1118
    servicio.agregar("A", peso_kg=Decimal("1.5"))  # 1.5kg x 4000 = 6000, excluido

    assert servicio.total == Decimal("13000")
    assert servicio.total_impuestos == Decimal("1118")

    venta = servicio.confirmar(fecha=datetime(2026, 6, 25, 11, 0))
    vuelto = calcular_vuelto(venta.total, Decimal("20000"))
    assert vuelto == Decimal("7000")

    repo = RepositorioVentasSQLite(conn)
    guardada = repo.guardar(venta, [Pago(medio_pago_id=1, monto=Decimal("20000"))])

    releida = repo.por_id(guardada.id)
    assert releida.total == Decimal("13000")
    assert releida.total_impuestos == Decimal("1118")
    assert len(releida.lineas) == 2
    assert repo.pagos_de(guardada.id)[0].monto == Decimal("20000")
```

- [ ] **Step 2: Run the test**

Run: `pytest tests/ventas/test_flujo_venta_simple.py -v`
Expected: PASS (1 passed).

- [ ] **Step 3: Run the full suite**

Run: `pytest -v`
Expected: PASS (todo E2 + E4 + E1 verde; el smoke de caja aún no existe).

- [ ] **Step 4: Commit**

```bash
git add tests/ventas/test_flujo_venta_simple.py
git commit -m "test(ventas): flujo critico de venta simple (total, IVA, cobro, persistencia)"
```

---

### Task E1.7: Prototipo de pantalla de caja (PySide6) + lanzador

> La pantalla es una cáscara delgada: toda la lógica está en `ServicioVenta`. PySide6 puede no estar instalado en CI/dev; el smoke test usa `pytest.importorskip("PySide6")` para saltarse sin romper la suite. Antes de lanzar de verdad: `pip install -r requirements.txt`.

**Files:**
- Create: `src/caja/pantalla_venta.py`
- Create: `scripts/caja.py`
- Test: `tests/caja/test_pantalla_venta.py`

**Interfaces:**
- Consumes: `ServicioVenta` (E1.3); `conectar`, `aplicar_migraciones` (E2.2); `RepositorioProductosSQLite`, `RepositorioImpuestosSQLite` (E2.3/E1.5).
- Produces: `caja.pantalla_venta.PantallaVenta(servicio: ServicioVenta)` — `QWidget` con campos `código`/`peso`, botón Agregar, tabla de líneas y etiqueta de total; método interno `_al_agregar()`. `scripts/caja.py:main(ruta="pos.db")` como composition root.

- [ ] **Step 1: Write the smoke test**

```python
# tests/caja/test_pantalla_venta.py
import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from decimal import Decimal  # noqa: E402

from PySide6.QtWidgets import QApplication  # noqa: E402

from core.entidades import Impuesto, Producto  # noqa: E402
from core.servicio_venta import ServicioVenta  # noqa: E402
from caja.pantalla_venta import PantallaVenta  # noqa: E402


class _FakeProductos:
    def por_codigo(self, codigo_barras: str):
        return Producto(codigo_barras="B", nombre="Gaseosa", precio=Decimal("3500"),
                        impuesto_id=10, id=1)


class _FakeImpuestos:
    def por_id(self, id: int):
        return Impuesto(nombre="IVA", tarifa=Decimal("0.19"), id=10)


def test_pantalla_agrega_linea_y_actualiza_total():
    _app = QApplication.instance() or QApplication([])
    win = PantallaVenta(ServicioVenta(_FakeProductos(), _FakeImpuestos()))
    win._codigo.setText("B")
    win._al_agregar()
    assert win._tabla.rowCount() == 1
    assert "3500" in win._total.text()
```

- [ ] **Step 2: Run test to verify it is collected (skips if no PySide6)**

Run: `pytest tests/caja/test_pantalla_venta.py -v`
Expected: 1 skipped (sin PySide6) o 1 passed (con PySide6). Cualquiera de los dos es válido; no debe FALLAR.

- [ ] **Step 3: Write the screen**

```python
# src/caja/pantalla_venta.py
"""Prototipo de pantalla de caja (PySide6). La lógica vive en ServicioVenta (core)."""
from __future__ import annotations

from decimal import Decimal

from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from core.servicio_venta import ServicioVenta


class PantallaVenta(QWidget):
    def __init__(self, servicio: ServicioVenta) -> None:
        super().__init__()
        self._servicio = servicio
        self.setWindowTitle("Caja — Venta")

        self._codigo = QLineEdit()
        self._codigo.setPlaceholderText("Código de barras")
        self._peso = QLineEdit()
        self._peso.setPlaceholderText("Peso kg (si aplica)")
        boton = QPushButton("Agregar")
        boton.clicked.connect(self._al_agregar)

        self._tabla = QTableWidget(0, 3)
        self._tabla.setHorizontalHeaderLabels(["Descripción", "Cant/Peso", "Subtotal"])
        self._total = QLabel("Total: 0")

        fila = QHBoxLayout()
        fila.addWidget(self._codigo)
        fila.addWidget(self._peso)
        fila.addWidget(boton)

        layout = QVBoxLayout(self)
        layout.addLayout(fila)
        layout.addWidget(self._tabla)
        layout.addWidget(self._total)

    def _al_agregar(self) -> None:
        codigo = self._codigo.text().strip()
        if not codigo:
            return
        peso_txt = self._peso.text().strip()
        peso = Decimal(peso_txt) if peso_txt else None
        linea = self._servicio.agregar(codigo, peso_kg=peso)
        fila = self._tabla.rowCount()
        self._tabla.insertRow(fila)
        self._tabla.setItem(fila, 0, QTableWidgetItem(linea.descripcion))
        self._tabla.setItem(fila, 1, QTableWidgetItem(str(linea.cantidad_o_peso)))
        self._tabla.setItem(fila, 2, QTableWidgetItem(str(linea.subtotal)))
        self._total.setText(f"Total: {self._servicio.total}")
        self._codigo.clear()
        self._peso.clear()
```

- [ ] **Step 4: Write the launcher (composition root)**

```python
# scripts/caja.py
"""Lanza la pantalla de caja. Uso: python scripts/caja.py [pos.db]"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from core.servicio_venta import ServicioVenta  # noqa: E402
from inventario.db import aplicar_migraciones, conectar  # noqa: E402
from inventario.repositorio_sqlite import (  # noqa: E402
    RepositorioImpuestosSQLite,
    RepositorioProductosSQLite,
)
from caja.pantalla_venta import PantallaVenta  # noqa: E402


def main(ruta: str = "pos.db") -> None:
    conn = conectar(ruta)
    aplicar_migraciones(conn)
    servicio = ServicioVenta(RepositorioProductosSQLite(conn), RepositorioImpuestosSQLite(conn))
    app = QApplication(sys.argv)
    ventana = PantallaVenta(servicio)
    ventana.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "pos.db")
```

- [ ] **Step 5: Run the smoke test again, then the full suite**

Run: `pytest tests/caja/test_pantalla_venta.py -v`
Expected: 1 passed (si PySide6 está instalado) o 1 skipped (si no). No debe FALLAR.

Run: `pytest -v`
Expected: PASS (toda la suite verde; el smoke de caja pasa o se salta).

- [ ] **Step 6: Commit**

```bash
git add src/caja/pantalla_venta.py scripts/caja.py tests/caja/test_pantalla_venta.py
git commit -m "feat(caja): prototipo de pantalla de venta (PySide6) sobre ServicioVenta"
```

---

## Definición de "hecho" (E1)

- `pytest -v` en verde; sin SQL fuera de `src/inventario/` y `src/ventas/`; sin imports de Qt/SQLite/pyserial dentro de `src/core/`.
- `python scripts/migrar.py pos.db` crea también las tablas de E1; `python scripts/caja.py` abre la pantalla (con PySide6 instalado).
- El flujo crítico #1 (venta simple: agregar por unidad y por peso, total con IVA contenido, cobro con vuelto, persistencia y relectura) tiene test de integración verde.
- La pantalla Qt no contiene lógica de negocio: todo pasa por `ServicioVenta`.

## Self-Review (cobertura del spec y del roadmap)

| Requisito (roadmap / spec / encargo E1) | Task |
|---|---|
| Entidades `Venta`, `LineaVenta`, `Pago`, `MedioPago` en core | E1.1 |
| Entidad `Cliente` con campos reservados DIAN | E1.1 |
| Cálculo de total con impuestos (IVA incluido) | E1.2, E1.3 |
| Servicio de venta: agregar línea por peso o por unidad | E1.3 |
| Puerto `RepositorioVentas` | E1.3 (puerto), E1.5 (adaptador) |
| Puerto `RepositorioClientes` | E1.3 (puerto), E1.5 (adaptador) |
| `RepositorioImpuestos.por_id` (lo necesita el servicio) | E1.3 (puerto), E1.5 (adaptador) |
| Adaptadores SQLite de venta/clientes/medios de pago | E1.5 |
| Migración `002` (ventas, venta_lineas, pagos, clientes, medios_pago) | E1.4 |
| Tablas `usuarios`/`caja_sesiones` (esquema ahora, repo diferido) | E1.4 |
| Prototipo de pantalla de caja en Qt (PySide6) | E1.7 |
| Flujo crítico "venta simple" con test (testing-pos #1) | E1.6 |
| Dinero/cantidades con `Decimal` exacto | Constraint global; E1.4, E1.5 |
| core sin Qt/SQLite | Constraint global; E1.7 (cáscara fuera de core) |

**Diferido a propósito (YAGNI):**
- **Descuento de inventario al confirmar** (emitir `salida` por cada línea): siguiente paso, se empareja con la devolución (E3). Cuando entre, `ServicioVenta.confirmar` (o un servicio de cobro) recibirá `RepositorioInventario` por inyección.
- **Devolución / anulación** (flujo crítico #3) — entra con E3.
- **Repos de `usuarios` y `caja_sesiones`** — E8 y E3; aquí solo el esquema para FK.
- **Cobro con múltiples medios de pago en la UI** — el modelo lo soporta (`guardar(venta, [Pago, ...])`); el prototipo cobra el flujo, la UI de cobro multi-medio se refina en E3/E7.
- **DIAN y outbox** — E5/E6.

## Nota de arquitectura

Este plan introduce el módulo de persistencia `src/ventas/`, no listado en la tabla de módulos del spec. Antes de mergear, **pasar el subagente `arquitecto-pos`** para validar la frontera y, si se aprueba, actualizar el mapa de módulos en `CLAUDE.md` y `docs/README-pos.md`. Si se rechaza el módulo nuevo, la alternativa es mover `src/ventas/repositorio_sqlite.py` a `src/inventario/` (un único módulo de persistencia), sin cambios en `core` ni en los tests salvo el path de import.
