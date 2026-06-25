# E2 Inventario + E4 Venta por peso — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir el dominio estable de inventario (productos, catálogo, stock por diario de movimientos) y la venta por peso (`LectorPeso` + tres adaptadores + regla precio×peso), sobre el que después nacerá la UI de caja (E1).

**Architecture:** Hexagonal estricta. El dominio (`src/core/`) son entidades, invariantes, reglas y **puertos** (`typing.Protocol`), sin Qt ni SQLite. La persistencia vive solo en `src/inventario/` como adaptadores SQLite de esos puertos. La venta por peso es un único puerto `LectorPeso` en `core/perifericos/` con tres adaptadores intercambiables (manual, GS1, balanza serial); la decodificación GS1 y el cálculo precio×peso son lógica pura testeable sin hardware.

**Tech Stack:** Python 3.11+, stdlib `sqlite3` + `decimal` + `dataclasses` + `typing.Protocol`, `pyserial` (solo inyectado, no importado en core), `pytest`.

## Global Constraints

- **Python ≥ 3.11** — usar sintaxis `X | None` y `tuple[...]` nativos.
- **`src/core/` NO importa Qt ni SQLite ni pyserial.** Prohibido `import sqlite3`/`from PySide6`/`import serial` en cualquier archivo bajo `src/core/`. El periférico serial se recibe por inyección (objeto con `readline()`), nunca se importa.
- **SQL solo en adaptadores de repositorio** (`src/inventario/`). Nada de SQL en `core`/`caja`.
- **Dinero y cantidades con `decimal.Decimal`**, nunca `float`. Columnas SQLite declaradas `DECIMAL` con adapter/converter; el `SUM` de stock se hace en Python para no coercer a float.
- **Nombres de dominio en español** (`Producto`, `Impuesto`, `MovimientoInventario`, `LectorPeso`).
- **Entidades del dominio = `@dataclass(frozen=True)`**; puertos = `typing.Protocol`. Mutar = `dataclasses.replace`.
- **Tests:** `pytest`, `pythonpath = src` (ya configurado en `pytest.ini`); archivos `test_*.py`, estructura espejo por módulo. Imports tipo `from core.entidades import Producto`.
- **Ponytail/YAGNI:** mínimo código; no modelar `ajuste` de inventario, ni repos de `lotes`, ni nada de E1/E3/E5 todavía. La tabla `lotes` se crea (esquema) pero sin código.
- **Migraciones versionadas** en `scripts/migraciones/NNN_*.sql`; integridad referencial activa (`PRAGMA foreign_keys = ON`).

---

## File Structure

**E2 — Inventario**
- `src/core/entidades.py` — `Categoria`, `Impuesto`, `Producto`, `MovimientoInventario` (frozen dataclasses + invariantes).
- `src/core/puertos.py` — Protocols `RepositorioCategorias`, `RepositorioImpuestos`, `RepositorioProductos`, `RepositorioInventario`.
- `scripts/migraciones/001_inventario.sql` — esquema: `categorias`, `impuestos`, `productos`, `lotes`, `inventario_movimientos`.
- `src/inventario/db.py` — `conectar()` (PRAGMA + adapters Decimal) y `aplicar_migraciones()`.
- `src/inventario/repositorio_sqlite.py` — adaptadores SQLite de los cuatro puertos.
- `scripts/migrar.py` — CLI mínima que aplica las migraciones a una ruta de BD.
- `tests/core/test_entidades.py`, `tests/inventario/test_db.py`, `tests/inventario/test_repositorio_catalogo.py`, `tests/inventario/test_inventario_movimientos.py`, `tests/inventario/conftest.py`.

**E4 — Venta por peso**
- `src/core/calculos.py` — `subtotal_por_peso(precio_por_kg, peso_kg)`.
- `src/core/perifericos/lector_peso.py` — Protocol `LectorPeso` + adaptador `IngresoManual`.
- `src/core/perifericos/gs1.py` — `FormatoGS1`, `ResultadoGS1`, `decodificar_gs1()`, adaptador `CodigoPesoGS1`.
- `src/core/perifericos/balanza_serial.py` — adaptador `BalanzaSerial`.
- `tests/core/test_calculos.py`, `tests/core/perifericos/__init__.py`, `tests/core/perifericos/test_lector_manual.py`, `tests/core/perifericos/test_gs1.py`, `tests/core/perifericos/test_balanza_serial.py`, `tests/core/perifericos/test_tres_adaptadores.py`.

---

# Parte E2 — Inventario

### Task E2.1: Entidades de dominio + invariantes

**Files:**
- Create: `src/core/entidades.py`
- Test: `tests/core/test_entidades.py`

**Interfaces:**
- Produces:
  - `Categoria(nombre: str, id: int | None = None)`
  - `Impuesto(nombre: str, tarifa: Decimal, id: int | None = None, codigo_dian: str | None = None)`
  - `Producto(codigo_barras: str, nombre: str, precio: Decimal, vendido_por_peso: bool = False, unidad: str = "und", costo: Decimal = Decimal("0"), categoria_id: int | None = None, impuesto_id: int | None = None, id: int | None = None)`
  - `MovimientoInventario(producto_id: int, tipo: str, cantidad: Decimal, fecha: datetime, ref: str | None = None, lote_id: int | None = None, id: int | None = None)` — `tipo ∈ {"entrada","salida"}`, `cantidad > 0`.

- [ ] **Step 1: Write the failing test**

```python
# tests/core/test_entidades.py
from datetime import datetime
from decimal import Decimal

import pytest

from core.entidades import Categoria, Impuesto, Producto, MovimientoInventario


def test_producto_valido_se_construye():
    p = Producto(codigo_barras="7701234567890", nombre="Lomo", precio=Decimal("32000"),
                 vendido_por_peso=True, unidad="kg")
    assert p.vendido_por_peso is True
    assert p.id is None


def test_impuesto_tarifa_fuera_de_rango_falla():
    with pytest.raises(ValueError):
        Impuesto(nombre="IVA", tarifa=Decimal("1.5"))


def test_producto_precio_negativo_falla():
    with pytest.raises(ValueError):
        Producto(codigo_barras="x", nombre="malo", precio=Decimal("-1"))


def test_movimiento_cantidad_no_positiva_falla():
    with pytest.raises(ValueError):
        MovimientoInventario(producto_id=1, tipo="entrada", cantidad=Decimal("0"),
                             fecha=datetime(2026, 6, 25))


def test_movimiento_tipo_invalido_falla():
    with pytest.raises(ValueError):
        MovimientoInventario(producto_id=1, tipo="regalo", cantidad=Decimal("1"),
                             fecha=datetime(2026, 6, 25))


def test_categoria_minima():
    assert Categoria(nombre="Carnes").nombre == "Carnes"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_entidades.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'core.entidades'`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/core/entidades.py
"""Entidades de dominio del inventario. Python puro: sin Qt, sin SQLite."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

CERO = Decimal("0")
TIPOS_MOVIMIENTO = ("entrada", "salida")


@dataclass(frozen=True)
class Categoria:
    nombre: str
    id: int | None = None


@dataclass(frozen=True)
class Impuesto:
    nombre: str
    tarifa: Decimal  # fracción: 0.19 = IVA 19%
    id: int | None = None
    codigo_dian: str | None = None  # reservado DIAN, sin uso fiscal hoy

    def __post_init__(self) -> None:
        if not (CERO <= self.tarifa <= Decimal("1")):
            raise ValueError("tarifa debe estar entre 0 y 1")


@dataclass(frozen=True)
class Producto:
    codigo_barras: str
    nombre: str
    precio: Decimal
    vendido_por_peso: bool = False
    unidad: str = "und"  # "und" o "kg"
    costo: Decimal = CERO
    categoria_id: int | None = None
    impuesto_id: int | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        if self.precio < CERO:
            raise ValueError("precio no puede ser negativo")
        if self.costo < CERO:
            raise ValueError("costo no puede ser negativo")


@dataclass(frozen=True)
class MovimientoInventario:
    producto_id: int
    tipo: str  # "entrada" o "salida"; el signo del stock lo da el tipo
    cantidad: Decimal  # siempre positiva
    fecha: datetime
    ref: str | None = None
    lote_id: int | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        if self.tipo not in TIPOS_MOVIMIENTO:
            raise ValueError(f"tipo inválido: {self.tipo!r}")
        if self.cantidad <= CERO:
            raise ValueError("cantidad debe ser positiva")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_entidades.py -v`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add src/core/entidades.py tests/core/test_entidades.py
git commit -m "feat(core): entidades de inventario con invariantes"
```

---

### Task E2.2: Esquema SQLite, conexión y migraciones

**Files:**
- Create: `scripts/migraciones/001_inventario.sql`
- Create: `src/inventario/db.py`
- Create: `scripts/migrar.py`
- Test: `tests/inventario/test_db.py`

**Interfaces:**
- Produces:
  - `inventario.db.conectar(ruta: str = ":memory:") -> sqlite3.Connection` — con `row_factory=Row`, `PARSE_DECLTYPES`, `PRAGMA foreign_keys=ON`, y converter `DECIMAL`→`Decimal`.
  - `inventario.db.aplicar_migraciones(conn: sqlite3.Connection) -> None` — ejecuta en orden todos los `scripts/migraciones/*.sql`.

- [ ] **Step 1: Write the failing test**

```python
# tests/inventario/test_db.py
from inventario.db import conectar, aplicar_migraciones


def test_migraciones_crean_tablas_del_inventario():
    conn = conectar()  # :memory:
    aplicar_migraciones(conn)
    tablas = {fila["name"] for fila in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"categorias", "impuestos", "productos", "lotes",
            "inventario_movimientos"} <= tablas


def test_foreign_keys_activadas():
    conn = conectar()
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/inventario/test_db.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'inventario.db'`.

- [ ] **Step 3a: Write the schema**

```sql
-- scripts/migraciones/001_inventario.sql
-- Esquema inicial de inventario (E2). Tipos DECLARADOS para portabilidad SQLite->PostgreSQL.

CREATE TABLE IF NOT EXISTS categorias (
    id     INTEGER PRIMARY KEY,
    nombre TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS impuestos (
    id          INTEGER PRIMARY KEY,
    nombre      TEXT NOT NULL,
    tarifa      DECIMAL NOT NULL,
    codigo_dian TEXT            -- reservado DIAN
);

CREATE TABLE IF NOT EXISTS productos (
    id               INTEGER PRIMARY KEY,
    codigo_barras    TEXT NOT NULL UNIQUE,
    nombre           TEXT NOT NULL,
    precio           DECIMAL NOT NULL,
    costo            DECIMAL NOT NULL DEFAULT '0',
    categoria_id     INTEGER REFERENCES categorias(id),
    impuesto_id      INTEGER REFERENCES impuestos(id),
    vendido_por_peso INTEGER NOT NULL DEFAULT 0,  -- BOOL: 0/1
    unidad           TEXT NOT NULL DEFAULT 'und'
);

-- Definida ahora (carnicería/fruver la exigirá); código diferido (sin repositorio aún).
CREATE TABLE IF NOT EXISTS lotes (
    id                INTEGER PRIMARY KEY,
    producto_id       INTEGER NOT NULL REFERENCES productos(id),
    lote              TEXT NOT NULL,
    fecha_vencimiento TEXT,                        -- ISO-8601
    cantidad          DECIMAL NOT NULL DEFAULT '0'
);

CREATE TABLE IF NOT EXISTS inventario_movimientos (
    id          INTEGER PRIMARY KEY,
    producto_id INTEGER NOT NULL REFERENCES productos(id),
    lote_id     INTEGER REFERENCES lotes(id),
    tipo        TEXT NOT NULL CHECK (tipo IN ('entrada', 'salida')),
    cantidad    DECIMAL NOT NULL,
    fecha       TEXT NOT NULL,                     -- ISO-8601
    ref         TEXT
);
```

- [ ] **Step 3b: Write the connection helper**

```python
# src/inventario/db.py
"""Conexión SQLite y aplicación de migraciones. Único lugar con detalles de sqlite3."""
from __future__ import annotations

import sqlite3
from decimal import Decimal
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
DIR_MIGRACIONES = RAIZ / "scripts" / "migraciones"

# Dinero/cantidades viajan como texto exacto, no como float.
sqlite3.register_adapter(Decimal, str)
sqlite3.register_converter("DECIMAL", lambda b: Decimal(b.decode()))


def conectar(ruta: str = ":memory:") -> sqlite3.Connection:
    conn = sqlite3.connect(ruta, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def aplicar_migraciones(conn: sqlite3.Connection) -> None:
    for archivo in sorted(DIR_MIGRACIONES.glob("*.sql")):
        conn.executescript(archivo.read_text(encoding="utf-8"))
    conn.commit()
```

- [ ] **Step 3c: Write the CLI runner**

```python
# scripts/migrar.py
"""Aplica las migraciones SQLite a la ruta dada. Uso: python scripts/migrar.py pos.db"""
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "src"))

from inventario.db import conectar, aplicar_migraciones  # noqa: E402


def main(ruta: str) -> None:
    conn = conectar(ruta)
    aplicar_migraciones(conn)
    conn.close()
    print(f"Migraciones aplicadas en {ruta}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "pos.db")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/inventario/test_db.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add scripts/migraciones/001_inventario.sql src/inventario/db.py scripts/migrar.py tests/inventario/test_db.py
git commit -m "feat(inventario): esquema SQLite inicial + conexion y migraciones"
```

---

### Task E2.3: Puertos + adaptador SQLite de catálogo

**Files:**
- Create: `src/core/puertos.py`
- Create: `src/inventario/repositorio_sqlite.py`
- Create: `tests/inventario/conftest.py`
- Test: `tests/inventario/test_repositorio_catalogo.py`

**Interfaces:**
- Consumes: `Categoria`, `Impuesto`, `Producto` (Task E2.1); `conectar`, `aplicar_migraciones` (Task E2.2).
- Produces (Protocols en `core.puertos`):
  - `RepositorioCategorias.guardar(c: Categoria) -> Categoria`
  - `RepositorioImpuestos.guardar(i: Impuesto) -> Impuesto`
  - `RepositorioProductos.guardar(p: Producto) -> Producto`; `.por_id(id: int) -> Producto | None`; `.por_codigo(codigo_barras: str) -> Producto | None`; `.listar() -> list[Producto]`
- Produces (adaptadores en `inventario.repositorio_sqlite`): `RepositorioCategoriasSQLite`, `RepositorioImpuestosSQLite`, `RepositorioProductosSQLite` — cada uno `__init__(self, conn: sqlite3.Connection)`.
- Produces (fixture): `conn` en `tests/inventario/conftest.py` — conexión `:memory:` ya migrada.

- [ ] **Step 1: Write the shared fixture**

```python
# tests/inventario/conftest.py
import pytest

from inventario.db import conectar, aplicar_migraciones


@pytest.fixture
def conn():
    c = conectar()  # :memory:
    aplicar_migraciones(c)
    yield c
    c.close()
```

- [ ] **Step 2: Write the failing test**

```python
# tests/inventario/test_repositorio_catalogo.py
from decimal import Decimal

import pytest

from core.entidades import Categoria, Impuesto, Producto
from inventario.repositorio_sqlite import (
    RepositorioCategoriasSQLite,
    RepositorioImpuestosSQLite,
    RepositorioProductosSQLite,
)


def _seed_producto(conn, **extra) -> Producto:
    cat = RepositorioCategoriasSQLite(conn).guardar(Categoria(nombre="Carnes"))
    imp = RepositorioImpuestosSQLite(conn).guardar(Impuesto(nombre="IVA", tarifa=Decimal("0.19")))
    base = dict(codigo_barras="7701234567890", nombre="Lomo", precio=Decimal("32000"),
                costo=Decimal("21000"), categoria_id=cat.id, impuesto_id=imp.id,
                vendido_por_peso=True, unidad="kg")
    base.update(extra)
    return RepositorioProductosSQLite(conn).guardar(Producto(**base))


def test_alta_de_producto_asigna_id(conn):
    p = _seed_producto(conn)
    assert p.id is not None


def test_consulta_por_id_devuelve_decimales_exactos(conn):
    guardado = _seed_producto(conn)
    repo = RepositorioProductosSQLite(conn)
    leido = repo.por_id(guardado.id)
    assert leido.precio == Decimal("32000")
    assert leido.vendido_por_peso is True
    assert leido.unidad == "kg"


def test_consulta_por_codigo_de_barras(conn):
    _seed_producto(conn)
    repo = RepositorioProductosSQLite(conn)
    assert repo.por_codigo("7701234567890").nombre == "Lomo"
    assert repo.por_codigo("noexiste") is None


def test_listar_devuelve_todos(conn):
    _seed_producto(conn)
    _seed_producto(conn, codigo_barras="7700000000001", nombre="Manzana",
                   vendido_por_peso=True)
    assert len(RepositorioProductosSQLite(conn).listar()) == 2


def test_fk_invalida_es_rechazada(conn):
    import sqlite3
    with pytest.raises(sqlite3.IntegrityError):
        RepositorioProductosSQLite(conn).guardar(
            Producto(codigo_barras="x", nombre="huérfano", precio=Decimal("1"),
                     categoria_id=999))
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/inventario/test_repositorio_catalogo.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'inventario.repositorio_sqlite'`.

- [ ] **Step 4a: Write the ports**

```python
# src/core/puertos.py
"""Puertos (interfaces) del dominio. Implementados por adaptadores fuera de core."""
from __future__ import annotations

from decimal import Decimal
from typing import Protocol

from core.entidades import Categoria, Impuesto, MovimientoInventario, Producto


class RepositorioCategorias(Protocol):
    def guardar(self, categoria: Categoria) -> Categoria: ...


class RepositorioImpuestos(Protocol):
    def guardar(self, impuesto: Impuesto) -> Impuesto: ...


class RepositorioProductos(Protocol):
    def guardar(self, producto: Producto) -> Producto: ...
    def por_id(self, id: int) -> Producto | None: ...
    def por_codigo(self, codigo_barras: str) -> Producto | None: ...
    def listar(self) -> list[Producto]: ...


class RepositorioInventario(Protocol):
    def registrar(self, movimiento: MovimientoInventario) -> MovimientoInventario: ...
    def stock_de(self, producto_id: int) -> Decimal: ...
```

- [ ] **Step 4b: Write the catalog adapters**

```python
# src/inventario/repositorio_sqlite.py
"""Adaptadores SQLite de los repositorios. Único lugar con SQL del inventario."""
from __future__ import annotations

import sqlite3
from dataclasses import replace

from core.entidades import Categoria, Impuesto, Producto


class RepositorioCategoriasSQLite:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def guardar(self, categoria: Categoria) -> Categoria:
        cur = self._conn.execute(
            "INSERT INTO categorias (nombre) VALUES (?)", (categoria.nombre,))
        self._conn.commit()
        return replace(categoria, id=cur.lastrowid)


class RepositorioImpuestosSQLite:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def guardar(self, impuesto: Impuesto) -> Impuesto:
        cur = self._conn.execute(
            "INSERT INTO impuestos (nombre, tarifa, codigo_dian) VALUES (?, ?, ?)",
            (impuesto.nombre, impuesto.tarifa, impuesto.codigo_dian))
        self._conn.commit()
        return replace(impuesto, id=cur.lastrowid)


def _fila_a_producto(f: sqlite3.Row) -> Producto:
    return Producto(
        codigo_barras=f["codigo_barras"],
        nombre=f["nombre"],
        precio=f["precio"],
        vendido_por_peso=bool(f["vendido_por_peso"]),
        unidad=f["unidad"],
        costo=f["costo"],
        categoria_id=f["categoria_id"],
        impuesto_id=f["impuesto_id"],
        id=f["id"],
    )


class RepositorioProductosSQLite:
    _COLS = ("codigo_barras, nombre, precio, costo, categoria_id, impuesto_id, "
             "vendido_por_peso, unidad")

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def guardar(self, producto: Producto) -> Producto:
        cur = self._conn.execute(
            f"INSERT INTO productos ({self._COLS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (producto.codigo_barras, producto.nombre, producto.precio, producto.costo,
             producto.categoria_id, producto.impuesto_id,
             int(producto.vendido_por_peso), producto.unidad))
        self._conn.commit()
        return replace(producto, id=cur.lastrowid)

    def por_id(self, id: int) -> Producto | None:
        f = self._conn.execute("SELECT * FROM productos WHERE id = ?", (id,)).fetchone()
        return _fila_a_producto(f) if f else None

    def por_codigo(self, codigo_barras: str) -> Producto | None:
        f = self._conn.execute(
            "SELECT * FROM productos WHERE codigo_barras = ?", (codigo_barras,)).fetchone()
        return _fila_a_producto(f) if f else None

    def listar(self) -> list[Producto]:
        filas = self._conn.execute("SELECT * FROM productos ORDER BY id").fetchall()
        return [_fila_a_producto(f) for f in filas]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/inventario/test_repositorio_catalogo.py -v`
Expected: PASS (5 passed).

- [ ] **Step 6: Commit**

```bash
git add src/core/puertos.py src/inventario/repositorio_sqlite.py tests/inventario/conftest.py tests/inventario/test_repositorio_catalogo.py
git commit -m "feat(inventario): puertos de repositorio y adaptador SQLite de catalogo"
```

---

### Task E2.4: Repositorio de inventario y stock (descuento de venta)

**Files:**
- Modify: `src/inventario/repositorio_sqlite.py` (añadir `RepositorioInventarioSQLite`)
- Test: `tests/inventario/test_inventario_movimientos.py`

**Interfaces:**
- Consumes: `MovimientoInventario` (Task E2.1); fixture `conn` (Task E2.3); `RepositorioProductosSQLite` (Task E2.3).
- Produces: `RepositorioInventarioSQLite(conn)` que cumple `RepositorioInventario`:
  - `.registrar(m: MovimientoInventario) -> MovimientoInventario`
  - `.stock_de(producto_id: int) -> Decimal` — `Σ entradas − Σ salidas`, sumado en Python (exacto).

- [ ] **Step 1: Write the failing test**

```python
# tests/inventario/test_inventario_movimientos.py
from datetime import datetime
from decimal import Decimal

from core.entidades import Categoria, MovimientoInventario, Producto
from inventario.repositorio_sqlite import (
    RepositorioCategoriasSQLite,
    RepositorioInventarioSQLite,
    RepositorioProductosSQLite,
)


def _producto(conn) -> Producto:
    cat = RepositorioCategoriasSQLite(conn).guardar(Categoria(nombre="Carnes"))
    return RepositorioProductosSQLite(conn).guardar(
        Producto(codigo_barras="7701", nombre="Lomo", precio=Decimal("32000"),
                 categoria_id=cat.id, vendido_por_peso=True, unidad="kg"))


def test_stock_sin_movimientos_es_cero(conn):
    p = _producto(conn)
    assert RepositorioInventarioSQLite(conn).stock_de(p.id) == Decimal("0")


def test_entrada_suma_y_salida_descuenta_stock(conn):
    p = _producto(conn)
    repo = RepositorioInventarioSQLite(conn)
    repo.registrar(MovimientoInventario(producto_id=p.id, tipo="entrada",
                                        cantidad=Decimal("10.5"), fecha=datetime(2026, 6, 25)))
    repo.registrar(MovimientoInventario(producto_id=p.id, tipo="salida",
                                        cantidad=Decimal("2.250"), fecha=datetime(2026, 6, 25),
                                        ref="venta#1"))
    assert repo.stock_de(p.id) == Decimal("8.250")  # exacto, sin float


def test_registrar_asigna_id(conn):
    p = _producto(conn)
    m = RepositorioInventarioSQLite(conn).registrar(
        MovimientoInventario(producto_id=p.id, tipo="entrada",
                             cantidad=Decimal("1"), fecha=datetime(2026, 6, 25)))
    assert m.id is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/inventario/test_inventario_movimientos.py -v`
Expected: FAIL con `ImportError: cannot import name 'RepositorioInventarioSQLite'`.

- [ ] **Step 3: Add the adapter**

Append to `src/inventario/repositorio_sqlite.py`:

```python
from decimal import Decimal  # añadir al bloque de imports superior

from core.entidades import MovimientoInventario  # añadir al import de core.entidades


class RepositorioInventarioSQLite:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def registrar(self, m: MovimientoInventario) -> MovimientoInventario:
        cur = self._conn.execute(
            "INSERT INTO inventario_movimientos "
            "(producto_id, lote_id, tipo, cantidad, fecha, ref) VALUES (?, ?, ?, ?, ?, ?)",
            (m.producto_id, m.lote_id, m.tipo, m.cantidad, m.fecha.isoformat(), m.ref))
        self._conn.commit()
        return replace(m, id=cur.lastrowid)

    def stock_de(self, producto_id: int) -> Decimal:
        filas = self._conn.execute(
            "SELECT tipo, cantidad FROM inventario_movimientos WHERE producto_id = ?",
            (producto_id,)).fetchall()
        total = Decimal("0")
        for f in filas:
            total += f["cantidad"] if f["tipo"] == "entrada" else -f["cantidad"]
        return total
```

> Nota: consolidar los imports (`from decimal import Decimal`, `from core.entidades import Categoria, Impuesto, MovimientoInventario, Producto`) en el bloque existente al inicio del archivo, no duplicarlos.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/inventario/test_inventario_movimientos.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add src/inventario/repositorio_sqlite.py tests/inventario/test_inventario_movimientos.py
git commit -m "feat(inventario): movimientos y stock por diario (entrada/salida)"
```

---

# Parte E4 — Venta por peso

### Task E4.1: Regla de dominio precio×peso

**Files:**
- Create: `src/core/calculos.py`
- Test: `tests/core/test_calculos.py`

**Interfaces:**
- Produces: `core.calculos.subtotal_por_peso(precio_por_kg: Decimal, peso_kg: Decimal) -> Decimal` — redondeo a peso colombiano (entero), `ROUND_HALF_UP`; rechaza negativos.

- [ ] **Step 1: Write the failing test**

```python
# tests/core/test_calculos.py
from decimal import Decimal

import pytest

from core.calculos import subtotal_por_peso


def test_precio_por_peso_basico():
    assert subtotal_por_peso(Decimal("12000"), Decimal("1.234")) == Decimal("14808")


def test_redondea_a_pesos_enteros_half_up():
    # 1000 * 0.3335 = 333.5 -> 334
    assert subtotal_por_peso(Decimal("1000"), Decimal("0.3335")) == Decimal("334")


def test_peso_cero_da_cero():
    assert subtotal_por_peso(Decimal("32000"), Decimal("0")) == Decimal("0")


def test_negativos_fallan():
    with pytest.raises(ValueError):
        subtotal_por_peso(Decimal("-1"), Decimal("1"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_calculos.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'core.calculos'`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/core/calculos.py
"""Reglas de cálculo del dominio. Python puro."""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

CERO = Decimal("0")


def subtotal_por_peso(precio_por_kg: Decimal, peso_kg: Decimal) -> Decimal:
    """Subtotal de una línea vendida por peso, redondeado a pesos colombianos (enteros)."""
    if precio_por_kg < CERO or peso_kg < CERO:
        raise ValueError("precio y peso deben ser no negativos")
    return (precio_por_kg * peso_kg).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_calculos.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add src/core/calculos.py tests/core/test_calculos.py
git commit -m "feat(core): regla de dominio precio x peso (redondeo COP)"
```

---

### Task E4.2: Puerto LectorPeso + adaptador IngresoManual

**Files:**
- Create: `src/core/perifericos/lector_peso.py`
- Create: `tests/core/perifericos/__init__.py`
- Test: `tests/core/perifericos/test_lector_manual.py`

**Interfaces:**
- Consumes: `subtotal_por_peso` (Task E4.1).
- Produces:
  - `LectorPeso` (Protocol): `.leer_peso() -> Decimal` (kg).
  - `IngresoManual(peso_kg: Decimal)` — adaptador fallback sin hardware; rechaza negativos.

- [ ] **Step 1: Create the test package marker**

```python
# tests/core/perifericos/__init__.py
```
(archivo vacío)

- [ ] **Step 2: Write the failing test**

```python
# tests/core/perifericos/test_lector_manual.py
from decimal import Decimal

import pytest

from core.calculos import subtotal_por_peso
from core.perifericos.lector_peso import IngresoManual, LectorPeso


def test_ingreso_manual_devuelve_el_peso():
    lector: LectorPeso = IngresoManual(Decimal("1.234"))
    assert lector.leer_peso() == Decimal("1.234")


def test_ingreso_manual_rechaza_negativo():
    with pytest.raises(ValueError):
        IngresoManual(Decimal("-0.5"))


def test_subtotal_con_lector_manual():
    lector = IngresoManual(Decimal("2.5"))
    assert subtotal_por_peso(Decimal("32000"), lector.leer_peso()) == Decimal("80000")
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/core/perifericos/test_lector_manual.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'core.perifericos.lector_peso'`.

- [ ] **Step 4: Write minimal implementation**

```python
# src/core/perifericos/lector_peso.py
"""Puerto LectorPeso y adaptador manual. Sin hardware, sin Qt."""
from __future__ import annotations

from decimal import Decimal
from typing import Protocol

CERO = Decimal("0")


class LectorPeso(Protocol):
    def leer_peso(self) -> Decimal:
        """Peso en kilogramos del ítem a vender."""
        ...


class IngresoManual:
    """Fallback sin balanza: el cajero teclea el peso."""

    def __init__(self, peso_kg: Decimal) -> None:
        if peso_kg < CERO:
            raise ValueError("peso no puede ser negativo")
        self._peso = peso_kg

    def leer_peso(self) -> Decimal:
        return self._peso
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/core/perifericos/test_lector_manual.py -v`
Expected: PASS (3 passed).

- [ ] **Step 6: Commit**

```bash
git add src/core/perifericos/lector_peso.py tests/core/perifericos/__init__.py tests/core/perifericos/test_lector_manual.py
git commit -m "feat(perifericos): puerto LectorPeso y adaptador IngresoManual"
```

---

### Task E4.3: Decodificación GS1 + adaptador CodigoPesoGS1

**Files:**
- Create: `src/core/perifericos/gs1.py`
- Test: `tests/core/perifericos/test_gs1.py`

**Interfaces:**
- Consumes: `LectorPeso` (Task E4.2, cumplido estructuralmente).
- Produces:
  - `FormatoGS1(prefijos=("2",), ini_codigo=1, fin_codigo=6, ini_valor=7, fin_valor=12, decimales_valor=3)` y `FORMATO_PESO_DEFECTO`.
  - `ResultadoGS1(codigo_producto: str, peso_kg: Decimal)`.
  - `decodificar_gs1(codigo: str, formato: FormatoGS1 = FORMATO_PESO_DEFECTO) -> ResultadoGS1` — valida longitud 13, dígitos, prefijo y dígito de control EAN-13.
  - `CodigoPesoGS1(codigo: str, formato=FORMATO_PESO_DEFECTO)` — adaptador `LectorPeso`; expone `.codigo_producto` y `.leer_peso()`.

**Formato GS1 por defecto** (EAN-13 de peso variable, estilo Chromis, prefijo `2`):
`P IIIII V WWWWW C` → `[0]` prefijo, `[1:6]` código producto (5), `[6]` dígito de control interno (ignorado), `[7:12]` peso en gramos (5 → kg con 3 decimales), `[12]` dígito de control EAN-13.
Ejemplo verificado: `"2012340012344"` → `codigo_producto="01234"`, `peso_kg=Decimal("1.234")`.

- [ ] **Step 1: Write the failing test**

```python
# tests/core/perifericos/test_gs1.py
from decimal import Decimal

import pytest

from core.perifericos.gs1 import CodigoPesoGS1, decodificar_gs1


def test_decodifica_codigo_y_peso():
    r = decodificar_gs1("2012340012344")
    assert r.codigo_producto == "01234"
    assert r.peso_kg == Decimal("1.234")


def test_digito_de_control_invalido_falla():
    with pytest.raises(ValueError):
        decodificar_gs1("2012340012340")  # último dígito incorrecto


def test_prefijo_no_de_peso_falla():
    with pytest.raises(ValueError):
        decodificar_gs1("3012340012344")  # no empieza por 2


def test_longitud_invalida_falla():
    with pytest.raises(ValueError):
        decodificar_gs1("20123")


def test_adaptador_cumple_lector_peso():
    lector = CodigoPesoGS1("2012340012344")
    assert lector.leer_peso() == Decimal("1.234")
    assert lector.codigo_producto == "01234"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/core/perifericos/test_gs1.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'core.perifericos.gs1'`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/core/perifericos/gs1.py
"""Decodificación de códigos GS1 de peso variable (EAN-13) y adaptador LectorPeso."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class FormatoGS1:
    prefijos: tuple[str, ...] = ("2",)  # primer dígito que marca peso variable
    ini_codigo: int = 1
    fin_codigo: int = 6   # codigo = ean[ini_codigo:fin_codigo] (5 dígitos)
    ini_valor: int = 7
    fin_valor: int = 12   # peso en gramos = ean[ini_valor:fin_valor] (5 dígitos)
    decimales_valor: int = 3  # gramos -> kg


FORMATO_PESO_DEFECTO = FormatoGS1()


@dataclass(frozen=True)
class ResultadoGS1:
    codigo_producto: str
    peso_kg: Decimal


def _digito_control_ean13(doce: str) -> int:
    suma = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(doce))
    return (10 - suma % 10) % 10


def decodificar_gs1(codigo: str, formato: FormatoGS1 = FORMATO_PESO_DEFECTO) -> ResultadoGS1:
    if len(codigo) != 13 or not codigo.isdigit():
        raise ValueError(f"EAN-13 inválido: {codigo!r}")
    if codigo[0] not in formato.prefijos:
        raise ValueError(f"prefijo {codigo[0]!r} no es de peso variable")
    if _digito_control_ean13(codigo[:12]) != int(codigo[12]):
        raise ValueError("dígito de control EAN-13 incorrecto")
    crudo = codigo[formato.ini_valor:formato.fin_valor]
    peso_kg = Decimal(crudo) / (Decimal(10) ** formato.decimales_valor)
    return ResultadoGS1(codigo[formato.ini_codigo:formato.fin_codigo], peso_kg)


class CodigoPesoGS1:
    """Adaptador LectorPeso: obtiene el peso de un código GS1 ya escaneado."""

    def __init__(self, codigo: str, formato: FormatoGS1 = FORMATO_PESO_DEFECTO) -> None:
        self._resultado = decodificar_gs1(codigo, formato)

    @property
    def codigo_producto(self) -> str:
        return self._resultado.codigo_producto

    def leer_peso(self) -> Decimal:
        return self._resultado.peso_kg
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/core/perifericos/test_gs1.py -v`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add src/core/perifericos/gs1.py tests/core/perifericos/test_gs1.py
git commit -m "feat(perifericos): decodificacion GS1 de peso variable y adaptador CodigoPesoGS1"
```

---

### Task E4.4: Adaptador BalanzaSerial

**Files:**
- Create: `src/core/perifericos/balanza_serial.py`
- Test: `tests/core/perifericos/test_balanza_serial.py`

**Interfaces:**
- Consumes: `LectorPeso` (Task E4.2, cumplido estructuralmente).
- Produces: `BalanzaSerial(puerto, parsear=_parsear_peso)` — `puerto` es cualquier objeto con `readline() -> bytes` (en producción `serial.Serial`, inyectado por el composition root; **no se importa pyserial aquí**). `parsear` es opcional para protocolos de balanza distintos. Default `_parsear_peso`: extrae el primer número decimal de la trama y lo trata como kg.

- [ ] **Step 1: Write the failing test**

```python
# tests/core/perifericos/test_balanza_serial.py
from decimal import Decimal

import pytest

from core.perifericos.balanza_serial import BalanzaSerial


class _SerialFake:
    def __init__(self, trama: bytes) -> None:
        self._trama = trama

    def readline(self) -> bytes:
        return self._trama


def test_lee_peso_de_trama_continua():
    balanza = BalanzaSerial(_SerialFake(b"ST,GS,+001.234kg\r\n"))
    assert balanza.leer_peso() == Decimal("1.234")


def test_trama_sin_peso_falla():
    with pytest.raises(ValueError):
        BalanzaSerial(_SerialFake(b"ST,US,error\r\n")).leer_peso()


def test_parser_personalizado():
    balanza = BalanzaSerial(_SerialFake(b"PESO=2500g"),
                            parsear=lambda t: Decimal(t.split(b"=")[1][:-1].decode()) / 1000)
    assert balanza.leer_peso() == Decimal("2.5")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/core/perifericos/test_balanza_serial.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'core.perifericos.balanza_serial'`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/core/perifericos/balanza_serial.py
"""Adaptador LectorPeso sobre balanza serial. pyserial se inyecta, no se importa."""
from __future__ import annotations

import re
from decimal import Decimal
from typing import Callable, Protocol

_NUMERO = re.compile(rb"[-+]?\d+\.\d+")


class _PuertoSerial(Protocol):
    def readline(self) -> bytes: ...


def _parsear_peso(trama: bytes) -> Decimal:
    """Extrae el primer número decimal de la trama (kg). Formato continuo común."""
    m = _NUMERO.search(trama)
    if not m:
        raise ValueError(f"trama de balanza sin peso: {trama!r}")
    return Decimal(m.group().decode())


class BalanzaSerial:
    def __init__(self, puerto: _PuertoSerial,
                 parsear: Callable[[bytes], Decimal] = _parsear_peso) -> None:
        self._puerto = puerto
        self._parsear = parsear

    def leer_peso(self) -> Decimal:
        return self._parsear(self._puerto.readline())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/core/perifericos/test_balanza_serial.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add src/core/perifericos/balanza_serial.py tests/core/perifericos/test_balanza_serial.py
git commit -m "feat(perifericos): adaptador BalanzaSerial (pyserial inyectado)"
```

---

### Task E4.5: Flujo crítico — precio×peso por los tres adaptadores

> Cierra el flujo crítico #2 de `testing-pos` ("venta por peso por los tres adaptadores") en una sola prueba parametrizada que demuestra la intercambiabilidad del puerto `LectorPeso`.

**Files:**
- Test: `tests/core/perifericos/test_tres_adaptadores.py`

**Interfaces:**
- Consumes: `IngresoManual`, `CodigoPesoGS1`, `BalanzaSerial`, `subtotal_por_peso`.

- [ ] **Step 1: Write the test**

```python
# tests/core/perifericos/test_tres_adaptadores.py
from decimal import Decimal

import pytest

from core.calculos import subtotal_por_peso
from core.perifericos.balanza_serial import BalanzaSerial
from core.perifericos.gs1 import CodigoPesoGS1
from core.perifericos.lector_peso import IngresoManual, LectorPeso


class _SerialFake:
    def readline(self) -> bytes:
        return b"ST,GS,+001.234kg\r\n"


@pytest.mark.parametrize("lector", [
    IngresoManual(Decimal("1.234")),
    CodigoPesoGS1("2012340012344"),
    BalanzaSerial(_SerialFake()),
])
def test_precio_por_peso_es_independiente_del_adaptador(lector: LectorPeso):
    # Mismo peso (1.234 kg) por cualquiera de los tres caminos -> mismo subtotal.
    assert subtotal_por_peso(Decimal("12000"), lector.leer_peso()) == Decimal("14808")
```

- [ ] **Step 2: Run the test**

Run: `pytest tests/core/perifericos/test_tres_adaptadores.py -v`
Expected: PASS (3 passed — uno por adaptador).

- [ ] **Step 3: Run the full suite**

Run: `pytest -v`
Expected: PASS (todos los tests de E2 + E4 verdes).

- [ ] **Step 4: Commit**

```bash
git add tests/core/perifericos/test_tres_adaptadores.py
git commit -m "test(perifericos): flujo critico precio x peso por los tres adaptadores"
```

---

## Definición de "hecho" (E2 + E4)

- `pytest -v` en verde, sin SQL fuera de `src/inventario/`, sin imports de Qt/SQLite/pyserial dentro de `src/core/`.
- `python scripts/migrar.py pos.db` crea la BD con las cinco tablas de inventario.
- El puerto `LectorPeso` tiene tres adaptadores intercambiables probados contra la misma regla `subtotal_por_peso`.
- Queda listo el dominio estable sobre el que E1 (UI de caja) construirá `Venta`/`LineaVenta`.

## Self-Review (cobertura del spec y del roadmap)

| Requisito (roadmap / spec) | Task |
|---|---|
| Entidades `Producto`, `Categoria`, `Impuesto` en core sin DB | E2.1 |
| Puerto `RepositorioProductos` en core | E2.3 |
| Tablas `productos`, `categorias`, `impuestos`, `inventario_movimientos` | E2.2 |
| Tabla `lotes` definida ahora, código diferido | E2.2 (esquema; sin repo) |
| Adaptador SQLite + migración inicial en `scripts/` | E2.2, E2.3, E2.4 |
| Tests: alta de producto, consulta, descuento de stock | E2.3, E2.4 |
| Integridad referencial (`PRAGMA foreign_keys`) | E2.2 (+ test FK en E2.3) |
| Puerto `LectorPeso` en `core/perifericos/` | E4.2 |
| Adaptador `IngresoManual` | E4.2 |
| Adaptador `CodigoPesoGS1` (EAN-13 peso/precio) | E4.3 |
| Adaptador `BalanzaSerial` (pyserial inyectado) | E4.4 |
| Regla de dominio `precio × peso` en core | E4.1 |
| Tests: precio×peso por los tres adaptadores | E4.5 |
| Dinero/cantidades con `Decimal` exacto | Constraint global; E2.2, E2.4 |
| core sin Qt/SQLite/pyserial | Constraint global; E4.4 (inyección) |

**Diferido a propósito (YAGNI):** repos de `lotes`, movimiento `ajuste`, tablas de `ventas`/`caja`/`pagos`/`clientes`/`usuarios`/`outbox` (entran con E1/E3/E6/E8), cálculo de impuestos por línea (E1), `param_dian_*` (E5).
