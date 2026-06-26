# Rediseño UI completo — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir la UI completa y ejecutable del POS: app con icon rail + 6 pantallas (Venta, Inventario, Clientes, Devoluciones, Reportes, Cierre), tema dark navy, sobre la lógica de dominio ya existente.

**Architecture:** Hexagonal estricta. Toda la UI vive en `src/caja/`, accede a datos solo vía servicios/repos inyectados desde un `ContextoApp` (composition root). `core` no cambia salvo ampliar firmas `Protocol`. Estilo 100% en `src/caja/tema.qss` (sin estilos inline, sin `paintEvent`).

**Tech Stack:** Python 3.11+, PySide6 (Qt6), SQLite (stdlib `sqlite3`), pytest. Sin dependencias nuevas.

## Global Constraints

- `src/core/` NO importa Qt ni SQLite. (verbatim del CLAUDE.md)
- SQL solo en adaptadores de repositorio. Prohibido SQL fuera de ellos.
- Sin dependencias nuevas fuera de PySide6 ya instalado.
- Sin animaciones (hardware viejo). Sin QtWebEngine. Sin `paintEvent` custom.
- Estilo solo en `src/caja/tema.qss`.
- Nombres de dominio en español.
- Tests Qt corren headless: cada test Qt empieza con
  `pytest.importorskip("PySide6")` y `os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")`,
  y obtiene la app con `QApplication.instance() or QApplication([])`.
- No romper los 140 tests existentes (suite: `pytest`).
- Dinero/cantidades son `Decimal`, nunca `float` en lógica (los `QDoubleSpinBox`
  de UI se convierten a `Decimal(str(spin.value()))` al cruzar a dominio).

---

## File Structure

| Archivo | Responsabilidad |
|---|---|
| `src/core/puertos.py` | (MOD) ampliar 4 Protocol con métodos de lectura/actualización |
| `src/inventario/repositorio_sqlite.py` | (MOD) impl. `categorias.listar/por_id`, `impuestos.listar`, `productos.actualizar` |
| `src/ventas/repositorio_sqlite.py` | (MOD) impl. `RepositorioCajaSesionesSQLite.listar()` |
| `src/caja/formato.py` | (NEW) helpers de formato moneda/cantidad/fecha |
| `src/caja/bootstrap.py` | (NEW) conexión + migraciones + seed demo idempotente |
| `src/caja/contexto.py` | (NEW) `ContextoApp`: repos + servicios |
| `src/caja/tema.qss` | (NEW) hoja de estilo dark navy |
| `src/caja/tema.py` | (NEW) `carga_tema(app)` |
| `src/caja/recursos/iconos/*.svg` | (NEW) 6 iconos del rail |
| `src/caja/widgets.py` | (NEW) `TarjetaProducto`, `TarjetaKpi`, `BotonRail` |
| `src/caja/dialogos/dialogo_cobro.py` | (NEW) selector multi-medio (cobro/reembolso) |
| `src/caja/dialogos/dialogo_producto.py` | (NEW) crear/editar producto |
| `src/caja/dialogos/dialogo_movimiento.py` | (NEW) movimiento de inventario |
| `src/caja/pantalla_venta.py` | (REWRITE) catálogo + carrito + cobro |
| `src/caja/pantalla_inventario.py` | (NEW) tabla productos + stock + acciones |
| `src/caja/pantalla_clientes.py` | (REWRITE) tabla + form crear/editar |
| `src/caja/pantalla_devoluciones.py` | (NEW) buscar venta + devolver líneas |
| `src/caja/pantalla_cierre.py` | (NEW) abrir/arqueo/cerrar caja |
| `src/caja/pantalla_reportes.py` | (NEW) ventas/inventario/cierre |
| `src/caja/ventana_principal.py` | (NEW) shell: rail + stack + status bar |
| `src/caja/__main__.py` | (NEW) entry point `python -m caja` |
| `scripts/caja.py` | (MOD) delegar a `caja.__main__` |

Tests espejo en `tests/inventario/`, `tests/caja/`.

**Cross-screen contract:** pantallas que cambian el estado de caja exponen una señal Qt
`caja_cambiada = Signal()`. La `VentanaPrincipal` la conecta para refrescar la barra de
estado. Pantallas que necesitan la sesión abierta la consultan con `ctx.repo_sesiones.abierta()`.
Cada pantalla expone `al_mostrar()` (recarga datos al entrar; no-op si no aplica).

**Nota sobre `ServicioVenta`:** es stateful (acumula líneas). `ContextoApp` NO guarda una
instancia compartida; `PantallaVenta` construye la suya desde los repos y la reemplaza tras
cada cobro.

---

## Task 1: Extensiones de puertos + adaptadores SQLite

**Files:**
- Modify: `src/core/puertos.py`
- Modify: `src/inventario/repositorio_sqlite.py`
- Modify: `src/ventas/repositorio_sqlite.py`
- Test: `tests/inventario/test_repositorio_extensiones.py` (create)
- Test: `tests/ventas/test_sesiones_listar.py` (create)

**Interfaces:**
- Produces:
  - `RepositorioCategoriasSQLite.listar() -> list[Categoria]`
  - `RepositorioCategoriasSQLite.por_id(id: int) -> Categoria | None`
  - `RepositorioImpuestosSQLite.listar() -> list[Impuesto]`
  - `RepositorioProductosSQLite.actualizar(producto: Producto) -> Producto`
  - `RepositorioCajaSesionesSQLite.listar() -> list[CajaSesion]`

- [ ] **Step 1: Write the failing test (inventario)**

Create `tests/inventario/test_repositorio_extensiones.py`:

```python
from decimal import Decimal

from dataclasses import replace

from core.entidades import Categoria, Impuesto, Producto
from inventario.repositorio_sqlite import (
    RepositorioCategoriasSQLite, RepositorioImpuestosSQLite, RepositorioProductosSQLite,
)


def test_categorias_listar_y_por_id(conn):
    repo = RepositorioCategoriasSQLite(conn)
    a = repo.guardar(Categoria(nombre="Carnes"))
    b = repo.guardar(Categoria(nombre="Frutas"))
    nombres = [c.nombre for c in repo.listar()]
    assert nombres == ["Carnes", "Frutas"]
    assert repo.por_id(a.id).nombre == "Carnes"
    assert repo.por_id(999) is None


def test_impuestos_listar(conn):
    repo = RepositorioImpuestosSQLite(conn)
    repo.guardar(Impuesto(nombre="IVA 0", tarifa=Decimal("0")))
    repo.guardar(Impuesto(nombre="IVA 19", tarifa=Decimal("0.19")))
    assert [i.nombre for i in repo.listar()] == ["IVA 0", "IVA 19"]


def test_productos_actualizar(conn):
    repo = RepositorioProductosSQLite(conn)
    p = repo.guardar(Producto(codigo_barras="B1", nombre="Manzana", precio=Decimal("1000")))
    modificado = repo.actualizar(replace(p, nombre="Manzana Roja", precio=Decimal("1200")))
    assert modificado.nombre == "Manzana Roja"
    leido = repo.por_id(p.id)
    assert leido.nombre == "Manzana Roja"
    assert leido.precio == Decimal("1200")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/inventario/test_repositorio_extensiones.py -v`
Expected: FAIL con `AttributeError: 'RepositorioCategoriasSQLite' object has no attribute 'listar'`

- [ ] **Step 3: Implement adapters (inventario)**

En `src/inventario/repositorio_sqlite.py`, dentro de `RepositorioCategoriasSQLite` añade:

```python
    def por_id(self, id: int) -> Categoria | None:
        f = self._conn.execute("SELECT * FROM categorias WHERE id = ?", (id,)).fetchone()
        return Categoria(nombre=f["nombre"], id=f["id"]) if f else None

    def listar(self) -> list[Categoria]:
        filas = self._conn.execute("SELECT * FROM categorias ORDER BY id").fetchall()
        return [Categoria(nombre=f["nombre"], id=f["id"]) for f in filas]
```

Dentro de `RepositorioImpuestosSQLite` añade:

```python
    def listar(self) -> list[Impuesto]:
        filas = self._conn.execute("SELECT * FROM impuestos ORDER BY id").fetchall()
        return [Impuesto(nombre=f["nombre"], tarifa=f["tarifa"],
                         codigo_dian=f["codigo_dian"], id=f["id"]) for f in filas]
```

Dentro de `RepositorioProductosSQLite` añade:

```python
    def actualizar(self, producto: Producto) -> Producto:
        cur = self._conn.execute(
            "UPDATE productos SET codigo_barras = ?, nombre = ?, precio = ?, costo = ?, "
            "categoria_id = ?, impuesto_id = ?, vendido_por_peso = ?, unidad = ? WHERE id = ?",
            (producto.codigo_barras, producto.nombre, producto.precio, producto.costo,
             producto.categoria_id, producto.impuesto_id,
             int(producto.vendido_por_peso), producto.unidad, producto.id))
        if cur.rowcount == 0:
            raise LookupError(f"producto inexistente: id={producto.id}")
        self._conn.commit()
        return producto
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/inventario/test_repositorio_extensiones.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Write the failing test (sesiones.listar)**

Create `tests/ventas/test_sesiones_listar.py`:

```python
from datetime import datetime
from decimal import Decimal

from core.entidades import CajaSesion
from ventas.repositorio_sqlite import RepositorioCajaSesionesSQLite


def test_listar_devuelve_todas_las_sesiones(conn):
    repo = RepositorioCajaSesionesSQLite(conn)
    repo.abrir(CajaSesion(apertura_fecha=datetime(2026, 6, 1, 8), monto_inicial=Decimal("100")))
    repo.abrir(CajaSesion(apertura_fecha=datetime(2026, 6, 2, 8), monto_inicial=Decimal("200")))
    sesiones = repo.listar()
    assert len(sesiones) == 2
    assert sesiones[0].monto_inicial == Decimal("100")
```

- [ ] **Step 6: Run test to verify it fails**

Run: `pytest tests/ventas/test_sesiones_listar.py -v`
Expected: FAIL con `AttributeError: ... no attribute 'listar'`

- [ ] **Step 7: Implement `listar()` (sesiones)**

En `src/ventas/repositorio_sqlite.py`, dentro de `RepositorioCajaSesionesSQLite` añade:

```python
    def listar(self) -> list[CajaSesion]:
        filas = self._conn.execute(
            "SELECT * FROM caja_sesiones ORDER BY id").fetchall()
        return [_fila_a_sesion(f) for f in filas]
```

- [ ] **Step 8: Update Protocol signatures**

En `src/core/puertos.py` reemplaza los 4 Protocol afectados:

```python
class RepositorioCategorias(Protocol):
    def guardar(self, categoria: Categoria) -> Categoria: ...
    def por_id(self, id: int) -> Categoria | None: ...
    def listar(self) -> list[Categoria]: ...


class RepositorioImpuestos(Protocol):
    def guardar(self, impuesto: Impuesto) -> Impuesto: ...
    def por_id(self, id: int) -> Impuesto | None: ...
    def listar(self) -> list[Impuesto]: ...


class RepositorioProductos(Protocol):
    def guardar(self, producto: Producto) -> Producto: ...
    def actualizar(self, producto: Producto) -> Producto: ...
    def por_id(self, id: int) -> Producto | None: ...
    def por_codigo(self, codigo_barras: str) -> Producto | None: ...
    def listar(self) -> list[Producto]: ...
```

Y en `RepositorioCajaSesiones` añade la línea:

```python
    def listar(self) -> list[CajaSesion]: ...
```

- [ ] **Step 9: Run full suite to verify no regression**

Run: `pytest tests/inventario/test_repositorio_extensiones.py tests/ventas/test_sesiones_listar.py -v && pytest`
Expected: nuevos PASS; suite completa sin fallos nuevos.

- [ ] **Step 10: Commit**

```bash
git add src/core/puertos.py src/inventario/repositorio_sqlite.py src/ventas/repositorio_sqlite.py tests/inventario/test_repositorio_extensiones.py tests/ventas/test_sesiones_listar.py
git commit -m "feat(repos): listar categorias/impuestos/sesiones y actualizar producto"
```

---

## Task 2: Helpers de formato (`formato.py`)

**Files:**
- Create: `src/caja/formato.py`
- Test: `tests/caja/test_formato.py`

**Interfaces:**
- Produces:
  - `formato_moneda(v: Decimal) -> str`  → `"$ 1.234.567"`
  - `formato_cantidad(v: Decimal, unidad: str) -> str`  → `"1,5 kg"` / `"3 und"`
  - `formato_fecha(dt: datetime) -> str`  → `"25/06/2026 14:32"`

- [ ] **Step 1: Write the failing test**

Create `tests/caja/test_formato.py`:

```python
from datetime import datetime
from decimal import Decimal

from caja.formato import formato_moneda, formato_cantidad, formato_fecha


def test_moneda_separador_de_miles():
    assert formato_moneda(Decimal("1234567")) == "$ 1.234.567"
    assert formato_moneda(Decimal("0")) == "$ 0"
    assert formato_moneda(Decimal("-4500")) == "-$ 4.500"


def test_cantidad_unidad_entera_sin_decimales():
    assert formato_cantidad(Decimal("3"), "und") == "3 und"


def test_cantidad_kg_con_decimales():
    assert formato_cantidad(Decimal("1.5"), "kg") == "1,5 kg"


def test_fecha():
    assert formato_fecha(datetime(2026, 6, 25, 14, 32)) == "25/06/2026 14:32"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/caja/test_formato.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'caja.formato'`

- [ ] **Step 3: Implement `formato.py`**

Create `src/caja/formato.py`:

```python
"""Helpers de presentación: dinero, cantidades y fechas. Solo stdlib."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal


def formato_moneda(v: Decimal) -> str:
    """Pesos colombianos sin decimales, separador de miles con punto."""
    entero = int(v.to_integral_value())
    signo = "-" if entero < 0 else ""
    miles = f"{abs(entero):,}".replace(",", ".")
    return f"{signo}$ {miles}"


def formato_cantidad(v: Decimal, unidad: str) -> str:
    """Entero sin decimales; fraccionario con coma decimal (es-CO)."""
    if v == v.to_integral_value():
        texto = str(int(v))
    else:
        texto = format(v.normalize(), "f").replace(".", ",")
    return f"{texto} {unidad}"


def formato_fecha(dt: datetime) -> str:
    return dt.strftime("%d/%m/%Y %H:%M")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/caja/test_formato.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/caja/formato.py tests/caja/test_formato.py
git commit -m "feat(caja): helpers de formato moneda/cantidad/fecha"
```

---

## Task 3: Bootstrap (`bootstrap.py`) — DB + migraciones + seed demo

**Files:**
- Create: `src/caja/bootstrap.py`
- Test: `tests/caja/test_bootstrap.py`

**Interfaces:**
- Consumes: `inventario.db.conectar`, `inventario.db.aplicar_migraciones`
- Produces:
  - `preparar_db(ruta: str = "pos.db") -> sqlite3.Connection` — conecta, migra, siembra demo
  - `sembrar_demo(conn: sqlite3.Connection) -> None` — idempotente (`INSERT OR IGNORE`)

- [ ] **Step 1: Write the failing test**

Create `tests/caja/test_bootstrap.py`:

```python
from caja.bootstrap import preparar_db, sembrar_demo


def test_preparar_db_siembra_categorias_y_productos():
    conn = preparar_db(":memory:")
    cats = conn.execute("SELECT COUNT(*) AS n FROM categorias").fetchone()["n"]
    prods = conn.execute("SELECT COUNT(*) AS n FROM productos").fetchone()["n"]
    assert cats >= 4
    assert prods >= 4
    conn.close()


def test_sembrar_demo_es_idempotente():
    conn = preparar_db(":memory:")
    antes = conn.execute("SELECT COUNT(*) AS n FROM productos").fetchone()["n"]
    sembrar_demo(conn)  # segunda vez
    despues = conn.execute("SELECT COUNT(*) AS n FROM productos").fetchone()["n"]
    assert antes == despues
    conn.close()


def test_productos_tienen_stock_inicial():
    conn = preparar_db(":memory:")
    fila = conn.execute(
        "SELECT COUNT(*) AS n FROM inventario_movimientos WHERE tipo = 'entrada'").fetchone()
    assert fila["n"] >= 4
    conn.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/caja/test_bootstrap.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'caja.bootstrap'`

- [ ] **Step 3: Implement `bootstrap.py`**

Create `src/caja/bootstrap.py`:

```python
"""Arranque de datos: conexión, migraciones y seed demo idempotente."""
from __future__ import annotations

import sqlite3
from datetime import datetime

from inventario.db import aplicar_migraciones, conectar

# (codigo_barras, nombre, precio, categoria_nombre, impuesto_nombre, vendido_por_peso, unidad, stock)
_PRODUCTOS_DEMO = [
    ("7700001", "Pechuga de pollo", "18900", "Carnes", "IVA 0%", 1, "kg", "25"),
    ("7700002", "Carne molida", "22000", "Carnes", "IVA 0%", 1, "kg", "18"),
    ("7700003", "Manzana roja", "6500", "Frutas", "IVA 0%", 1, "kg", "40"),
    ("7700004", "Banano", "3200", "Frutas", "IVA 0%", 1, "kg", "60"),
    ("7700005", "Papa pastusa", "2800", "Verduras", "IVA 0%", 1, "kg", "80"),
    ("7700006", "Arroz 500g", "2500", "Abarrotes", "IVA 19%", 0, "und", "100"),
]
_CATEGORIAS_DEMO = ["Carnes", "Frutas", "Verduras", "Abarrotes"]
_IMPUESTOS_DEMO = [("IVA 0%", "0"), ("IVA 19%", "0.19")]


def sembrar_demo(conn: sqlite3.Connection) -> None:
    """Crea categorías, impuestos y productos demo si no existen. Idempotente."""
    for nombre in _CATEGORIAS_DEMO:
        conn.execute("INSERT OR IGNORE INTO categorias (nombre) VALUES (?)", (nombre,))
    for nombre, tarifa in _IMPUESTOS_DEMO:
        conn.execute(
            "INSERT OR IGNORE INTO impuestos (nombre, tarifa) VALUES (?, ?)", (nombre, tarifa))
    conn.commit()

    cat_id = {r["nombre"]: r["id"]
              for r in conn.execute("SELECT id, nombre FROM categorias")}
    imp_id = {r["nombre"]: r["id"]
              for r in conn.execute("SELECT id, nombre FROM impuestos")}

    for cod, nombre, precio, cat, imp, peso, unidad, stock in _PRODUCTOS_DEMO:
        existe = conn.execute(
            "SELECT id FROM productos WHERE codigo_barras = ?", (cod,)).fetchone()
        if existe:
            continue
        cur = conn.execute(
            "INSERT INTO productos "
            "(codigo_barras, nombre, precio, costo, categoria_id, impuesto_id, "
            "vendido_por_peso, unidad) VALUES (?, ?, ?, 0, ?, ?, ?, ?)",
            (cod, nombre, precio, cat_id[cat], imp_id[imp], peso, unidad))
        conn.execute(
            "INSERT INTO inventario_movimientos "
            "(producto_id, tipo, cantidad, fecha, ref) VALUES (?, 'entrada', ?, ?, 'seed')",
            (cur.lastrowid, stock, datetime.now().isoformat()))
    conn.commit()


def preparar_db(ruta: str = "pos.db") -> sqlite3.Connection:
    conn = conectar(ruta)
    aplicar_migraciones(conn)
    sembrar_demo(conn)
    return conn
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/caja/test_bootstrap.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/caja/bootstrap.py tests/caja/test_bootstrap.py
git commit -m "feat(caja): bootstrap con migraciones y seed demo idempotente"
```

---

## Task 4: Composition root (`contexto.py`)

**Files:**
- Create: `src/caja/contexto.py`
- Test: `tests/caja/test_contexto.py`

**Interfaces:**
- Consumes: `preparar_db`, todos los repos SQLite, servicios de `core`.
- Produces:
  - `ContextoApp` dataclass con repos: `repo_productos, repo_categorias, repo_impuestos,
    repo_inventario, repo_clientes, repo_medios_pago, repo_ventas, repo_sesiones, repo_devoluciones`
    y servicios: `svc_registro, svc_anulacion, svc_clientes, svc_caja, svc_devolucion, svc_reportes`.
  - `ContextoApp.desde_conn(conn) -> ContextoApp`
  - `ContextoApp.crear(ruta_db: str = "pos.db") -> ContextoApp`
  - `ContextoApp.nueva_venta() -> ServicioVenta` (instancia fresca, stateful)

- [ ] **Step 1: Write the failing test**

Create `tests/caja/test_contexto.py`:

```python
from caja.contexto import ContextoApp
from core.servicio_venta import ServicioVenta


def test_crear_en_memoria_expone_repos_y_servicios():
    ctx = ContextoApp.crear(":memory:")
    assert ctx.repo_productos.listar()  # seed cargó productos
    assert ctx.repo_medios_pago.listar()  # migración sembró medios
    assert ctx.svc_reportes is not None
    assert ctx.svc_caja is not None
    ctx.conn.close()


def test_nueva_venta_devuelve_instancia_fresca():
    ctx = ContextoApp.crear(":memory:")
    v1 = ctx.nueva_venta()
    v2 = ctx.nueva_venta()
    assert isinstance(v1, ServicioVenta)
    assert v1 is not v2
    ctx.conn.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/caja/test_contexto.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'caja.contexto'`

- [ ] **Step 3: Implement `contexto.py`**

Create `src/caja/contexto.py`:

```python
"""Composition root: construye repos y servicios sobre una conexión SQLite."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from caja.bootstrap import preparar_db
from core.servicio_caja import ServicioCaja
from core.servicio_clientes import ServicioClientes
from core.servicio_reportes import ServicioReportes
from core.servicio_venta import (
    ServicioAnulacion, ServicioDevolucion, ServicioRegistroVenta, ServicioVenta,
)
from inventario.repositorio_sqlite import (
    RepositorioCategoriasSQLite, RepositorioImpuestosSQLite,
    RepositorioInventarioSQLite, RepositorioProductosSQLite,
)
from ventas.repositorio_sqlite import (
    RepositorioCajaSesionesSQLite, RepositorioClientesSQLite,
    RepositorioDevolucionesSQLite, RepositorioMediosPagoSQLite, RepositorioVentasSQLite,
)

EFECTIVO_MEDIO_PAGO_ID = 1


@dataclass
class ContextoApp:
    conn: sqlite3.Connection
    repo_productos: RepositorioProductosSQLite
    repo_categorias: RepositorioCategoriasSQLite
    repo_impuestos: RepositorioImpuestosSQLite
    repo_inventario: RepositorioInventarioSQLite
    repo_clientes: RepositorioClientesSQLite
    repo_medios_pago: RepositorioMediosPagoSQLite
    repo_ventas: RepositorioVentasSQLite
    repo_sesiones: RepositorioCajaSesionesSQLite
    repo_devoluciones: RepositorioDevolucionesSQLite
    svc_registro: ServicioRegistroVenta
    svc_anulacion: ServicioAnulacion
    svc_clientes: ServicioClientes
    svc_caja: ServicioCaja
    svc_devolucion: ServicioDevolucion
    svc_reportes: ServicioReportes

    @classmethod
    def desde_conn(cls, conn: sqlite3.Connection) -> "ContextoApp":
        productos = RepositorioProductosSQLite(conn)
        categorias = RepositorioCategoriasSQLite(conn)
        impuestos = RepositorioImpuestosSQLite(conn)
        inventario = RepositorioInventarioSQLite(conn)
        clientes = RepositorioClientesSQLite(conn)
        medios = RepositorioMediosPagoSQLite(conn)
        ventas = RepositorioVentasSQLite(conn)
        sesiones = RepositorioCajaSesionesSQLite(conn)
        devoluciones = RepositorioDevolucionesSQLite(conn)
        return cls(
            conn=conn,
            repo_productos=productos, repo_categorias=categorias, repo_impuestos=impuestos,
            repo_inventario=inventario, repo_clientes=clientes, repo_medios_pago=medios,
            repo_ventas=ventas, repo_sesiones=sesiones, repo_devoluciones=devoluciones,
            svc_registro=ServicioRegistroVenta(ventas, inventario),
            svc_anulacion=ServicioAnulacion(ventas, inventario),
            svc_clientes=ServicioClientes(clientes),
            svc_caja=ServicioCaja(sesiones, ventas, EFECTIVO_MEDIO_PAGO_ID),
            svc_devolucion=ServicioDevolucion(ventas, devoluciones, inventario),
            svc_reportes=ServicioReportes(ventas, devoluciones, inventario, sesiones,
                                          EFECTIVO_MEDIO_PAGO_ID),
        )

    @classmethod
    def crear(cls, ruta_db: str = "pos.db") -> "ContextoApp":
        return cls.desde_conn(preparar_db(ruta_db))

    def nueva_venta(self) -> ServicioVenta:
        return ServicioVenta(self.repo_productos, self.repo_impuestos)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/caja/test_contexto.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/caja/contexto.py tests/caja/test_contexto.py
git commit -m "feat(caja): ContextoApp composition root"
```

---

## Task 5: Tema (`tema.qss` + `tema.py`) + iconos del rail

**Files:**
- Create: `src/caja/tema.qss`
- Create: `src/caja/tema.py`
- Create: `src/caja/recursos/iconos/{venta,inventario,clientes,devoluciones,reportes,cierre}.svg`
- Test: `tests/caja/test_tema.py`

**Interfaces:**
- Produces:
  - `carga_tema(app: QApplication) -> None` — aplica `tema.qss`
  - `RUTA_ICONOS: Path` — directorio de iconos
  - `icono(nombre: str) -> str` — ruta absoluta del SVG `nombre`

- [ ] **Step 1: Write the failing test**

Create `tests/caja/test_tema.py`:

```python
import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path  # noqa: E402

from PySide6.QtWidgets import QApplication  # noqa: E402

from caja.tema import carga_tema, icono  # noqa: E402


def test_carga_tema_aplica_stylesheet():
    app = QApplication.instance() or QApplication([])
    app.setStyleSheet("")
    carga_tema(app)
    assert "#0B0E14" in app.styleSheet()


def test_icono_existe():
    for nombre in ("venta", "inventario", "clientes", "devoluciones", "reportes", "cierre"):
        assert Path(icono(nombre)).exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/caja/test_tema.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'caja.tema'`

- [ ] **Step 3: Create `tema.qss`**

Create `src/caja/tema.qss`:

```css
* {
    font-family: "Segoe UI", "DejaVu Sans", sans-serif;
    font-size: 13px;
    color: #F0F2F5;
}
QMainWindow, QWidget#fondo, QDialog {
    background-color: #0B0E14;
}
QWidget#panel, QWidget#rail {
    background-color: #151A25;
}
QFrame#card, QFrame.card {
    background-color: #1E2330;
    border: 1px solid #2E3548;
    border-radius: 8px;
}
QLabel#secundario { color: #8B95A8; }
QLabel#muted { color: #5A6278; }
QLabel#kpi-valor { font-size: 22px; font-weight: bold; color: #F0F2F5; }
QLabel#positivo { color: #22C55E; font-weight: bold; }
QLabel#alerta { color: #F59E0B; font-weight: bold; }
QLabel#error { color: #EF4444; }

QTableWidget, QTableView {
    background-color: #1E2330;
    gridline-color: #2E3548;
    border: 1px solid #2E3548;
    border-radius: 6px;
    selection-background-color: #EF4444;
    selection-color: #FFFFFF;
}
QHeaderView::section {
    background-color: #151A25;
    color: #8B95A8;
    padding: 6px;
    border: none;
    border-bottom: 1px solid #2E3548;
}

QLineEdit, QDateEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #1E2330;
    border: 1px solid #2E3548;
    border-radius: 6px;
    padding: 6px 8px;
    color: #F0F2F5;
}
QLineEdit:focus, QDateEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid #EF4444;
}
QLineEdit[error="true"] { border: 1px solid #EF4444; }

QPushButton {
    background-color: #1E2330;
    border: 1px solid #2E3548;
    border-radius: 6px;
    padding: 8px 14px;
    color: #F0F2F5;
}
QPushButton:hover { border: 1px solid #5A6278; }
QPushButton#primario {
    background-color: #EF4444;
    border: none;
    color: #FFFFFF;
    font-weight: bold;
}
QPushButton#primario:hover { background-color: #DC2626; }
QPushButton#primario:disabled { background-color: #5A6278; color: #1E2330; }
QPushButton#chip:checked {
    background-color: #EF4444;
    border: none;
    color: #FFFFFF;
}

QToolButton#rail {
    background-color: #151A25;
    border: none;
    border-left: 3px solid transparent;
    padding: 10px 0px;
}
QToolButton#rail:hover { background-color: #1E2330; }
QToolButton#rail:checked {
    background-color: #1E2330;
    border-left: 3px solid #EF4444;
}

QTabWidget::pane { border: 1px solid #2E3548; border-radius: 6px; }
QTabBar::tab {
    background-color: #151A25;
    color: #8B95A8;
    padding: 8px 16px;
    border: 1px solid #2E3548;
}
QTabBar::tab:selected { background-color: #1E2330; color: #F0F2F5; }

QScrollBar:vertical, QScrollBar:horizontal { background-color: #151A25; border: none; }
QScrollBar::handle { background-color: #2E3548; border-radius: 4px; }
QScrollBar::handle:hover { background-color: #5A6278; }
QScrollBar::add-line, QScrollBar::sub-line { background: none; border: none; }

QStatusBar { background-color: #151A25; color: #8B95A8; }
QMessageBox { background-color: #1E2330; }
```

- [ ] **Step 4: Create the 6 SVG icons**

Crea cada archivo en `src/caja/recursos/iconos/`. Iconos monocromos `currentColor`→`#8B95A8`, 24×24.

`venta.svg`:
```xml
<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#8B95A8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/></svg>
```

`inventario.svg`:
```xml
<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#8B95A8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>
```

`clientes.svg`:
```xml
<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#8B95A8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
```

`devoluciones.svg`:
```xml
<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#8B95A8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 14 4 9 9 4"/><path d="M20 20v-7a4 4 0 0 0-4-4H4"/></svg>
```

`reportes.svg`:
```xml
<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#8B95A8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
```

`cierre.svg`:
```xml
<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#8B95A8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>
```

- [ ] **Step 5: Implement `tema.py`**

Create `src/caja/tema.py`:

```python
"""Carga del tema QSS global y rutas de iconos."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QApplication

_DIR = Path(__file__).resolve().parent
RUTA_QSS = _DIR / "tema.qss"
RUTA_ICONOS = _DIR / "recursos" / "iconos"


def carga_tema(app: QApplication) -> None:
    app.setStyleSheet(RUTA_QSS.read_text(encoding="utf-8"))


def icono(nombre: str) -> str:
    return str(RUTA_ICONOS / f"{nombre}.svg")
```

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/caja/test_tema.py -v`
Expected: PASS (2 passed)

- [ ] **Step 7: Commit**

```bash
git add src/caja/tema.qss src/caja/tema.py src/caja/recursos/iconos/ tests/caja/test_tema.py
git commit -m "feat(caja): tema QSS dark navy + iconos del rail"
```

---

## Task 6: Widgets reutilizables (`widgets.py`)

**Files:**
- Create: `src/caja/widgets.py`
- Test: `tests/caja/test_widgets.py`

**Interfaces:**
- Consumes: `core.entidades.Producto`, `caja.formato.formato_moneda`
- Produces:
  - `TarjetaProducto(QFrame)`: `__init__(self, producto: Producto, nombre_categoria: str = "")`;
    señal `seleccionado = Signal(object)` (emite el `Producto` al hacer click).
  - `TarjetaKpi(QFrame)`: `__init__(self, titulo: str, valor: str = "", subtitulo: str = "")`;
    método `set_valor(self, texto: str) -> None`; `set_estado(self, estado: str) -> None`
    donde estado ∈ {"normal","positivo","alerta"} cambia el objectName del valor.
  - `BotonRail(QToolButton)`: `__init__(self, ruta_icono: str, tooltip: str)`.

- [ ] **Step 1: Write the failing test**

Create `tests/caja/test_widgets.py`:

```python
import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from decimal import Decimal  # noqa: E402

from PySide6.QtWidgets import QApplication  # noqa: E402

from core.entidades import Producto  # noqa: E402
from caja.widgets import TarjetaProducto, TarjetaKpi, BotonRail  # noqa: E402
from caja.tema import icono  # noqa: E402


def test_tarjeta_producto_emite_seleccionado():
    _app = QApplication.instance() or QApplication([])
    p = Producto(codigo_barras="B1", nombre="Manzana", precio=Decimal("6500"), id=1)
    tarjeta = TarjetaProducto(p, "Frutas")
    recibido = []
    tarjeta.seleccionado.connect(lambda prod: recibido.append(prod))
    tarjeta._emitir()  # simula click
    assert recibido and recibido[0].id == 1


def test_tarjeta_kpi_set_valor_y_estado():
    _app = QApplication.instance() or QApplication([])
    kpi = TarjetaKpi("Diferencia", "0")
    kpi.set_valor("$ 1.000")
    assert kpi._valor.text() == "$ 1.000"
    kpi.set_estado("alerta")
    assert kpi._valor.objectName() == "alerta"


def test_boton_rail_es_checkable():
    _app = QApplication.instance() or QApplication([])
    b = BotonRail(icono("venta"), "Venta")
    assert b.isCheckable()
    assert b.toolTip() == "Venta"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/caja/test_widgets.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'caja.widgets'`

- [ ] **Step 3: Implement `widgets.py`**

Create `src/caja/widgets.py`:

```python
"""Widgets reutilizables. Solo composición Qt; estilo en tema.qss."""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QFrame, QLabel, QToolButton, QVBoxLayout

from caja.formato import formato_moneda
from core.entidades import Producto


class TarjetaProducto(QFrame):
    """Card clickable con nombre, precio y categoría de un producto."""

    seleccionado = Signal(object)

    def __init__(self, producto: Producto, nombre_categoria: str = "") -> None:
        super().__init__()
        self._producto = producto
        self.setObjectName("card")
        self.setCursor(Qt.PointingHandCursor)

        nombre = QLabel(producto.nombre)
        nombre.setWordWrap(True)
        precio = QLabel(formato_moneda(producto.precio))
        precio.setObjectName("kpi-valor")
        cat = QLabel(nombre_categoria or "—")
        cat.setObjectName("secundario")

        layout = QVBoxLayout(self)
        layout.addWidget(nombre)
        layout.addWidget(precio)
        layout.addWidget(cat)

    def _emitir(self) -> None:
        self.seleccionado.emit(self._producto)

    def mousePressEvent(self, event) -> None:  # noqa: N802 (Qt API)
        self._emitir()
        super().mousePressEvent(event)


class TarjetaKpi(QFrame):
    """Card de indicador: título, valor grande y subtítulo opcional."""

    def __init__(self, titulo: str, valor: str = "", subtitulo: str = "") -> None:
        super().__init__()
        self.setObjectName("card")
        self._titulo = QLabel(titulo)
        self._titulo.setObjectName("secundario")
        self._valor = QLabel(valor)
        self._valor.setObjectName("kpi-valor")
        self._subtitulo = QLabel(subtitulo)
        self._subtitulo.setObjectName("muted")

        layout = QVBoxLayout(self)
        layout.addWidget(self._titulo)
        layout.addWidget(self._valor)
        layout.addWidget(self._subtitulo)

    def set_valor(self, texto: str) -> None:
        self._valor.setText(texto)

    def set_subtitulo(self, texto: str) -> None:
        self._subtitulo.setText(texto)

    def set_estado(self, estado: str) -> None:
        """estado ∈ {'normal','positivo','alerta'} — cambia color del valor."""
        nombre = "kpi-valor" if estado == "normal" else estado
        self._valor.setObjectName(nombre)
        self._valor.style().unpolish(self._valor)
        self._valor.style().polish(self._valor)


class BotonRail(QToolButton):
    """Botón del rail de navegación: icono + tooltip, checkable exclusivo."""

    def __init__(self, ruta_icono: str, tooltip: str) -> None:
        super().__init__()
        self.setObjectName("rail")
        self.setCheckable(True)
        self.setToolTip(tooltip)
        self.setIcon(QIcon(ruta_icono))
        self.setIconSize(QSize(24, 24))
        self.setToolButtonStyle(Qt.ToolButtonIconOnly)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/caja/test_widgets.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/caja/widgets.py tests/caja/test_widgets.py
git commit -m "feat(caja): widgets TarjetaProducto/TarjetaKpi/BotonRail"
```

---

## Task 7: Diálogo de cobro/reembolso (`dialogos/dialogo_cobro.py`)

**Files:**
- Create: `src/caja/dialogos/__init__.py`
- Create: `src/caja/dialogos/dialogo_cobro.py`
- Test: `tests/caja/test_dialogo_cobro.py`

**Interfaces:**
- Consumes: `core.entidades.MedioPago`, `core.entidades.Pago`, `caja.formato.formato_moneda`
- Produces:
  - `DialogoCobro(QDialog)`: `__init__(self, total: Decimal, medios: list[MedioPago], *,
    modo: str = "cobro", efectivo_id: int = 1, parent=None)`.
    - `modo == "cobro"`: permite recibir ≥ total; muestra vuelto; los `Pago` devueltos suman
      exactamente `total` (el medio efectivo absorbe el ajuste).
    - `modo == "reembolso"`: exige recibido == total; `Pago` = montos ingresados.
  - `pagos(self) -> list[Pago]` — válido tras aceptar; lista de `Pago` (monto>0).
  - `vuelto(self) -> Decimal`.
  - método interno `_validar() -> str | None` (mensaje de error o `None`).

- [ ] **Step 1: Write the failing test**

Create `tests/caja/test_dialogo_cobro.py`:

```python
import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from decimal import Decimal  # noqa: E402

from PySide6.QtWidgets import QApplication  # noqa: E402

from core.entidades import MedioPago  # noqa: E402
from caja.dialogos.dialogo_cobro import DialogoCobro  # noqa: E402

MEDIOS = [MedioPago(nombre="Efectivo", id=1), MedioPago(nombre="Tarjeta", id=2)]


def test_cobro_exacto_un_medio():
    _app = QApplication.instance() or QApplication([])
    d = DialogoCobro(Decimal("10000"), MEDIOS, modo="cobro", efectivo_id=1)
    d._montos[1].setValue(10000)
    assert d._validar() is None
    pagos = d.pagos()
    assert sum(p.monto for p in pagos) == Decimal("10000")
    assert d.vuelto() == Decimal("0")


def test_cobro_con_vuelto_ajusta_efectivo():
    _app = QApplication.instance() or QApplication([])
    d = DialogoCobro(Decimal("10000"), MEDIOS, modo="cobro", efectivo_id=1)
    d._montos[1].setValue(15000)  # paga 15000 en efectivo
    assert d._validar() is None
    pagos = d.pagos()
    assert sum(p.monto for p in pagos) == Decimal("10000")  # registrado = total
    assert d.vuelto() == Decimal("5000")


def test_cobro_insuficiente_da_error():
    _app = QApplication.instance() or QApplication([])
    d = DialogoCobro(Decimal("10000"), MEDIOS, modo="cobro", efectivo_id=1)
    d._montos[1].setValue(8000)
    assert d._validar() is not None


def test_reembolso_exige_suma_exacta():
    _app = QApplication.instance() or QApplication([])
    d = DialogoCobro(Decimal("7000"), MEDIOS, modo="reembolso", efectivo_id=1)
    d._montos[1].setValue(7000)
    assert d._validar() is None
    d._montos[1].setValue(8000)
    assert d._validar() is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/caja/test_dialogo_cobro.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'caja.dialogos'`

- [ ] **Step 3: Create package + implement `dialogo_cobro.py`**

Create `src/caja/dialogos/__init__.py` (vacío).

Create `src/caja/dialogos/dialogo_cobro.py`:

```python
"""Diálogo de cobro (venta) y reembolso (devolución): selección multi-medio."""
from __future__ import annotations

from decimal import Decimal

from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QLabel, QVBoxLayout,
)

from caja.formato import formato_moneda
from core.entidades import MedioPago, Pago

CERO = Decimal("0")


class DialogoCobro(QDialog):
    def __init__(self, total: Decimal, medios: list[MedioPago], *, modo: str = "cobro",
                 efectivo_id: int = 1, parent=None) -> None:
        super().__init__(parent)
        self._total = total
        self._modo = modo
        self._efectivo_id = efectivo_id
        titulo = "Cobrar" if modo == "cobro" else "Reembolsar"
        self.setWindowTitle(titulo)

        self._montos: dict[int, QDoubleSpinBox] = {}
        form = QFormLayout()
        for m in medios:
            spin = QDoubleSpinBox()
            spin.setMaximum(99_999_999)
            spin.setDecimals(0)
            spin.valueChanged.connect(self._refrescar)
            self._montos[m.id] = spin
            form.addRow(m.nombre, spin)

        self._lbl_total = QLabel(f"{titulo} total: {formato_moneda(total)}")
        self._lbl_total.setObjectName("kpi-valor")
        self._lbl_vuelto = QLabel("")
        self._lbl_vuelto.setObjectName("secundario")
        self._lbl_error = QLabel("")
        self._lbl_error.setObjectName("error")

        self._botones = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self._botones.button(QDialogButtonBox.Ok).setObjectName("primario")
        self._botones.accepted.connect(self._al_aceptar)
        self._botones.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self._lbl_total)
        layout.addLayout(form)
        layout.addWidget(self._lbl_vuelto)
        layout.addWidget(self._lbl_error)
        layout.addWidget(self._botones)
        self._refrescar()

    def _recibido(self) -> Decimal:
        return sum((Decimal(str(int(s.value()))) for s in self._montos.values()), CERO)

    def vuelto(self) -> Decimal:
        if self._modo != "cobro":
            return CERO
        return max(self._recibido() - self._total, CERO)

    def _validar(self) -> str | None:
        recibido = self._recibido()
        if recibido <= CERO:
            return "Ingresa al menos un monto"
        if self._modo == "cobro" and recibido < self._total:
            return f"Faltan {formato_moneda(self._total - recibido)}"
        if self._modo == "reembolso" and recibido != self._total:
            return f"El reembolso debe sumar exactamente {formato_moneda(self._total)}"
        return None

    def _refrescar(self) -> None:
        error = self._validar()
        self._lbl_error.setText(error or "")
        self._lbl_vuelto.setText(
            f"Vuelto: {formato_moneda(self.vuelto())}" if self._modo == "cobro" else "")
        self._botones.button(QDialogButtonBox.Ok).setEnabled(error is None)

    def pagos(self) -> list[Pago]:
        """Cobro: ajusta el efectivo para que la suma == total. Reembolso: montos tal cual."""
        crudos = {mid: Decimal(str(int(s.value()))) for mid, s in self._montos.items()}
        if self._modo == "reembolso":
            return [Pago(medio_pago_id=mid, monto=m) for mid, m in crudos.items() if m > CERO]
        no_efectivo = sum((m for mid, m in crudos.items() if mid != self._efectivo_id), CERO)
        efectivo_registrado = self._total - no_efectivo
        pagos: list[Pago] = []
        for mid, m in crudos.items():
            monto = efectivo_registrado if mid == self._efectivo_id else m
            if monto > CERO:
                pagos.append(Pago(medio_pago_id=mid, monto=monto))
        return pagos

    def _al_aceptar(self) -> None:
        if self._validar() is None:
            self.accept()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/caja/test_dialogo_cobro.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/caja/dialogos/ tests/caja/test_dialogo_cobro.py
git commit -m "feat(caja): DialogoCobro multi-medio (cobro/reembolso)"
```

---

## Task 8: PantallaVenta (rediseño)

**Files:**
- Rewrite: `src/caja/pantalla_venta.py`
- Modify: `tests/caja/test_pantalla_venta.py` (reescribir para nuevo constructor)

**Interfaces:**
- Consumes: `ContextoApp`, `TarjetaProducto`, `DialogoCobro`, `formato`, `ServicioVenta`.
- Produces:
  - `PantallaVenta(QWidget)`: `__init__(self, ctx: ContextoApp)`; señal `caja_cambiada = Signal()`.
  - método `al_mostrar(self) -> None` (recarga catálogo + estado botón).
  - atributos de test: `_busqueda` (QLineEdit), `_carrito` (QTableWidget),
    `_lbl_total` (QLabel), `_boton_cobrar` (QPushButton), `_venta` (ServicioVenta).
  - método `_agregar_producto(self, producto)`; `_cobrar()`; `_total_actual() -> Decimal`.

- [ ] **Step 1: Write the failing test**

Reemplaza `tests/caja/test_pantalla_venta.py` por:

```python
import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from datetime import datetime  # noqa: E402
from decimal import Decimal  # noqa: E402

from PySide6.QtWidgets import QApplication  # noqa: E402

from caja.contexto import ContextoApp  # noqa: E402
from caja.pantalla_venta import PantallaVenta  # noqa: E402


def _ctx():
    return ContextoApp.crear(":memory:")


def test_pantalla_construye_y_lista_productos():
    _app = QApplication.instance() or QApplication([])
    win = PantallaVenta(_ctx())
    win.al_mostrar()
    assert len(win._tarjetas) >= 4


def test_agregar_producto_actualiza_carrito_y_total():
    _app = QApplication.instance() or QApplication([])
    ctx = _ctx()
    win = PantallaVenta(ctx)
    win.al_mostrar()
    producto = ctx.repo_productos.por_codigo("7700006")  # Arroz, por unidad
    win._agregar_producto(producto)
    assert win._carrito.rowCount() == 1
    assert win._total_actual() == Decimal("2500")


def test_cobrar_deshabilitado_sin_caja_abierta():
    _app = QApplication.instance() or QApplication([])
    ctx = _ctx()
    win = PantallaVenta(ctx)
    win.al_mostrar()
    producto = ctx.repo_productos.por_codigo("7700006")
    win._agregar_producto(producto)
    assert win._boton_cobrar.isEnabled() is False  # no hay caja abierta


def test_cobrar_registra_venta_con_caja_abierta():
    _app = QApplication.instance() or QApplication([])
    ctx = _ctx()
    ctx.svc_caja.abrir(fecha=datetime.now(), monto_inicial=Decimal("0"))
    win = PantallaVenta(ctx)
    win.al_mostrar()
    producto = ctx.repo_productos.por_codigo("7700006")
    win._agregar_producto(producto)
    sesion = ctx.repo_sesiones.abierta()
    win._registrar_pagos([__import__("core.entidades", fromlist=["Pago"]).Pago(
        medio_pago_id=1, monto=Decimal("2500"))], sesion.id)
    assert win._carrito.rowCount() == 0  # carrito limpio tras cobro
    assert len(ctx.repo_ventas.ventas_de_sesion(sesion.id)) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/caja/test_pantalla_venta.py -v`
Expected: FAIL (constructor nuevo aún no existe; `AttributeError`/`TypeError`)

- [ ] **Step 3: Implement `pantalla_venta.py`**

Reemplaza `src/caja/pantalla_venta.py` por:

```python
"""Pantalla de venta: catálogo (izq) + carrito (der). Lógica en ServicioVenta."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGridLayout, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QMessageBox,
    QPushButton, QScrollArea, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from caja.contexto import ContextoApp
from caja.dialogos.dialogo_cobro import DialogoCobro
from caja.formato import formato_cantidad, formato_moneda
from caja.widgets import TarjetaProducto
from core.entidades import Pago, Producto
from core.servicio_venta import ProductoNoEncontrado, PesoRequerido

CERO = Decimal("0")
_COLS_GRID = 4


class PantallaVenta(QWidget):
    caja_cambiada = Signal()

    def __init__(self, ctx: ContextoApp) -> None:
        super().__init__()
        self._ctx = ctx
        self._venta = ctx.nueva_venta()
        self._tarjetas: list[TarjetaProducto] = []
        self._categoria_filtro: int | None = None

        # --- catálogo (izquierda) ---
        self._busqueda = QLineEdit()
        self._busqueda.setPlaceholderText("Buscar producto…")
        self._busqueda.textChanged.connect(self._aplicar_filtro)

        self._fila_chips = QHBoxLayout()
        self._cont_grid = QWidget()
        self._grid = QGridLayout(self._cont_grid)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._cont_grid)

        izquierda = QVBoxLayout()
        izquierda.addWidget(self._busqueda)
        izquierda.addLayout(self._fila_chips)
        izquierda.addWidget(scroll)

        # --- carrito (derecha) ---
        panel = QWidget()
        panel.setObjectName("panel")
        self._carrito = QTableWidget(0, 3)
        self._carrito.setHorizontalHeaderLabels(["Descripción", "Cant.", "Subtotal"])
        self._carrito.setEditTriggers(QTableWidget.NoEditTriggers)
        self._lbl_total = QLabel(formato_moneda(CERO))
        self._lbl_total.setObjectName("kpi-valor")
        boton_quitar = QPushButton("Quitar ítem")
        boton_quitar.clicked.connect(self._quitar_seleccionado)
        self._boton_cobrar = QPushButton("Cobrar")
        self._boton_cobrar.setObjectName("primario")
        self._boton_cobrar.clicked.connect(self._cobrar)
        self._estado = QLabel("")
        self._estado.setObjectName("error")

        der = QVBoxLayout(panel)
        der.addWidget(QLabel("Carrito"))
        der.addWidget(self._carrito)
        der.addWidget(self._estado)
        der.addWidget(QLabel("Total"))
        der.addWidget(self._lbl_total)
        der.addWidget(boton_quitar)
        der.addWidget(self._boton_cobrar)

        raiz = QHBoxLayout(self)
        raiz.addLayout(izquierda, 65)
        raiz.addWidget(panel, 35)

    # ---- ciclo de vida ----
    def al_mostrar(self) -> None:
        self._construir_chips()
        self._construir_grid()
        self._refrescar_carrito()

    # ---- catálogo ----
    def _construir_chips(self) -> None:
        while self._fila_chips.count():
            item = self._fila_chips.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        todas = QPushButton("Todas")
        todas.setObjectName("chip")
        todas.setCheckable(True)
        todas.setChecked(True)
        todas.clicked.connect(lambda: self._filtrar_categoria(None))
        self._fila_chips.addWidget(todas)
        for c in self._ctx.repo_categorias.listar():
            chip = QPushButton(c.nombre)
            chip.setObjectName("chip")
            chip.setCheckable(True)
            chip.clicked.connect(lambda _=False, cid=c.id: self._filtrar_categoria(cid))
            self._fila_chips.addWidget(chip)

    def _construir_grid(self) -> None:
        for t in self._tarjetas:
            t.deleteLater()
        self._tarjetas = []
        nombres_cat = {c.id: c.nombre for c in self._ctx.repo_categorias.listar()}
        for i, p in enumerate(self._ctx.repo_productos.listar()):
            tarjeta = TarjetaProducto(p, nombres_cat.get(p.categoria_id, ""))
            tarjeta.seleccionado.connect(self._agregar_producto)
            self._grid.addWidget(tarjeta, i // _COLS_GRID, i % _COLS_GRID)
            self._tarjetas.append(tarjeta)
        self._aplicar_filtro()

    def _filtrar_categoria(self, categoria_id: int | None) -> None:
        self._categoria_filtro = categoria_id
        for chip in (self._fila_chips.itemAt(i).widget()
                     for i in range(self._fila_chips.count())):
            chip.setChecked(False)
        self._aplicar_filtro()

    def _aplicar_filtro(self) -> None:
        texto = self._busqueda.text().strip().lower()
        for t in self._tarjetas:
            p = t._producto
            visible = (self._categoria_filtro is None or p.categoria_id == self._categoria_filtro)
            if texto:
                visible = visible and (texto in p.nombre.lower() or texto in p.codigo_barras.lower())
            t.setVisible(visible)

    # ---- carrito ----
    def _agregar_producto(self, producto: Producto) -> None:
        peso = None
        if producto.vendido_por_peso:
            valor, ok = QInputDialog.getDouble(
                self, "Peso", f"Kg de {producto.nombre}:", 1.0, 0.001, 9999, 3)
            if not ok:
                return
            peso = Decimal(str(valor))
        try:
            self._venta.agregar(producto.codigo_barras, peso_kg=peso)
        except (ProductoNoEncontrado, PesoRequerido, ValueError) as exc:
            self._estado.setText(str(exc))
            return
        self._estado.setText("")
        self._refrescar_carrito()

    def _refrescar_carrito(self) -> None:
        lineas = self._venta.lineas
        self._carrito.setRowCount(0)
        for linea in lineas:
            fila = self._carrito.rowCount()
            self._carrito.insertRow(fila)
            self._carrito.setItem(fila, 0, QTableWidgetItem(linea.descripcion))
            self._carrito.setItem(fila, 1, QTableWidgetItem(
                formato_cantidad(linea.cantidad_o_peso, "")))
            self._carrito.setItem(fila, 2, QTableWidgetItem(formato_moneda(linea.subtotal)))
        self._lbl_total.setText(formato_moneda(self._total_actual()))
        self._actualizar_boton_cobrar()

    def _total_actual(self) -> Decimal:
        return self._venta.total

    def _quitar_seleccionado(self) -> None:
        fila = self._carrito.currentRow()
        if fila < 0:
            return
        # ServicioVenta no expone quitar: reconstruir sin la línea.
        # peso vs unidad lo decide el flag del producto (fuente de verdad), no el valor.
        lineas = list(self._venta.lineas)
        del lineas[fila]
        self._venta = self._ctx.nueva_venta()
        for ln in lineas:
            producto = self._ctx.repo_productos.por_id(ln.producto_id)
            if producto.vendido_por_peso:
                self._venta.agregar(producto.codigo_barras, peso_kg=ln.cantidad_o_peso)
            else:
                self._venta.agregar(producto.codigo_barras, cantidad=ln.cantidad_o_peso)
        self._refrescar_carrito()

    def _actualizar_boton_cobrar(self) -> None:
        hay_caja = self._ctx.repo_sesiones.abierta() is not None
        self._boton_cobrar.setEnabled(hay_caja and bool(self._venta.lineas))

    # ---- cobro ----
    def _cobrar(self) -> None:
        sesion = self._ctx.repo_sesiones.abierta()
        if sesion is None or not self._venta.lineas:
            return
        dlg = DialogoCobro(self._total_actual(), self._ctx.repo_medios_pago.listar(),
                           modo="cobro", efectivo_id=1, parent=self)
        if dlg.exec() != DialogoCobro.Accepted:
            return
        self._registrar_pagos(dlg.pagos(), sesion.id)

    def _registrar_pagos(self, pagos: list[Pago], sesion_id: int) -> None:
        venta = self._venta.confirmar(fecha=datetime.now(), caja_sesion_id=sesion_id)
        try:
            self._ctx.svc_registro.registrar(venta, pagos)
        except Exception as exc:  # noqa: BLE001 — error inesperado al cajero
            QMessageBox.critical(self, "Error al registrar", str(exc))
            return
        self._venta = self._ctx.nueva_venta()
        self._refrescar_carrito()
        self.caja_cambiada.emit()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/caja/test_pantalla_venta.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/caja/pantalla_venta.py tests/caja/test_pantalla_venta.py
git commit -m "feat(caja): PantallaVenta rediseñada (catálogo + carrito + cobro)"
```

---

## Task 9: Diálogos de producto y movimiento

**Files:**
- Create: `src/caja/dialogos/dialogo_producto.py`
- Create: `src/caja/dialogos/dialogo_movimiento.py`
- Test: `tests/caja/test_dialogos_inventario.py`

**Interfaces:**
- Consumes: `core.entidades.{Producto, Categoria, Impuesto, MovimientoInventario}`.
- Produces:
  - `DialogoProducto(QDialog)`: `__init__(self, categorias: list[Categoria],
    impuestos: list[Impuesto], *, producto: Producto | None = None, parent=None)`.
    `producto(self) -> Producto` — construye el `Producto` con los datos del form (conserva `id`
    si era edición).
  - `DialogoMovimiento(QDialog)`: `__init__(self, producto_id: int, parent=None)`.
    `movimiento(self) -> MovimientoInventario`.

- [ ] **Step 1: Write the failing test**

Create `tests/caja/test_dialogos_inventario.py`:

```python
import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from decimal import Decimal  # noqa: E402

from PySide6.QtWidgets import QApplication  # noqa: E402

from core.entidades import Categoria, Impuesto, Producto  # noqa: E402
from caja.dialogos.dialogo_producto import DialogoProducto  # noqa: E402
from caja.dialogos.dialogo_movimiento import DialogoMovimiento  # noqa: E402

CATS = [Categoria(nombre="Carnes", id=1), Categoria(nombre="Frutas", id=2)]
IMPS = [Impuesto(nombre="IVA 0%", tarifa=Decimal("0"), id=1)]


def test_dialogo_producto_construye_nuevo():
    _app = QApplication.instance() or QApplication([])
    d = DialogoProducto(CATS, IMPS)
    d._codigo.setText("999")
    d._nombre.setText("Lomo")
    d._precio.setValue(25000)
    p = d.producto()
    assert p.codigo_barras == "999"
    assert p.nombre == "Lomo"
    assert p.precio == Decimal("25000")
    assert p.id is None


def test_dialogo_producto_conserva_id_en_edicion():
    _app = QApplication.instance() or QApplication([])
    existente = Producto(codigo_barras="1", nombre="X", precio=Decimal("100"),
                         categoria_id=1, impuesto_id=1, id=7)
    d = DialogoProducto(CATS, IMPS, producto=existente)
    d._nombre.setText("X editado")
    p = d.producto()
    assert p.id == 7
    assert p.nombre == "X editado"


def test_dialogo_movimiento_construye():
    _app = QApplication.instance() or QApplication([])
    d = DialogoMovimiento(producto_id=3)
    d._tipo.setCurrentText("entrada")
    d._cantidad.setValue(10)
    m = d.movimiento()
    assert m.producto_id == 3
    assert m.tipo == "entrada"
    assert m.cantidad == Decimal("10")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/caja/test_dialogos_inventario.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'caja.dialogos.dialogo_producto'`

- [ ] **Step 3: Implement `dialogo_producto.py`**

Create `src/caja/dialogos/dialogo_producto.py`:

```python
"""Diálogo crear/editar Producto. No persiste; solo construye la entidad."""
from __future__ import annotations

from decimal import Decimal

from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox,
    QFormLayout, QLineEdit, QVBoxLayout,
)

from core.entidades import Categoria, Impuesto, Producto


class DialogoProducto(QDialog):
    def __init__(self, categorias: list[Categoria], impuestos: list[Impuesto], *,
                 producto: Producto | None = None, parent=None) -> None:
        super().__init__(parent)
        self._editando = producto
        self.setWindowTitle("Editar producto" if producto else "Nuevo producto")

        self._codigo = QLineEdit()
        self._nombre = QLineEdit()
        self._precio = QDoubleSpinBox(); self._precio.setMaximum(99_999_999); self._precio.setDecimals(0)
        self._costo = QDoubleSpinBox(); self._costo.setMaximum(99_999_999); self._costo.setDecimals(0)
        self._categoria = QComboBox()
        for c in categorias:
            self._categoria.addItem(c.nombre, c.id)
        self._impuesto = QComboBox()
        self._impuesto.addItem("(ninguno)", None)
        for i in impuestos:
            self._impuesto.addItem(i.nombre, i.id)
        self._por_peso = QCheckBox("Vendido por peso")
        self._unidad = QComboBox()
        self._unidad.addItems(["und", "kg"])

        if producto:
            self._codigo.setText(producto.codigo_barras)
            self._nombre.setText(producto.nombre)
            self._precio.setValue(float(producto.precio))
            self._costo.setValue(float(producto.costo))
            self._seleccionar(self._categoria, producto.categoria_id)
            self._seleccionar(self._impuesto, producto.impuesto_id)
            self._por_peso.setChecked(producto.vendido_por_peso)
            self._unidad.setCurrentText(producto.unidad)

        form = QFormLayout()
        form.addRow("Código de barras", self._codigo)
        form.addRow("Nombre", self._nombre)
        form.addRow("Precio", self._precio)
        form.addRow("Costo", self._costo)
        form.addRow("Categoría", self._categoria)
        form.addRow("Impuesto", self._impuesto)
        form.addRow("", self._por_peso)
        form.addRow("Unidad", self._unidad)

        botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botones.button(QDialogButtonBox.Ok).setObjectName("primario")
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(botones)

    @staticmethod
    def _seleccionar(combo: QComboBox, data) -> None:
        idx = combo.findData(data)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def producto(self) -> Producto:
        return Producto(
            codigo_barras=self._codigo.text().strip(),
            nombre=self._nombre.text().strip(),
            precio=Decimal(str(int(self._precio.value()))),
            costo=Decimal(str(int(self._costo.value()))),
            categoria_id=self._categoria.currentData(),
            impuesto_id=self._impuesto.currentData(),
            vendido_por_peso=self._por_peso.isChecked(),
            unidad=self._unidad.currentText(),
            id=self._editando.id if self._editando else None,
        )
```

- [ ] **Step 4: Implement `dialogo_movimiento.py`**

Create `src/caja/dialogos/dialogo_movimiento.py`:

```python
"""Diálogo de movimiento de inventario (entrada/salida). Construye la entidad."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QLineEdit, QVBoxLayout,
)

from core.entidades import MovimientoInventario


class DialogoMovimiento(QDialog):
    def __init__(self, producto_id: int, parent=None) -> None:
        super().__init__(parent)
        self._producto_id = producto_id
        self.setWindowTitle("Movimiento de inventario")

        self._tipo = QComboBox()
        self._tipo.addItems(["entrada", "salida"])
        self._cantidad = QDoubleSpinBox()
        self._cantidad.setMaximum(99_999_999)
        self._cantidad.setDecimals(3)
        self._cantidad.setMinimum(0.001)
        self._ref = QLineEdit()
        self._ref.setPlaceholderText("Referencia (opcional)")

        form = QFormLayout()
        form.addRow("Tipo", self._tipo)
        form.addRow("Cantidad", self._cantidad)
        form.addRow("Referencia", self._ref)

        botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botones.button(QDialogButtonBox.Ok).setObjectName("primario")
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(botones)

    def movimiento(self) -> MovimientoInventario:
        return MovimientoInventario(
            producto_id=self._producto_id,
            tipo=self._tipo.currentText(),
            cantidad=Decimal(str(self._cantidad.value())),
            fecha=datetime.now(),
            ref=self._ref.text().strip() or None,
        )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/caja/test_dialogos_inventario.py -v`
Expected: PASS (3 passed)

- [ ] **Step 6: Commit**

```bash
git add src/caja/dialogos/dialogo_producto.py src/caja/dialogos/dialogo_movimiento.py tests/caja/test_dialogos_inventario.py
git commit -m "feat(caja): diálogos de producto y movimiento de inventario"
```

---

## Task 10: PantallaInventario

**Files:**
- Create: `src/caja/pantalla_inventario.py`
- Test: `tests/caja/test_pantalla_inventario.py`

**Interfaces:**
- Consumes: `ContextoApp`, `DialogoProducto`, `DialogoMovimiento`, `formato`.
- Produces:
  - `PantallaInventario(QWidget)`: `__init__(self, ctx: ContextoApp)`; `al_mostrar()`.
  - atributos de test: `_tabla` (QTableWidget), `_busqueda` (QLineEdit),
    `_productos` (list[Producto] en orden de filas).
  - métodos: `_crear_producto()`, `_editar_producto()`, `_registrar_movimiento()`,
    `_producto_seleccionado() -> Producto | None`.

- [ ] **Step 1: Write the failing test**

Create `tests/caja/test_pantalla_inventario.py`:

```python
import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from decimal import Decimal  # noqa: E402

from PySide6.QtWidgets import QApplication  # noqa: E402

from core.entidades import MovimientoInventario, Producto  # noqa: E402
from caja.contexto import ContextoApp  # noqa: E402
from caja.pantalla_inventario import PantallaInventario  # noqa: E402


def test_lista_productos_con_stock():
    _app = QApplication.instance() or QApplication([])
    ctx = ContextoApp.crear(":memory:")
    win = PantallaInventario(ctx)
    win.al_mostrar()
    assert win._tabla.rowCount() >= 4
    # columna stock (índice 5) muestra número
    assert win._tabla.item(0, 5) is not None


def test_guardar_producto_nuevo_agrega_fila():
    _app = QApplication.instance() or QApplication([])
    ctx = ContextoApp.crear(":memory:")
    win = PantallaInventario(ctx)
    win.al_mostrar()
    antes = win._tabla.rowCount()
    nuevo = Producto(codigo_barras="555", nombre="Cerdo", precio=Decimal("19000"),
                     categoria_id=1, impuesto_id=1, unidad="kg", vendido_por_peso=True)
    win._guardar_producto(nuevo)
    win.al_mostrar()
    assert win._tabla.rowCount() == antes + 1


def test_aplicar_movimiento_cambia_stock():
    _app = QApplication.instance() or QApplication([])
    ctx = ContextoApp.crear(":memory:")
    win = PantallaInventario(ctx)
    win.al_mostrar()
    prod = ctx.repo_productos.listar()[0]
    stock_antes = ctx.repo_inventario.stock_de(prod.id)
    win._aplicar_movimiento(MovimientoInventario(
        producto_id=prod.id, tipo="entrada", cantidad=Decimal("5"),
        fecha=__import__("datetime").datetime.now()))
    assert ctx.repo_inventario.stock_de(prod.id) == stock_antes + Decimal("5")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/caja/test_pantalla_inventario.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'caja.pantalla_inventario'`

- [ ] **Step 3: Implement `pantalla_inventario.py`**

Create `src/caja/pantalla_inventario.py`:

```python
"""Pantalla de inventario: tabla de productos con stock + CRUD y movimientos."""
from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QHBoxLayout, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from caja.contexto import ContextoApp
from caja.dialogos.dialogo_movimiento import DialogoMovimiento
from caja.dialogos.dialogo_producto import DialogoProducto
from caja.formato import formato_cantidad, formato_moneda
from core.entidades import MovimientoInventario, Producto

_COLS = ["Código", "Nombre", "Categoría", "Precio", "Costo", "Stock", "Unidad"]
_COLOR_ALERTA = QColor("#F59E0B")


class PantallaInventario(QWidget):
    def __init__(self, ctx: ContextoApp) -> None:
        super().__init__()
        self._ctx = ctx
        self._productos: list[Producto] = []

        self._busqueda = QLineEdit()
        self._busqueda.setPlaceholderText("Buscar por nombre o código…")
        self._busqueda.textChanged.connect(self._filtrar)

        boton_nuevo = QPushButton("Nuevo producto")
        boton_nuevo.clicked.connect(self._crear_producto)
        self._boton_editar = QPushButton("Editar")
        self._boton_editar.clicked.connect(self._editar_producto)
        self._boton_mov = QPushButton("Movimiento")
        self._boton_mov.clicked.connect(self._registrar_movimiento)

        barra = QHBoxLayout()
        barra.addWidget(self._busqueda, 1)
        barra.addWidget(boton_nuevo)
        barra.addWidget(self._boton_editar)
        barra.addWidget(self._boton_mov)

        self._tabla = QTableWidget(0, len(_COLS))
        self._tabla.setHorizontalHeaderLabels(_COLS)
        self._tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self._tabla.setSelectionBehavior(QTableWidget.SelectRows)

        layout = QVBoxLayout(self)
        layout.addLayout(barra)
        layout.addWidget(self._tabla)

    def al_mostrar(self) -> None:
        self._productos = self._ctx.repo_productos.listar()
        nombres_cat = {c.id: c.nombre for c in self._ctx.repo_categorias.listar()}
        self._tabla.setRowCount(0)
        for p in self._productos:
            fila = self._tabla.rowCount()
            self._tabla.insertRow(fila)
            stock = self._ctx.repo_inventario.stock_de(p.id)
            celdas = [
                p.codigo_barras, p.nombre, nombres_cat.get(p.categoria_id, "—"),
                formato_moneda(p.precio), formato_moneda(p.costo),
                formato_cantidad(stock, p.unidad), p.unidad,
            ]
            for col, texto in enumerate(celdas):
                item = QTableWidgetItem(texto)
                if col == 5 and stock <= 0:
                    item.setForeground(_COLOR_ALERTA)
                self._tabla.setItem(fila, col, item)
        self._filtrar()

    def _filtrar(self) -> None:
        texto = self._busqueda.text().strip().lower()
        for fila, p in enumerate(self._productos):
            visible = (not texto) or (texto in p.nombre.lower()
                                      or texto in p.codigo_barras.lower())
            self._tabla.setRowHidden(fila, not visible)

    def _producto_seleccionado(self) -> Producto | None:
        fila = self._tabla.currentRow()
        if 0 <= fila < len(self._productos):
            return self._productos[fila]
        return None

    def _crear_producto(self) -> None:
        dlg = DialogoProducto(self._ctx.repo_categorias.listar(),
                              self._ctx.repo_impuestos.listar(), parent=self)
        if dlg.exec() == DialogoProducto.Accepted:
            self._guardar_producto(dlg.producto())
            self.al_mostrar()

    def _editar_producto(self) -> None:
        p = self._producto_seleccionado()
        if p is None:
            return
        dlg = DialogoProducto(self._ctx.repo_categorias.listar(),
                              self._ctx.repo_impuestos.listar(), producto=p, parent=self)
        if dlg.exec() == DialogoProducto.Accepted:
            self._guardar_producto(dlg.producto())
            self.al_mostrar()

    def _guardar_producto(self, producto: Producto) -> None:
        if producto.id is None:
            self._ctx.repo_productos.guardar(producto)
        else:
            self._ctx.repo_productos.actualizar(producto)

    def _registrar_movimiento(self) -> None:
        p = self._producto_seleccionado()
        if p is None:
            return
        dlg = DialogoMovimiento(p.id, parent=self)
        if dlg.exec() == DialogoMovimiento.Accepted:
            self._aplicar_movimiento(dlg.movimiento())
            self.al_mostrar()

    def _aplicar_movimiento(self, movimiento: MovimientoInventario) -> None:
        self._ctx.repo_inventario.registrar(movimiento)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/caja/test_pantalla_inventario.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/caja/pantalla_inventario.py tests/caja/test_pantalla_inventario.py
git commit -m "feat(caja): PantallaInventario (CRUD productos + stock + movimientos)"
```

---

## Task 11: PantallaClientes (rediseño)

**Files:**
- Rewrite: `src/caja/pantalla_clientes.py`
- Modify: `tests/caja/test_pantalla_clientes.py`

**Interfaces:**
- Consumes: `ServicioClientes`, `core.entidades.Cliente`.
- Produces:
  - `PantallaClientes(QWidget)`: `__init__(self, servicio: ServicioClientes)`; `al_mostrar()`.
  - atributos de test: `_tabla`, `_identificacion`, `_nombre`, `_contacto`, `_estado`,
    `_boton_guardar`, `_editando` (Cliente | None).
  - métodos: `_guardar()`, `_seleccionar_fila(fila: int)`, `_nuevo()`.

- [ ] **Step 1: Write the failing test**

Reemplaza `tests/caja/test_pantalla_clientes.py` por:

```python
import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from core.servicio_clientes import ServicioClientes  # noqa: E402
from caja.pantalla_clientes import PantallaClientes  # noqa: E402


class _FakeRepo:
    def __init__(self):
        self._items = {}
        self._next = 1

    def guardar(self, cliente):
        from dataclasses import replace
        c = replace(cliente, id=self._next)
        self._items[self._next] = c
        self._next += 1
        return c

    def actualizar(self, cliente):
        self._items[cliente.id] = cliente
        return cliente

    def por_id(self, id):
        return self._items.get(id)

    def por_identificacion(self, identificacion):
        return next((c for c in self._items.values()
                     if c.identificacion == identificacion), None)

    def listar(self):
        return list(self._items.values())


def _pantalla():
    return PantallaClientes(ServicioClientes(_FakeRepo()))


def test_crear_agrega_fila():
    _app = QApplication.instance() or QApplication([])
    win = _pantalla()
    win._identificacion.setText("900123")
    win._nombre.setText("Carnes SAS")
    win._guardar()
    assert win._tabla.rowCount() == 1
    assert "Carnes SAS" in win._tabla.item(0, 1).text()


def test_crear_duplicado_muestra_error():
    _app = QApplication.instance() or QApplication([])
    win = _pantalla()
    win._identificacion.setText("900123"); win._nombre.setText("A"); win._guardar()
    win._nuevo()
    win._identificacion.setText("900123"); win._nombre.setText("B"); win._guardar()
    assert "Error" in win._estado.text() or win._estado.text() != ""
    assert win._tabla.rowCount() == 1


def test_editar_cliente_existente():
    _app = QApplication.instance() or QApplication([])
    win = _pantalla()
    win._identificacion.setText("900123"); win._nombre.setText("Viejo"); win._guardar()
    win._seleccionar_fila(0)
    win._nombre.setText("Nuevo")
    win._guardar()
    assert win._tabla.rowCount() == 1
    assert "Nuevo" in win._tabla.item(0, 1).text()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/caja/test_pantalla_clientes.py -v`
Expected: FAIL (`_guardar`/`_nuevo`/`_seleccionar_fila` no existen)

- [ ] **Step 3: Implement `pantalla_clientes.py`**

Reemplaza `src/caja/pantalla_clientes.py` por:

```python
"""Pantalla de clientes: tabla + formulario crear/editar. Lógica en ServicioClientes."""
from __future__ import annotations

from dataclasses import replace

from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from core.entidades import Cliente
from core.servicio_clientes import ServicioClientes


class PantallaClientes(QWidget):
    def __init__(self, servicio: ServicioClientes) -> None:
        super().__init__()
        self._servicio = servicio
        self._editando: Cliente | None = None
        self._clientes: list[Cliente] = []

        self._tabla = QTableWidget(0, 3)
        self._tabla.setHorizontalHeaderLabels(["Identificación", "Nombre", "Contacto"])
        self._tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self._tabla.setSelectionBehavior(QTableWidget.SelectRows)
        self._tabla.cellClicked.connect(lambda fila, _col: self._seleccionar_fila(fila))

        self._identificacion = QLineEdit(); self._identificacion.setPlaceholderText("Identificación")
        self._nombre = QLineEdit(); self._nombre.setPlaceholderText("Nombre")
        self._contacto = QLineEdit(); self._contacto.setPlaceholderText("Contacto (opcional)")
        self._boton_guardar = QPushButton("Crear")
        self._boton_guardar.setObjectName("primario")
        self._boton_guardar.clicked.connect(self._guardar)
        boton_nuevo = QPushButton("Nuevo")
        boton_nuevo.clicked.connect(self._nuevo)
        self._estado = QLabel("")
        self._estado.setObjectName("error")

        form = QVBoxLayout()
        form.addWidget(QLabel("Cliente"))
        form.addWidget(self._identificacion)
        form.addWidget(self._nombre)
        form.addWidget(self._contacto)
        form.addWidget(self._boton_guardar)
        form.addWidget(boton_nuevo)
        form.addWidget(self._estado)
        form.addStretch(1)
        panel = QWidget(); panel.setObjectName("panel"); panel.setLayout(form)

        raiz = QHBoxLayout(self)
        raiz.addWidget(self._tabla, 65)
        raiz.addWidget(panel, 35)

        self.al_mostrar()

    def al_mostrar(self) -> None:
        self._clientes = self._servicio.listar()
        self._tabla.setRowCount(0)
        for c in self._clientes:
            fila = self._tabla.rowCount()
            self._tabla.insertRow(fila)
            self._tabla.setItem(fila, 0, QTableWidgetItem(c.identificacion))
            self._tabla.setItem(fila, 1, QTableWidgetItem(c.nombre))
            self._tabla.setItem(fila, 2, QTableWidgetItem(c.contacto or ""))

    def _seleccionar_fila(self, fila: int) -> None:
        if not (0 <= fila < len(self._clientes)):
            return
        c = self._clientes[fila]
        self._editando = c
        self._identificacion.setText(c.identificacion)
        self._nombre.setText(c.nombre)
        self._contacto.setText(c.contacto or "")
        bloqueado = c.bloqueado_edicion
        for campo in (self._identificacion, self._nombre, self._contacto):
            campo.setEnabled(not bloqueado)
        self._boton_guardar.setEnabled(not bloqueado)
        self._boton_guardar.setText("Guardar cambios")
        self._estado.setText("Cliente bloqueado" if bloqueado else "")

    def _nuevo(self) -> None:
        self._editando = None
        for campo in (self._identificacion, self._nombre, self._contacto):
            campo.clear(); campo.setEnabled(True)
        self._boton_guardar.setEnabled(True)
        self._boton_guardar.setText("Crear")
        self._estado.setText("")

    def _guardar(self) -> None:
        identificacion = self._identificacion.text().strip()
        nombre = self._nombre.text().strip()
        contacto = self._contacto.text().strip() or None
        try:
            if self._editando is None:
                self._servicio.crear(identificacion, nombre, contacto)
            else:
                self._servicio.actualizar(replace(
                    self._editando, identificacion=identificacion,
                    nombre=nombre, contacto=contacto))
        except (ValueError, LookupError) as exc:
            self._estado.setText(f"Error: {exc}")
            return
        self._nuevo()
        self.al_mostrar()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/caja/test_pantalla_clientes.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/caja/pantalla_clientes.py tests/caja/test_pantalla_clientes.py
git commit -m "feat(caja): PantallaClientes rediseñada con edición"
```

---

## Task 12: PantallaDevoluciones

**Files:**
- Create: `src/caja/pantalla_devoluciones.py`
- Test: `tests/caja/test_pantalla_devoluciones.py`

**Interfaces:**
- Consumes: `ContextoApp`, `DialogoCobro` (modo reembolso), `ServicioDevolucion`,
  `core.entidades.{ItemDevolucion, Pago}`.
- Produces:
  - `PantallaDevoluciones(QWidget)`: `__init__(self, ctx: ContextoApp)`;
    señal `caja_cambiada = Signal()`; `al_mostrar()` (no-op / limpia).
  - atributos de test: `_id_venta` (QLineEdit), `_tabla` (QTableWidget),
    `_lbl_total` (QLabel), `_estado` (QLabel), `_venta` (Venta | None).
  - métodos: `_buscar()`, `_items_a_devolver() -> list[ItemDevolucion]`,
    `_total_a_devolver() -> Decimal`, `_procesar(pagos: list[Pago])`.

- [ ] **Step 1: Write the failing test**

Create `tests/caja/test_pantalla_devoluciones.py`:

```python
import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from datetime import datetime  # noqa: E402
from decimal import Decimal  # noqa: E402

from PySide6.QtWidgets import QApplication  # noqa: E402

from core.entidades import Pago  # noqa: E402
from caja.contexto import ContextoApp  # noqa: E402
from caja.pantalla_devoluciones import PantallaDevoluciones  # noqa: E402


def _ctx_con_venta():
    ctx = ContextoApp.crear(":memory:")
    ctx.svc_caja.abrir(fecha=datetime.now(), monto_inicial=Decimal("0"))
    sesion = ctx.repo_sesiones.abierta()
    venta_serv = ctx.nueva_venta()
    venta_serv.agregar("7700006")  # Arroz und 2500
    venta = venta_serv.confirmar(fecha=datetime.now(), caja_sesion_id=sesion.id)
    guardada = ctx.svc_registro.registrar(venta, [Pago(medio_pago_id=1, monto=Decimal("2500"))])
    return ctx, guardada


def test_buscar_venta_existente_carga_lineas():
    _app = QApplication.instance() or QApplication([])
    ctx, venta = _ctx_con_venta()
    win = PantallaDevoluciones(ctx)
    win._id_venta.setText(str(venta.id))
    win._buscar()
    assert win._tabla.rowCount() == 1
    assert win._venta is not None


def test_buscar_venta_inexistente_muestra_error():
    _app = QApplication.instance() or QApplication([])
    ctx, _ = _ctx_con_venta()
    win = PantallaDevoluciones(ctx)
    win._id_venta.setText("9999")
    win._buscar()
    assert win._estado.text() != ""
    assert win._venta is None


def test_procesar_devolucion_total():
    _app = QApplication.instance() or QApplication([])
    ctx, venta = _ctx_con_venta()
    win = PantallaDevoluciones(ctx)
    win._id_venta.setText(str(venta.id))
    win._buscar()
    win._spins[0].setValue(1)  # devolver 1 unidad
    assert win._total_a_devolver() == Decimal("2500")
    win._procesar([Pago(medio_pago_id=1, monto=Decimal("2500"))])
    assert ctx.repo_ventas.por_id(venta.id).estado == "devuelta"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/caja/test_pantalla_devoluciones.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'caja.pantalla_devoluciones'`

- [ ] **Step 3: Implement `pantalla_devoluciones.py`**

Create `src/caja/pantalla_devoluciones.py`:

```python
"""Pantalla de devoluciones: buscar venta, elegir cantidades, reembolsar."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QDoubleSpinBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from caja.contexto import ContextoApp
from caja.dialogos.dialogo_cobro import DialogoCobro
from caja.formato import formato_cantidad, formato_moneda
from core.entidades import ItemDevolucion, Pago, Venta
from core.servicio_venta import (
    CantidadDevueltaExcede, ReembolsoDescuadrado, VentaNoDevolvible, VentaNoEncontrada,
)

CERO = Decimal("0")
_COLS = ["Producto", "Vendido", "Ya devuelto", "Remanente", "A devolver"]


class PantallaDevoluciones(QWidget):
    caja_cambiada = Signal()

    def __init__(self, ctx: ContextoApp) -> None:
        super().__init__()
        self._ctx = ctx
        self._venta: Venta | None = None
        self._spins: list[QDoubleSpinBox] = []
        self._remanentes: list[Decimal] = []

        self._id_venta = QLineEdit()
        self._id_venta.setPlaceholderText("ID de venta")
        boton_buscar = QPushButton("Buscar")
        boton_buscar.clicked.connect(self._buscar)
        barra = QHBoxLayout()
        barra.addWidget(self._id_venta, 1)
        barra.addWidget(boton_buscar)

        self._resumen = QLabel("")
        self._resumen.setObjectName("secundario")
        self._tabla = QTableWidget(0, len(_COLS))
        self._tabla.setHorizontalHeaderLabels(_COLS)
        self._tabla.setEditTriggers(QTableWidget.NoEditTriggers)

        self._lbl_total = QLabel(formato_moneda(CERO))
        self._lbl_total.setObjectName("kpi-valor")
        self._boton_procesar = QPushButton("Procesar devolución")
        self._boton_procesar.setObjectName("primario")
        self._boton_procesar.clicked.connect(self._abrir_reembolso)
        self._boton_procesar.setEnabled(False)
        self._estado = QLabel("")
        self._estado.setObjectName("error")

        layout = QVBoxLayout(self)
        layout.addLayout(barra)
        layout.addWidget(self._resumen)
        layout.addWidget(self._tabla)
        layout.addWidget(self._estado)
        layout.addWidget(QLabel("Total a reembolsar"))
        layout.addWidget(self._lbl_total)
        layout.addWidget(self._boton_procesar)

    def al_mostrar(self) -> None:
        self._limpiar()

    def _limpiar(self) -> None:
        self._venta = None
        self._spins = []
        self._remanentes = []
        self._tabla.setRowCount(0)
        self._resumen.setText("")
        self._estado.setText("")
        self._lbl_total.setText(formato_moneda(CERO))
        self._boton_procesar.setEnabled(False)

    def _buscar(self) -> None:
        self._limpiar()
        texto = self._id_venta.text().strip()
        if not texto.isdigit():
            self._estado.setText("ID inválido")
            return
        venta = self._ctx.repo_ventas.por_id(int(texto))
        if venta is None:
            self._estado.setText("Venta no encontrada")
            return
        if venta.estado in ("anulada", "devuelta"):
            self._estado.setText(f"Venta en estado '{venta.estado}', no devolvible")
            return
        self._venta = venta
        self._resumen.setText(
            f"Venta #{venta.id} · {venta.estado} · {formato_moneda(venta.total)}")
        ya_devuelto = self._ctx.repo_devoluciones.devuelto_por_linea(venta.id)
        for linea in venta.lineas:
            remanente = linea.cantidad_o_peso - ya_devuelto.get(linea.id, CERO)
            fila = self._tabla.rowCount()
            self._tabla.insertRow(fila)
            self._tabla.setItem(fila, 0, QTableWidgetItem(linea.descripcion))
            self._tabla.setItem(fila, 1, QTableWidgetItem(
                formato_cantidad(linea.cantidad_o_peso, "")))
            self._tabla.setItem(fila, 2, QTableWidgetItem(
                formato_cantidad(ya_devuelto.get(linea.id, CERO), "")))
            self._tabla.setItem(fila, 3, QTableWidgetItem(formato_cantidad(remanente, "")))
            spin = QDoubleSpinBox()
            spin.setDecimals(3)
            spin.setMaximum(float(remanente))
            spin.valueChanged.connect(self._refrescar_total)
            self._tabla.setCellWidget(fila, 4, spin)
            self._spins.append(spin)
            self._remanentes.append(remanente)
        self._refrescar_total()

    def _items_a_devolver(self) -> list[ItemDevolucion]:
        items: list[ItemDevolucion] = []
        for linea, spin in zip(self._venta.lineas, self._spins):
            cantidad = Decimal(str(spin.value()))
            if cantidad > CERO:
                items.append(ItemDevolucion(venta_linea_id=linea.id, cantidad_o_peso=cantidad))
        return items

    def _total_a_devolver(self) -> Decimal:
        total = CERO
        for linea, spin in zip(self._venta.lineas, self._spins):
            cantidad = Decimal(str(spin.value()))
            if cantidad > CERO and linea.cantidad_o_peso > CERO:
                ratio = cantidad / linea.cantidad_o_peso
                total += (linea.subtotal * ratio).quantize(Decimal("1"))
        return total

    def _refrescar_total(self) -> None:
        if self._venta is None:
            return
        total = self._total_a_devolver()
        self._lbl_total.setText(formato_moneda(total))
        self._boton_procesar.setEnabled(total > CERO)

    def _abrir_reembolso(self) -> None:
        if self._venta is None:
            return
        total = self._total_a_devolver()
        dlg = DialogoCobro(total, self._ctx.repo_medios_pago.listar(),
                           modo="reembolso", efectivo_id=1, parent=self)
        if dlg.exec() == DialogoCobro.Accepted:
            self._procesar(dlg.pagos())

    def _procesar(self, pagos: list[Pago]) -> None:
        sesion = self._ctx.repo_sesiones.abierta()
        try:
            self._ctx.svc_devolucion.devolver(
                self._venta.id, self._items_a_devolver(), pagos,
                fecha=datetime.now(),
                caja_sesion_id=sesion.id if sesion else None)
        except (VentaNoEncontrada, VentaNoDevolvible, CantidadDevueltaExcede,
                ReembolsoDescuadrado) as exc:
            self._estado.setText(f"Error: {exc}")
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", str(exc))
            return
        QMessageBox.information(self, "Devolución", "Devolución procesada.")
        self._limpiar()
        self.caja_cambiada.emit()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/caja/test_pantalla_devoluciones.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/caja/pantalla_devoluciones.py tests/caja/test_pantalla_devoluciones.py
git commit -m "feat(caja): PantallaDevoluciones (buscar venta + reembolso)"
```

---

## Task 13: PantallaCierre

**Files:**
- Create: `src/caja/pantalla_cierre.py`
- Test: `tests/caja/test_pantalla_cierre.py`

**Interfaces:**
- Consumes: `ContextoApp`, `ServicioCaja`, `TarjetaKpi`, `formato`.
- Produces:
  - `PantallaCierre(QWidget)`: `__init__(self, ctx: ContextoApp)`;
    señal `caja_cambiada = Signal()`; `al_mostrar()` (reconstruye según haya caja).
  - atributos de test: `_monto_inicial` (QDoubleSpinBox), `_monto_contado` (QDoubleSpinBox),
    `_kpi_esperado`, `_kpi_diferencia` (TarjetaKpi), `_boton_abrir`, `_boton_cerrar`.
  - métodos: `_abrir()`, `_cerrar()`, `_recalcular_arqueo()`.

- [ ] **Step 1: Write the failing test**

Create `tests/caja/test_pantalla_cierre.py`:

```python
import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from decimal import Decimal  # noqa: E402

from PySide6.QtWidgets import QApplication  # noqa: E402

from caja.contexto import ContextoApp  # noqa: E402
from caja.pantalla_cierre import PantallaCierre  # noqa: E402


def test_abrir_caja_crea_sesion():
    _app = QApplication.instance() or QApplication([])
    ctx = ContextoApp.crear(":memory:")
    win = PantallaCierre(ctx)
    win.al_mostrar()
    win._monto_inicial.setValue(50000)
    win._abrir()
    assert ctx.repo_sesiones.abierta() is not None


def test_cerrar_caja_cierra_sesion():
    _app = QApplication.instance() or QApplication([])
    ctx = ContextoApp.crear(":memory:")
    win = PantallaCierre(ctx)
    win.al_mostrar()
    win._monto_inicial.setValue(50000)
    win._abrir()
    win.al_mostrar()
    win._monto_contado.setValue(50000)
    win._cerrar()
    assert ctx.repo_sesiones.abierta() is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/caja/test_pantalla_cierre.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'caja.pantalla_cierre'`

- [ ] **Step 3: Implement `pantalla_cierre.py`**

Create `src/caja/pantalla_cierre.py`:

```python
"""Pantalla de cierre: abrir caja o ver arqueo en vivo y cerrar."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QDoubleSpinBox, QGridLayout, QHBoxLayout, QLabel, QMessageBox,
    QPushButton, QVBoxLayout, QWidget,
)

from caja.contexto import ContextoApp
from caja.formato import formato_moneda
from caja.widgets import TarjetaKpi
from core.entidades import CajaSesion
from core.servicio_caja import CajaNoAbierta, CajaYaAbierta

CERO = Decimal("0")


class PantallaCierre(QWidget):
    caja_cambiada = Signal()

    def __init__(self, ctx: ContextoApp) -> None:
        super().__init__()
        self._ctx = ctx
        self._layout = QVBoxLayout(self)
        # widgets persistentes para test/acceso
        self._monto_inicial = QDoubleSpinBox()
        self._monto_inicial.setMaximum(99_999_999); self._monto_inicial.setDecimals(0)
        self._monto_contado = QDoubleSpinBox()
        self._monto_contado.setMaximum(99_999_999); self._monto_contado.setDecimals(0)
        self._monto_contado.valueChanged.connect(self._recalcular_arqueo)
        self._boton_abrir = QPushButton("Abrir caja"); self._boton_abrir.setObjectName("primario")
        self._boton_abrir.clicked.connect(self._abrir)
        self._boton_cerrar = QPushButton("Cerrar caja"); self._boton_cerrar.setObjectName("primario")
        self._boton_cerrar.clicked.connect(self._cerrar)
        self._kpi_inicial = TarjetaKpi("Monto inicial")
        self._kpi_efectivo = TarjetaKpi("Ventas efectivo")
        self._kpi_esperado = TarjetaKpi("Esperado")
        self._kpi_diferencia = TarjetaKpi("Diferencia")
        self._estado = QLabel(""); self._estado.setObjectName("error")

    def al_mostrar(self) -> None:
        self._limpiar_layout()
        sesion = self._ctx.repo_sesiones.abierta()
        if sesion is None:
            self._montar_apertura()
        else:
            self._montar_arqueo(sesion)

    def _limpiar_layout(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)

    def _montar_apertura(self) -> None:
        self._layout.addWidget(QLabel("Caja cerrada"))
        self._layout.addWidget(QLabel("Monto inicial"))
        self._layout.addWidget(self._monto_inicial)
        self._layout.addWidget(self._boton_abrir)
        self._layout.addWidget(self._estado)
        self._layout.addStretch(1)

    def _montar_arqueo(self, sesion: CajaSesion) -> None:
        grid = QGridLayout()
        grid.addWidget(self._kpi_inicial, 0, 0)
        grid.addWidget(self._kpi_efectivo, 0, 1)
        grid.addWidget(self._kpi_esperado, 1, 0)
        grid.addWidget(self._kpi_diferencia, 1, 1)
        self._layout.addWidget(QLabel(f"Caja #{sesion.id} abierta"))
        self._layout.addLayout(grid)
        fila = QHBoxLayout()
        fila.addWidget(QLabel("Efectivo contado"))
        fila.addWidget(self._monto_contado)
        self._layout.addLayout(fila)
        self._layout.addWidget(self._boton_cerrar)
        self._layout.addWidget(self._estado)
        self._layout.addStretch(1)
        self._kpi_inicial.set_valor(formato_moneda(sesion.monto_inicial))
        self._recalcular_arqueo()

    def _efectivo_ventas(self, sesion: CajaSesion) -> Decimal:
        return self._ctx.repo_ventas.totales_por_medio(sesion.id).get(1, CERO)

    def _recalcular_arqueo(self) -> None:
        sesion = self._ctx.repo_sesiones.abierta()
        if sesion is None:
            return
        contado = Decimal(str(int(self._monto_contado.value())))
        arqueo = self._ctx.svc_caja.arqueo(sesion.id, contado)
        self._kpi_efectivo.set_valor(formato_moneda(arqueo.efectivo_ventas))
        self._kpi_esperado.set_valor(formato_moneda(arqueo.esperado))
        self._kpi_diferencia.set_valor(formato_moneda(arqueo.diferencia))
        self._kpi_diferencia.set_estado("positivo" if arqueo.diferencia >= CERO else "alerta")

    def _abrir(self) -> None:
        try:
            self._ctx.svc_caja.abrir(
                fecha=datetime.now(),
                monto_inicial=Decimal(str(int(self._monto_inicial.value()))))
        except (CajaYaAbierta, ValueError) as exc:
            self._estado.setText(f"Error: {exc}")
            return
        self.al_mostrar()
        self.caja_cambiada.emit()

    def _cerrar(self) -> None:
        sesion = self._ctx.repo_sesiones.abierta()
        if sesion is None:
            return
        try:
            self._ctx.svc_caja.cerrar(
                sesion_id=sesion.id, fecha=datetime.now(),
                monto_contado=Decimal(str(int(self._monto_contado.value()))))
        except (CajaNoAbierta, ValueError) as exc:
            self._estado.setText(f"Error: {exc}")
            return
        QMessageBox.information(self, "Cierre", "Caja cerrada.")
        self.al_mostrar()
        self.caja_cambiada.emit()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/caja/test_pantalla_cierre.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/caja/pantalla_cierre.py tests/caja/test_pantalla_cierre.py
git commit -m "feat(caja): PantallaCierre (abrir/arqueo en vivo/cerrar)"
```

---

## Task 14: PantallaReportes

**Files:**
- Create: `src/caja/pantalla_reportes.py`
- Test: `tests/caja/test_pantalla_reportes.py`

**Interfaces:**
- Consumes: `ContextoApp`, `ServicioReportes`, `TarjetaKpi`, `formato`.
- Produces:
  - `PantallaReportes(QWidget)`: `__init__(self, ctx: ContextoApp)`; `al_mostrar()` (consulta hoy).
  - atributos de test: `_desde`, `_hasta` (QDateEdit), `_tabla_ventas`, `_tabla_inventario`
    (QTableWidget), `_kpi_neto` (TarjetaKpi).
  - métodos: `_consultar()`, `_rango() -> tuple[datetime, datetime]`.

- [ ] **Step 1: Write the failing test**

Create `tests/caja/test_pantalla_reportes.py`:

```python
import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from datetime import datetime  # noqa: E402
from decimal import Decimal  # noqa: E402

from PySide6.QtWidgets import QApplication  # noqa: E402

from core.entidades import Pago  # noqa: E402
from caja.contexto import ContextoApp  # noqa: E402
from caja.pantalla_reportes import PantallaReportes  # noqa: E402


def _ctx_con_venta():
    ctx = ContextoApp.crear(":memory:")
    ctx.svc_caja.abrir(fecha=datetime.now(), monto_inicial=Decimal("0"))
    sesion = ctx.repo_sesiones.abierta()
    v = ctx.nueva_venta()
    v.agregar("7700006")
    venta = v.confirmar(fecha=datetime.now(), caja_sesion_id=sesion.id)
    ctx.svc_registro.registrar(venta, [Pago(medio_pago_id=1, monto=Decimal("2500"))])
    return ctx


def test_consultar_llena_kpi_neto():
    _app = QApplication.instance() or QApplication([])
    ctx = _ctx_con_venta()
    win = PantallaReportes(ctx)
    win.al_mostrar()
    win._consultar()
    assert "2.500" in win._kpi_neto._valor.text()


def test_tabla_inventario_se_llena():
    _app = QApplication.instance() or QApplication([])
    ctx = _ctx_con_venta()
    win = PantallaReportes(ctx)
    win.al_mostrar()
    win._consultar()
    assert win._tabla_inventario.rowCount() >= 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/caja/test_pantalla_reportes.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'caja.pantalla_reportes'`

- [ ] **Step 3: Implement `pantalla_reportes.py`**

Create `src/caja/pantalla_reportes.py`:

```python
"""Pantalla de reportes: ventas / inventario por rango de fechas. Solo lectura."""
from __future__ import annotations

from datetime import datetime, time

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QDateEdit, QGridLayout, QHBoxLayout, QLabel, QPushButton, QTabWidget,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from caja.contexto import ContextoApp
from caja.formato import formato_moneda
from caja.widgets import TarjetaKpi


class PantallaReportes(QWidget):
    def __init__(self, ctx: ContextoApp) -> None:
        super().__init__()
        self._ctx = ctx

        self._desde = QDateEdit(QDate.currentDate()); self._desde.setCalendarPopup(True)
        self._hasta = QDateEdit(QDate.currentDate()); self._hasta.setCalendarPopup(True)
        boton = QPushButton("Consultar"); boton.setObjectName("primario")
        boton.clicked.connect(self._consultar)
        barra = QHBoxLayout()
        barra.addWidget(QLabel("Desde")); barra.addWidget(self._desde)
        barra.addWidget(QLabel("Hasta")); barra.addWidget(self._hasta)
        barra.addWidget(boton); barra.addStretch(1)

        # KPIs ventas
        self._kpi_num = TarjetaKpi("# Ventas")
        self._kpi_total = TarjetaKpi("Total bruto")
        self._kpi_iva = TarjetaKpi("IVA")
        self._kpi_dev = TarjetaKpi("Devoluciones")
        self._kpi_neto = TarjetaKpi("Neto")
        kpis = QGridLayout()
        for i, k in enumerate((self._kpi_num, self._kpi_total, self._kpi_iva,
                               self._kpi_dev, self._kpi_neto)):
            kpis.addWidget(k, 0, i)

        self._tabla_ventas = QTableWidget(0, 2)
        self._tabla_ventas.setHorizontalHeaderLabels(["Medio de pago", "Neto"])
        self._tabla_ventas.setEditTriggers(QTableWidget.NoEditTriggers)
        tab_ventas = QWidget(); lv = QVBoxLayout(tab_ventas)
        lv.addLayout(kpis); lv.addWidget(self._tabla_ventas)

        self._tabla_inventario = QTableWidget(0, 4)
        self._tabla_inventario.setHorizontalHeaderLabels(
            ["Producto", "Entradas", "Salidas", "Neto"])
        self._tabla_inventario.setEditTriggers(QTableWidget.NoEditTriggers)
        tab_inv = QWidget(); li = QVBoxLayout(tab_inv); li.addWidget(self._tabla_inventario)

        tabs = QTabWidget()
        tabs.addTab(tab_ventas, "Ventas")
        tabs.addTab(tab_inv, "Inventario")

        layout = QVBoxLayout(self)
        layout.addLayout(barra)
        layout.addWidget(tabs)

    def al_mostrar(self) -> None:
        self._consultar()

    def _rango(self) -> tuple[datetime, datetime]:
        d = self._desde.date().toPython()
        h = self._hasta.date().toPython()
        return (datetime.combine(d, time.min), datetime.combine(h, time.max))

    def _consultar(self) -> None:
        desde, hasta = self._rango()
        rv = self._ctx.svc_reportes.ventas(desde, hasta)
        self._kpi_num.set_valor(str(rv.num_ventas))
        self._kpi_total.set_valor(formato_moneda(rv.total))
        self._kpi_iva.set_valor(formato_moneda(rv.total_impuestos))
        self._kpi_dev.set_valor(formato_moneda(rv.total_devoluciones))
        self._kpi_neto.set_valor(formato_moneda(rv.neto))

        self._tabla_ventas.setRowCount(0)
        for medio_id, monto in rv.por_medio.items():
            medio = self._ctx.repo_medios_pago.por_id(medio_id)
            fila = self._tabla_ventas.rowCount()
            self._tabla_ventas.insertRow(fila)
            self._tabla_ventas.setItem(fila, 0, QTableWidgetItem(
                medio.nombre if medio else f"#{medio_id}"))
            self._tabla_ventas.setItem(fila, 1, QTableWidgetItem(formato_moneda(monto)))

        ri = self._ctx.svc_reportes.inventario(desde, hasta)
        self._tabla_inventario.setRowCount(0)
        for mp in ri.por_producto:
            prod = self._ctx.repo_productos.por_id(mp.producto_id)
            fila = self._tabla_inventario.rowCount()
            self._tabla_inventario.insertRow(fila)
            self._tabla_inventario.setItem(fila, 0, QTableWidgetItem(
                prod.nombre if prod else f"#{mp.producto_id}"))
            self._tabla_inventario.setItem(fila, 1, QTableWidgetItem(str(mp.entradas)))
            self._tabla_inventario.setItem(fila, 2, QTableWidgetItem(str(mp.salidas)))
            self._tabla_inventario.setItem(fila, 3, QTableWidgetItem(str(mp.neto)))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/caja/test_pantalla_reportes.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/caja/pantalla_reportes.py tests/caja/test_pantalla_reportes.py
git commit -m "feat(caja): PantallaReportes (ventas + inventario por rango)"
```

---

## Task 15: Shell + entry point (`ventana_principal.py`, `__main__.py`, `scripts/caja.py`)

**Files:**
- Create: `src/caja/ventana_principal.py`
- Create: `src/caja/__main__.py`
- Modify: `scripts/caja.py`
- Test: `tests/caja/test_ventana_principal.py`

**Interfaces:**
- Consumes: `ContextoApp` y las 6 pantallas; `BotonRail`; `tema.icono`.
- Produces:
  - `VentanaPrincipal(QMainWindow)`: `__init__(self, ctx: ContextoApp)`.
  - atributos de test: `_stack` (QStackedWidget), `_botones` (list[BotonRail]),
    `_pantallas` (list[QWidget]).
  - método `_ir_a(indice: int)`; `_refrescar_estado()`.

- [ ] **Step 1: Write the failing test**

Create `tests/caja/test_ventana_principal.py`:

```python
import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from datetime import datetime  # noqa: E402
from decimal import Decimal  # noqa: E402

from PySide6.QtWidgets import QApplication  # noqa: E402

from caja.contexto import ContextoApp  # noqa: E402
from caja.ventana_principal import VentanaPrincipal  # noqa: E402


def test_shell_tiene_seis_pantallas():
    _app = QApplication.instance() or QApplication([])
    win = VentanaPrincipal(ContextoApp.crear(":memory:"))
    assert len(win._pantallas) == 6
    assert win._stack.count() == 6


def test_navegar_cambia_pantalla_activa():
    _app = QApplication.instance() or QApplication([])
    win = VentanaPrincipal(ContextoApp.crear(":memory:"))
    win._ir_a(2)
    assert win._stack.currentIndex() == 2


def test_barra_estado_refleja_caja_abierta():
    _app = QApplication.instance() or QApplication([])
    ctx = ContextoApp.crear(":memory:")
    ctx.svc_caja.abrir(fecha=datetime.now(), monto_inicial=Decimal("0"))
    win = VentanaPrincipal(ctx)
    win._refrescar_estado()
    assert "abierta" in win.statusBar().currentMessage().lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/caja/test_ventana_principal.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'caja.ventana_principal'`

- [ ] **Step 3: Implement `ventana_principal.py`**

Create `src/caja/ventana_principal.py`:

```python
"""Shell de la app: rail de navegación + QStackedWidget + barra de estado."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QButtonGroup, QHBoxLayout, QMainWindow, QStackedWidget, QVBoxLayout, QWidget,
)

from caja.contexto import ContextoApp
from caja.formato import formato_moneda
from caja.pantalla_cierre import PantallaCierre
from caja.pantalla_clientes import PantallaClientes
from caja.pantalla_devoluciones import PantallaDevoluciones
from caja.pantalla_inventario import PantallaInventario
from caja.pantalla_reportes import PantallaReportes
from caja.pantalla_venta import PantallaVenta
from caja.tema import icono
from caja.widgets import BotonRail

# (icono, tooltip, factory)
_DEFINICION = [
    ("venta", "Venta", PantallaVenta),
    ("inventario", "Inventario", PantallaInventario),
    ("clientes", "Clientes", PantallaClientes),
    ("devoluciones", "Devoluciones", PantallaDevoluciones),
    ("reportes", "Reportes", PantallaReportes),
    ("cierre", "Cierre", PantallaCierre),
]


class VentanaPrincipal(QMainWindow):
    def __init__(self, ctx: ContextoApp) -> None:
        super().__init__()
        self._ctx = ctx
        self.setWindowTitle("POS — Carnes y Frutas")
        self.resize(1100, 720)

        self._stack = QStackedWidget()
        self._botones: list[BotonRail] = []
        self._pantallas: list[QWidget] = []
        self._grupo = QButtonGroup(self)
        self._grupo.setExclusive(True)

        rail = QWidget(); rail.setObjectName("rail"); rail.setFixedWidth(60)
        rail_layout = QVBoxLayout(rail)
        rail_layout.setContentsMargins(0, 8, 0, 8)

        for i, (ic, tip, factory) in enumerate(_DEFINICION):
            pantalla = self._construir_pantalla(factory)
            self._pantallas.append(pantalla)
            self._stack.addWidget(pantalla)
            boton = BotonRail(icono(ic), tip)
            boton.clicked.connect(lambda _=False, idx=i: self._ir_a(idx))
            self._grupo.addButton(boton, i)
            rail_layout.addWidget(boton)
            self._botones.append(boton)
        rail_layout.addStretch(1)

        central = QWidget(); central.setObjectName("fondo")
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(rail)
        layout.addWidget(self._stack, 1)
        self.setCentralWidget(central)

        self._botones[0].setChecked(True)
        self._ir_a(0)

    def _construir_pantalla(self, factory) -> QWidget:
        if factory is PantallaClientes:
            pantalla = factory(self._ctx.svc_clientes)
        else:
            pantalla = factory(self._ctx)
        if hasattr(pantalla, "caja_cambiada"):
            pantalla.caja_cambiada.connect(self._refrescar_estado)
        return pantalla

    def _ir_a(self, indice: int) -> None:
        self._stack.setCurrentIndex(indice)
        pantalla = self._pantallas[indice]
        if hasattr(pantalla, "al_mostrar"):
            pantalla.al_mostrar()
        self._refrescar_estado()

    def _refrescar_estado(self) -> None:
        sesion = self._ctx.repo_sesiones.abierta()
        if sesion is None:
            self.statusBar().showMessage("Caja cerrada")
            return
        efectivo = self._ctx.repo_ventas.totales_por_medio(sesion.id).get(1, None)
        from decimal import Decimal
        monto = efectivo if efectivo is not None else Decimal("0")
        self.statusBar().showMessage(
            f"● Caja #{sesion.id} abierta  ·  Efectivo: {formato_moneda(monto)}")
```

- [ ] **Step 4: Implement `__main__.py`**

Create `src/caja/__main__.py`:

```python
"""Entry point: python -m caja [ruta_db]."""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from caja.contexto import ContextoApp
from caja.tema import carga_tema
from caja.ventana_principal import VentanaPrincipal


def main(ruta_db: str = "pos.db") -> int:
    app = QApplication(sys.argv)
    carga_tema(app)
    ctx = ContextoApp.crear(ruta_db)
    ventana = VentanaPrincipal(ctx)
    ventana.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "pos.db"))
```

- [ ] **Step 5: Simplify `scripts/caja.py`**

Reemplaza `scripts/caja.py` por:

```python
"""Lanza el POS. Uso: python scripts/caja.py [pos.db]"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from caja.__main__ import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "pos.db"))
```

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/caja/test_ventana_principal.py -v`
Expected: PASS (3 passed)

- [ ] **Step 7: Run full suite + smoke launch**

Run: `pytest`
Expected: toda la suite verde (140 previos + nuevos).

Run (smoke, headless): `QT_QPA_PLATFORM=offscreen python -c "import sys; sys.path.insert(0,'src'); from caja.__main__ import main"`
Expected: importa sin error (no se llama a `main()` para no bloquear).

- [ ] **Step 8: Commit**

```bash
git add src/caja/ventana_principal.py src/caja/__main__.py scripts/caja.py tests/caja/test_ventana_principal.py
git commit -m "feat(caja): shell VentanaPrincipal + entry point python -m caja"
```

---

## Self-Review

**1. Spec coverage:**

| Sección spec | Tarea |
|---|---|
| §3 estructura archivos | Tasks 2–15 (todos los archivos creados) |
| §4 bootstrap + ContextoApp | Tasks 3, 4 |
| §5 extensiones puertos | Task 1 |
| §6 tema.qss + widgets | Tasks 5, 6 |
| §7 shell navegación | Task 15 |
| §8.1 PantallaVenta | Task 8 |
| §8.2 DialogoCobro | Task 7 |
| §8.3 PantallaInventario + dialogos | Tasks 9, 10 |
| §8.4 PantallaClientes | Task 11 |
| §8.5 PantallaDevoluciones | Task 12 |
| §8.6 PantallaCierre | Task 13 |
| §8.7 PantallaReportes | Task 14 |
| §9 formato.py | Task 2 |
| §10 manejo errores | integrado en cada pantalla (QLabel#error / QMessageBox) |
| §11 pruebas | tests en cada task |

Nota de desviación vs spec: la pestaña "Cierre por sesión" de Reportes (§8.7) se omite del
scope inicial — Reportes cubre Ventas e Inventario; el arqueo por sesión ya está en
PantallaCierre. `RepositorioCajaSesiones.listar()` se implementa igual (Task 1) por si se
añade luego. **Confirmar con el usuario si la pestaña de cierre en Reportes es obligatoria.**

**2. Placeholder scan:** sin TBD/TODO; todo el código está completo en cada step.

**3. Type consistency:** `al_mostrar()`, `caja_cambiada = Signal()`, `ContextoApp.nueva_venta()`,
`DialogoCobro.pagos()`, `formato_moneda/_cantidad/_fecha` usados consistentemente entre tasks.
`PantallaClientes` recibe `ServicioClientes` (no `ContextoApp`) — reflejado en Task 15 shell.

---

## Execution Handoff

Ver mensaje del asistente para elegir modo de ejecución.
