# Promociones por producto + Conteo de efectivo — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Añadir promociones por producto (precio fijo o %, con duración por tiempo/unidades/manual) que conviven con el descuento del cliente, y un ayudante opcional de conteo de efectivo por denominaciones en el cierre de caja.

**Architecture:** Hexagonal. El dominio de promociones (entidad, reglas de precio/vigencia/consumo, servicio) vive en `core/` sin Qt ni SQLite. La persistencia entra por el puerto `RepositorioPromociones` con adaptador SQLite en `inventario/`. `ServicioVenta` aplica la promo al precio del producto (antes del descuento del cliente); `ServicioRegistroVenta` consume unidades al registrar. El conteo es una ayuda 100% en la capa UI (`caja/`), con el cálculo como función pura testeable.

**Tech Stack:** Python 3.11, PySide6 (Qt6), SQLite (sqlite3 stdlib), pytest.

**Spec:** [../specs/2026-07-01-promociones-conteo-caja-design.md](../specs/2026-07-01-promociones-conteo-caja-design.md)

## Global Constraints

- `src/core/` NO conoce Qt ni SQLite; SQL solo en adaptadores de repositorio.
- Dinero/cantidades en `Decimal`; redondeo a peso colombiano entero con `ROUND_HALF_UP` (via `subtotal_por_peso`/`subtotal_por_unidad`/`impuesto_incluido` de `core/calculos.py`).
- Migraciones numeradas en `scripts/migraciones/`; la nueva es `006_promociones.sql`. El runner `inventario.db.aplicar_migraciones` es idempotente.
- Conexión de test: `inventario.db.conectar(":memory:")` + `aplicar_migraciones`; `Decimal` viaja como texto (adapters ya registrados en `inventario/db.py`).
- Tests `test_*.py` en estructura espejo (`tests/core/`, `tests/inventario/`, `tests/ventas/`, `tests/caja/`). Tests de UI Qt: `pytest.importorskip("PySide6")` + `QT_QPA_PLATFORM=offscreen` + `QApplication.instance() or QApplication([])`.
- Nombres de dominio en español. Reglas Ponytail: mínimo código, stdlib, YAGNI.
- Prefijos de task: `PROMO.x` (primero) y `CONTEO.x` (después). Usar el ID completo en cualquier tracking.
- Suite base al empezar: `python -m pytest -q` → 269 passed.

---

## File Structure

**Crear:**
- `src/core/promociones.py` — reglas puras: `promo_vigente`, `precio_con_promo`, `consumir_unidades`.
- `src/core/servicio_promociones.py` — `ServicioPromociones` (crear/activar/desactivar/listar) + `PromocionActivaExiste`.
- `scripts/migraciones/006_promociones.sql` — tabla `promociones` + `venta_lineas.promocion_id`.
- `src/caja/dialogos/dialogo_promociones.py` — `DialogoPromociones` (crear + listar/desactivar).
- `src/caja/conteo.py` — `DENOMINACIONES` + `total_conteo` (función pura).
- `src/caja/dialogos/dialogo_conteo.py` — `DialogoConteoEfectivo`.

**Modificar:**
- `src/core/entidades.py` — entidad `Promocion` + `LineaVenta.promocion_id`.
- `src/core/puertos.py` — `RepositorioPromociones`.
- `src/core/permisos.py` — acción `gestionar_promociones`.
- `src/core/servicio_venta.py` — `ServicioVenta` aplica promo; `ServicioRegistroVenta` consume unidades; `_Entrada.promocion_id`.
- `src/inventario/repositorio_sqlite.py` — `RepositorioPromocionesSQLite`.
- `src/ventas/repositorio_sqlite.py` — persistir/leer `venta_lineas.promocion_id`.
- `src/caja/contexto.py` — wiring de `repo_promociones`, `svc_promociones`, `nueva_venta`, `svc_registro`.
- `src/caja/pantalla_inventario.py` — botón "Promociones".
- `src/caja/pantalla_venta.py` — marca visual del precio promo (`etiqueta_linea`).
- `src/caja/pantalla_cierre.py` — botón "Contar efectivo".

---

## PROMO.1: Entidad Promocion + LineaVenta.promocion_id (core/entidades.py)

**Files:**
- Modify: `src/core/entidades.py`
- Test: `tests/core/test_promocion_entidad.py`

**Interfaces:**
- Produces: `Promocion(producto_id, tipo_valor, valor, tipo_duracion, activa=True, desde=None, hasta=None, unidades_limite=None, unidades_restantes=None, id=None)`; constantes `TIPOS_VALOR_PROMO`, `TIPOS_DURACION_PROMO`. `LineaVenta` gana `promocion_id: int | None = None`.

- [ ] **Step 1: Write the failing test**

```python
# tests/core/test_promocion_entidad.py
from datetime import datetime
from decimal import Decimal

import pytest

from core.entidades import LineaVenta, Promocion


def test_promo_precio_fijo_valida():
    p = Promocion(producto_id=1, tipo_valor="precio_fijo", valor=Decimal("8000"),
                  tipo_duracion="manual")
    assert p.activa is True


def test_promo_porcentaje_fuera_de_rango_rechaza():
    with pytest.raises(ValueError):
        Promocion(producto_id=1, tipo_valor="porcentaje", valor=Decimal("1"),
                  tipo_duracion="manual")


def test_promo_tiempo_exige_rango_ordenado():
    with pytest.raises(ValueError):
        Promocion(producto_id=1, tipo_valor="precio_fijo", valor=Decimal("8000"),
                  tipo_duracion="tiempo",
                  desde=datetime(2026, 7, 2), hasta=datetime(2026, 7, 1))


def test_promo_unidades_inicializa_restantes():
    p = Promocion(producto_id=1, tipo_valor="precio_fijo", valor=Decimal("8000"),
                  tipo_duracion="unidades", unidades_limite=Decimal("50"))
    assert p.unidades_restantes == Decimal("50")


def test_tipo_valor_invalido_rechaza():
    with pytest.raises(ValueError):
        Promocion(producto_id=1, tipo_valor="regalo", valor=Decimal("1"),
                  tipo_duracion="manual")


def test_linea_venta_acepta_promocion_id():
    ln = LineaVenta(producto_id=1, descripcion="X", cantidad_o_peso=Decimal("1"),
                    precio_unit=Decimal("8000"), impuesto=Decimal("0"),
                    subtotal=Decimal("8000"), promocion_id=5)
    assert ln.promocion_id == 5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/core/test_promocion_entidad.py -q`
Expected: FAIL (`ImportError: cannot import name 'Promocion'`).

- [ ] **Step 3: Write minimal implementation**

En `src/core/entidades.py`, añade `promocion_id` a `LineaVenta` (tras `subtotal`, antes de `venta_id`):

```python
@dataclass(frozen=True)
class LineaVenta:
    producto_id: int
    descripcion: str
    cantidad_o_peso: Decimal
    precio_unit: Decimal
    impuesto: Decimal
    subtotal: Decimal
    promocion_id: int | None = None
    venta_id: int | None = None
    id: int | None = None
```

Y al final del archivo añade la entidad y sus constantes:

```python
TIPOS_VALOR_PROMO = ("precio_fijo", "porcentaje")
TIPOS_DURACION_PROMO = ("tiempo", "unidades", "manual")


@dataclass(frozen=True)
class Promocion:
    producto_id: int
    tipo_valor: str            # "precio_fijo" | "porcentaje"
    valor: Decimal             # pesos (fijo) o fracción [0,1) (porcentaje)
    tipo_duracion: str         # "tiempo" | "unidades" | "manual"
    activa: bool = True
    desde: datetime | None = None
    hasta: datetime | None = None
    unidades_limite: Decimal | None = None
    unidades_restantes: Decimal | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        if self.tipo_valor not in TIPOS_VALOR_PROMO:
            raise ValueError(f"tipo_valor inválido: {self.tipo_valor!r}")
        if self.tipo_duracion not in TIPOS_DURACION_PROMO:
            raise ValueError(f"tipo_duracion inválido: {self.tipo_duracion!r}")
        if self.tipo_valor == "porcentaje" and not (CERO <= self.valor < Decimal("1")):
            raise ValueError("valor de porcentaje debe estar en [0, 1)")
        if self.tipo_valor == "precio_fijo" and self.valor < CERO:
            raise ValueError("precio fijo no puede ser negativo")
        if self.tipo_duracion == "tiempo":
            if self.desde is None or self.hasta is None:
                raise ValueError("promo por tiempo requiere desde y hasta")
            if self.desde > self.hasta:
                raise ValueError("desde no puede ser posterior a hasta")
        if self.tipo_duracion == "unidades":
            if self.unidades_limite is None or self.unidades_limite <= CERO:
                raise ValueError("promo por unidades requiere unidades_limite > 0")
            if self.unidades_restantes is None:
                object.__setattr__(self, "unidades_restantes", self.unidades_limite)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/core/test_promocion_entidad.py -q`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add src/core/entidades.py tests/core/test_promocion_entidad.py
git commit -m "feat(promociones): entidad Promocion + LineaVenta.promocion_id (PROMO.1)"
```

---

## PROMO.2: Reglas de dominio de promoción (core/promociones.py)

**Files:**
- Create: `src/core/promociones.py`
- Test: `tests/core/test_promociones_reglas.py`

**Interfaces:**
- Consumes: `Promocion` (PROMO.1).
- Produces: `promo_vigente(promo: Promocion, ahora: datetime) -> bool`; `precio_con_promo(precio_base: Decimal, promo: Promocion) -> Decimal`; `consumir_unidades(promo: Promocion, cantidad: Decimal) -> Promocion`.

- [ ] **Step 1: Write the failing test**

```python
# tests/core/test_promociones_reglas.py
from datetime import datetime
from decimal import Decimal

from core.entidades import Promocion
from core.promociones import consumir_unidades, precio_con_promo, promo_vigente

AHORA = datetime(2026, 7, 1, 12, 0)


def _fija(**kw):
    base = dict(producto_id=1, tipo_valor="precio_fijo", valor=Decimal("8000"),
                tipo_duracion="manual")
    base.update(kw)
    return Promocion(**base)


def test_manual_vigente_si_activa():
    assert promo_vigente(_fija(activa=True), AHORA) is True
    assert promo_vigente(_fija(activa=False), AHORA) is False


def test_tiempo_vigente_dentro_del_rango():
    p = _fija(tipo_duracion="tiempo",
              desde=datetime(2026, 7, 1, 0, 0), hasta=datetime(2026, 7, 1, 23, 59))
    assert promo_vigente(p, AHORA) is True


def test_tiempo_no_vigente_fuera_del_rango():
    p = _fija(tipo_duracion="tiempo",
              desde=datetime(2026, 6, 1), hasta=datetime(2026, 6, 30))
    assert promo_vigente(p, AHORA) is False


def test_unidades_vigente_si_restan():
    p = _fija(tipo_duracion="unidades", unidades_limite=Decimal("3"))
    assert promo_vigente(p, AHORA) is True
    agotada = _fija(tipo_duracion="unidades", unidades_limite=Decimal("3"),
                    unidades_restantes=Decimal("0"))
    assert promo_vigente(agotada, AHORA) is False


def test_precio_con_promo_fijo():
    assert precio_con_promo(Decimal("10000"), _fija(valor=Decimal("8000"))) == Decimal("8000")


def test_precio_con_promo_porcentaje():
    p = _fija(tipo_valor="porcentaje", valor=Decimal("0.2"))
    assert precio_con_promo(Decimal("2500"), p) == Decimal("2000")


def test_consumir_unidades_desactiva_al_agotar():
    p = _fija(tipo_duracion="unidades", unidades_limite=Decimal("2"))
    r = consumir_unidades(p, Decimal("2"))
    assert r.unidades_restantes == Decimal("0")
    assert r.activa is False


def test_consumir_unidades_deja_restante_positivo():
    p = _fija(tipo_duracion="unidades", unidades_limite=Decimal("5"))
    r = consumir_unidades(p, Decimal("2"))
    assert r.unidades_restantes == Decimal("3")
    assert r.activa is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/core/test_promociones_reglas.py -q`
Expected: FAIL (`ModuleNotFoundError: No module named 'core.promociones'`).

- [ ] **Step 3: Write minimal implementation**

```python
# src/core/promociones.py
"""Reglas de dominio de promociones por producto. Python puro."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from decimal import Decimal

from core.entidades import Promocion

CERO = Decimal("0")


def promo_vigente(promo: Promocion, ahora: datetime) -> bool:
    """True si la promo aplica ahora: activa y dentro de su duración."""
    if not promo.activa:
        return False
    if promo.tipo_duracion == "tiempo":
        return promo.desde <= ahora <= promo.hasta
    if promo.tipo_duracion == "unidades":
        return (promo.unidades_restantes or CERO) > CERO
    return True  # manual


def precio_con_promo(precio_base: Decimal, promo: Promocion) -> Decimal:
    """Precio efectivo del producto bajo la promo (sin cuantizar; el subtotal cuantiza)."""
    if promo.tipo_valor == "precio_fijo":
        return promo.valor
    return precio_base * (Decimal("1") - promo.valor)


def consumir_unidades(promo: Promocion, cantidad: Decimal) -> Promocion:
    """Descuenta `cantidad` de las unidades restantes; desactiva la promo si llega a <= 0."""
    restantes = (promo.unidades_restantes or CERO) - cantidad
    return replace(promo, unidades_restantes=restantes, activa=restantes > CERO)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/core/test_promociones_reglas.py -q`
Expected: PASS (8 passed).

- [ ] **Step 5: Commit**

```bash
git add src/core/promociones.py tests/core/test_promociones_reglas.py
git commit -m "feat(promociones): reglas vigencia/precio/consumo (PROMO.2)"
```

---

## PROMO.3: Puerto RepositorioPromociones + ServicioPromociones (core)

**Files:**
- Modify: `src/core/puertos.py`
- Create: `src/core/servicio_promociones.py`
- Test: `tests/core/test_servicio_promociones.py`

**Interfaces:**
- Consumes: `Promocion` (PROMO.1).
- Produces: `RepositorioPromociones` Protocol con `guardar(promo) -> Promocion`, `actualizar(promo) -> None`, `por_id(id) -> Promocion | None`, `activa_por_producto(producto_id) -> Promocion | None`, `listar() -> list[Promocion]`. `ServicioPromociones(promociones)` con `crear(promo) -> Promocion`, `activar(id) -> None`, `desactivar(id) -> None`, `listar() -> list[Promocion]`. Excepción `PromocionActivaExiste`.

- [ ] **Step 1: Write the failing test**

```python
# tests/core/test_servicio_promociones.py
from dataclasses import replace
from decimal import Decimal

import pytest

from core.entidades import Promocion
from core.servicio_promociones import PromocionActivaExiste, ServicioPromociones


class FakePromos:
    def __init__(self):
        self.items = {}
        self._next = 1

    def guardar(self, promo):
        pid = self._next
        self._next += 1
        guardada = replace(promo, id=pid)
        self.items[pid] = guardada
        return guardada

    def actualizar(self, promo):
        self.items[promo.id] = promo

    def por_id(self, id):
        return self.items.get(id)

    def activa_por_producto(self, producto_id):
        for p in self.items.values():
            if p.producto_id == producto_id and p.activa:
                return p
        return None

    def listar(self):
        return list(self.items.values())


def _promo(**kw):
    base = dict(producto_id=1, tipo_valor="precio_fijo", valor=Decimal("8000"),
                tipo_duracion="manual")
    base.update(kw)
    return Promocion(**base)


def test_crear_guarda_y_devuelve_con_id():
    svc = ServicioPromociones(FakePromos())
    guardada = svc.crear(_promo())
    assert guardada.id == 1


def test_crear_rechaza_segunda_promo_activa_del_mismo_producto():
    svc = ServicioPromociones(FakePromos())
    svc.crear(_promo())
    with pytest.raises(PromocionActivaExiste):
        svc.crear(_promo(valor=Decimal("7000")))


def test_desactivar_libera_el_producto():
    repo = FakePromos()
    svc = ServicioPromociones(repo)
    p = svc.crear(_promo())
    svc.desactivar(p.id)
    assert repo.por_id(p.id).activa is False
    svc.crear(_promo(valor=Decimal("7000")))  # ya no colisiona


def test_activar_vuelve_a_marcar_activa():
    repo = FakePromos()
    svc = ServicioPromociones(repo)
    p = svc.crear(_promo())
    svc.desactivar(p.id)
    svc.activar(p.id)
    assert repo.por_id(p.id).activa is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/core/test_servicio_promociones.py -q`
Expected: FAIL (`ModuleNotFoundError: No module named 'core.servicio_promociones'`).

- [ ] **Step 3: Write minimal implementation**

En `src/core/puertos.py` añade `Promocion` al import de `core.entidades` y este Protocol al final:

```python
class RepositorioPromociones(Protocol):
    def guardar(self, promo: Promocion) -> Promocion: ...
    def actualizar(self, promo: Promocion) -> None: ...
    def por_id(self, id: int) -> Promocion | None: ...
    def activa_por_producto(self, producto_id: int) -> Promocion | None: ...
    def listar(self) -> list[Promocion]: ...
```

Crea `src/core/servicio_promociones.py`:

```python
"""Servicio de gestión de promociones. Python puro: solo conoce el puerto."""
from __future__ import annotations

from dataclasses import replace

from core.entidades import Promocion
from core.puertos import RepositorioPromociones


class PromocionActivaExiste(ValueError):
    pass


class PromocionNoEncontrada(ValueError):
    pass


class ServicioPromociones:
    def __init__(self, promociones: RepositorioPromociones) -> None:
        self._promociones = promociones

    def crear(self, promo: Promocion) -> Promocion:
        if promo.activa and self._promociones.activa_por_producto(promo.producto_id) is not None:
            raise PromocionActivaExiste(
                f"el producto {promo.producto_id} ya tiene una promoción activa")
        return self._promociones.guardar(promo)

    def activar(self, promocion_id: int) -> None:
        self._set_activa(promocion_id, True)

    def desactivar(self, promocion_id: int) -> None:
        self._set_activa(promocion_id, False)

    def _set_activa(self, promocion_id: int, activa: bool) -> None:
        promo = self._promociones.por_id(promocion_id)
        if promo is None:
            raise PromocionNoEncontrada(f"promoción inexistente: {promocion_id}")
        self._promociones.actualizar(replace(promo, activa=activa))

    def listar(self) -> list[Promocion]:
        return self._promociones.listar()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/core/test_servicio_promociones.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add src/core/puertos.py src/core/servicio_promociones.py tests/core/test_servicio_promociones.py
git commit -m "feat(promociones): puerto + ServicioPromociones (PROMO.3)"
```

---

## PROMO.4: Migración 006 (tabla promociones + venta_lineas.promocion_id)

**Files:**
- Create: `scripts/migraciones/006_promociones.sql`
- Test: `tests/inventario/test_migraciones_006.py`

**Interfaces:**
- Produces: tabla `promociones` y columna `venta_lineas.promocion_id` en el esquema aplicado por `aplicar_migraciones`.

- [ ] **Step 1: Write the failing test**

```python
# tests/inventario/test_migraciones_006.py
from inventario.db import aplicar_migraciones, conectar


def _columnas(conn, tabla):
    return {r["name"] for r in conn.execute(f"PRAGMA table_info({tabla})")}


def test_crea_tabla_promociones():
    conn = conectar()
    aplicar_migraciones(conn)
    cols = _columnas(conn, "promociones")
    assert {"producto_id", "tipo_valor", "valor", "tipo_duracion", "activa",
            "desde", "hasta", "unidades_limite", "unidades_restantes"} <= cols


def test_venta_lineas_tiene_promocion_id():
    conn = conectar()
    aplicar_migraciones(conn)
    assert "promocion_id" in _columnas(conn, "venta_lineas")


def test_aplicar_migraciones_es_idempotente():
    conn = conectar()
    aplicar_migraciones(conn)
    aplicar_migraciones(conn)  # no debe lanzar "duplicate column name"
    assert "promocion_id" in _columnas(conn, "venta_lineas")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/inventario/test_migraciones_006.py -q`
Expected: FAIL (no existe la tabla `promociones`).

- [ ] **Step 3: Write minimal implementation**

```sql
-- scripts/migraciones/006_promociones.sql
-- 006: promociones por producto + vínculo de la línea de venta a la promo aplicada.
-- El runner (inventario.db.aplicar_migraciones) aplica cada archivo una sola vez.

CREATE TABLE IF NOT EXISTS promociones (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id        INTEGER NOT NULL REFERENCES productos(id),
    tipo_valor         TEXT NOT NULL,          -- 'precio_fijo' | 'porcentaje'
    valor              DECIMAL NOT NULL,       -- pesos (fijo) o fracción (porcentaje)
    tipo_duracion      TEXT NOT NULL,          -- 'tiempo' | 'unidades' | 'manual'
    activa             INTEGER NOT NULL DEFAULT 1,
    desde              TEXT,                   -- ISO datetime (tipo 'tiempo')
    hasta              TEXT,                   -- ISO datetime (tipo 'tiempo')
    unidades_limite    DECIMAL,
    unidades_restantes DECIMAL
);

ALTER TABLE venta_lineas ADD COLUMN promocion_id INTEGER REFERENCES promociones(id);
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/inventario/test_migraciones_006.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add scripts/migraciones/006_promociones.sql tests/inventario/test_migraciones_006.py
git commit -m "feat(promociones): migración 006 tabla promociones + venta_lineas.promocion_id (PROMO.4)"
```

---

## PROMO.5: Adaptador RepositorioPromocionesSQLite (inventario)

**Files:**
- Modify: `src/inventario/repositorio_sqlite.py`
- Test: `tests/inventario/test_repositorio_promociones.py`

**Interfaces:**
- Consumes: `RepositorioPromociones` (PROMO.3), tabla `promociones` (PROMO.4).
- Produces: `RepositorioPromocionesSQLite(conn)` que implementa el puerto.

- [ ] **Step 1: Write the failing test**

```python
# tests/inventario/test_repositorio_promociones.py
from datetime import datetime
from decimal import Decimal

import pytest

from core.entidades import Promocion
from inventario.db import aplicar_migraciones, conectar
from inventario.repositorio_sqlite import RepositorioPromocionesSQLite


@pytest.fixture
def conn():
    c = conectar()
    aplicar_migraciones(c)
    c.execute("INSERT INTO productos (codigo_barras, nombre, precio, costo, "
              "vendido_por_peso, unidad) VALUES ('1','Lomo','20000','0',1,'kg')")
    c.commit()
    yield c
    c.close()


def _promo(**kw):
    base = dict(producto_id=1, tipo_valor="precio_fijo", valor=Decimal("8000"),
                tipo_duracion="manual")
    base.update(kw)
    return Promocion(**base)


def test_guardar_y_por_id_roundtrip(conn):
    repo = RepositorioPromocionesSQLite(conn)
    guardada = repo.guardar(_promo())
    leida = repo.por_id(guardada.id)
    assert leida.valor == Decimal("8000")
    assert leida.tipo_duracion == "manual"
    assert leida.activa is True


def test_tiempo_roundtrip_conserva_fechas(conn):
    repo = RepositorioPromocionesSQLite(conn)
    p = repo.guardar(_promo(tipo_duracion="tiempo",
                            desde=datetime(2026, 7, 1, 8, 0),
                            hasta=datetime(2026, 7, 1, 20, 0)))
    leida = repo.por_id(p.id)
    assert leida.desde == datetime(2026, 7, 1, 8, 0)
    assert leida.hasta == datetime(2026, 7, 1, 20, 0)


def test_activa_por_producto_solo_devuelve_activa(conn):
    repo = RepositorioPromocionesSQLite(conn)
    p = repo.guardar(_promo())
    assert repo.activa_por_producto(1).id == p.id
    repo.actualizar(repo.por_id(p.id).__class__(**{**repo.por_id(p.id).__dict__, "activa": False}))
    assert repo.activa_por_producto(1) is None


def test_unidades_roundtrip(conn):
    repo = RepositorioPromocionesSQLite(conn)
    p = repo.guardar(_promo(tipo_duracion="unidades", unidades_limite=Decimal("5")))
    leida = repo.por_id(p.id)
    assert leida.unidades_limite == Decimal("5")
    assert leida.unidades_restantes == Decimal("5")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/inventario/test_repositorio_promociones.py -q`
Expected: FAIL (`ImportError: cannot import name 'RepositorioPromocionesSQLite'`).

- [ ] **Step 3: Write minimal implementation**

En `src/inventario/repositorio_sqlite.py` añade `Promocion` al import de `core.entidades` y al final del archivo:

```python
def _fila_a_promocion(f: sqlite3.Row) -> Promocion:
    return Promocion(
        producto_id=f["producto_id"],
        tipo_valor=f["tipo_valor"],
        valor=f["valor"],
        tipo_duracion=f["tipo_duracion"],
        activa=bool(f["activa"]),
        desde=datetime.fromisoformat(f["desde"]) if f["desde"] else None,
        hasta=datetime.fromisoformat(f["hasta"]) if f["hasta"] else None,
        unidades_limite=f["unidades_limite"],
        unidades_restantes=f["unidades_restantes"],
        id=f["id"],
    )


class RepositorioPromocionesSQLite:
    _COLS = ("producto_id, tipo_valor, valor, tipo_duracion, activa, "
             "desde, hasta, unidades_limite, unidades_restantes")

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def guardar(self, promo: Promocion) -> Promocion:
        cur = self._conn.execute(
            f"INSERT INTO promociones ({self._COLS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            self._valores(promo))
        self._conn.commit()
        return replace(promo, id=cur.lastrowid)

    def actualizar(self, promo: Promocion) -> None:
        cur = self._conn.execute(
            "UPDATE promociones SET producto_id = ?, tipo_valor = ?, valor = ?, "
            "tipo_duracion = ?, activa = ?, desde = ?, hasta = ?, "
            "unidades_limite = ?, unidades_restantes = ? WHERE id = ?",
            (*self._valores(promo), promo.id))
        if cur.rowcount == 0:
            raise LookupError(f"promoción inexistente: id={promo.id}")
        self._conn.commit()

    @staticmethod
    def _valores(promo: Promocion) -> tuple:
        return (
            promo.producto_id, promo.tipo_valor, promo.valor, promo.tipo_duracion,
            int(promo.activa),
            promo.desde.isoformat() if promo.desde else None,
            promo.hasta.isoformat() if promo.hasta else None,
            promo.unidades_limite, promo.unidades_restantes,
        )

    def por_id(self, id: int) -> Promocion | None:
        f = self._conn.execute("SELECT * FROM promociones WHERE id = ?", (id,)).fetchone()
        return _fila_a_promocion(f) if f else None

    def activa_por_producto(self, producto_id: int) -> Promocion | None:
        f = self._conn.execute(
            "SELECT * FROM promociones WHERE producto_id = ? AND activa = 1 "
            "ORDER BY id DESC LIMIT 1", (producto_id,)).fetchone()
        return _fila_a_promocion(f) if f else None

    def listar(self) -> list[Promocion]:
        filas = self._conn.execute("SELECT * FROM promociones ORDER BY id").fetchall()
        return [_fila_a_promocion(f) for f in filas]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/inventario/test_repositorio_promociones.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add src/inventario/repositorio_sqlite.py tests/inventario/test_repositorio_promociones.py
git commit -m "feat(promociones): RepositorioPromocionesSQLite (PROMO.5)"
```

---

## PROMO.6: ServicioVenta aplica la promo + wiring en ContextoApp

**Files:**
- Modify: `src/core/servicio_venta.py` (`_Entrada`, `ServicioVenta.__init__`, `agregar`, `agregar_escaneado`, `_linea`)
- Modify: `src/caja/contexto.py` (`repo_promociones`, `svc_promociones`, `nueva_venta`)
- Test: `tests/core/test_servicio_venta_promocion.py`

**Interfaces:**
- Consumes: `promo_vigente`, `precio_con_promo` (PROMO.2); `RepositorioPromociones` (PROMO.3).
- Produces: `ServicioVenta(productos, impuestos, promociones=None)`; `agregar(..., ahora=None)` fija el precio promo y `promocion_id` en la línea. `ContextoApp.repo_promociones`, `ContextoApp.svc_promociones`, `nueva_venta()` inyecta el repo de promociones.

- [ ] **Step 1: Write the failing test**

```python
# tests/core/test_servicio_venta_promocion.py
from datetime import datetime
from decimal import Decimal

from core.entidades import Impuesto, Producto, Promocion
from core.servicio_venta import ServicioVenta

AHORA = datetime(2026, 7, 1, 12, 0)


class FakeProductos:
    def __init__(self, productos):
        self._por_codigo = {p.codigo_barras: p for p in productos}

    def por_codigo(self, codigo):
        return self._por_codigo.get(codigo)


class FakeImpuestos:
    def __init__(self, impuestos):
        self._por_id = {i.id: i for i in impuestos}

    def por_id(self, id):
        return self._por_id.get(id)


class FakePromos:
    def __init__(self, promo=None):
        self._promo = promo

    def activa_por_producto(self, producto_id):
        return self._promo if self._promo and self._promo.producto_id == producto_id else None


def _servicio(promo=None):
    lomo = Producto(codigo_barras="1", nombre="Lomo", precio=Decimal("20000"),
                    vendido_por_peso=True, unidad="kg", impuesto_id=1, id=1)
    iva = Impuesto(nombre="IVA 0%", tarifa=Decimal("0"), id=1)
    return ServicioVenta(FakeProductos([lomo]), FakeImpuestos([iva]), FakePromos(promo))


def _promo(**kw):
    base = dict(producto_id=1, tipo_valor="precio_fijo", valor=Decimal("15000"),
                tipo_duracion="manual")
    base.update(kw)
    return Promocion(**base)


def test_promo_fija_baja_el_precio_de_la_linea():
    s = _servicio(_promo())
    linea = s.agregar("1", peso_kg=Decimal("2"), ahora=AHORA)
    assert linea.subtotal == Decimal("30000")  # 15000 * 2
    assert linea.promocion_id == 1


def test_sin_promo_precio_normal():
    s = _servicio(None)
    linea = s.agregar("1", peso_kg=Decimal("2"), ahora=AHORA)
    assert linea.subtotal == Decimal("40000")
    assert linea.promocion_id is None


def test_promo_no_vigente_no_aplica():
    vencida = _promo(tipo_duracion="tiempo",
                     desde=datetime(2026, 6, 1), hasta=datetime(2026, 6, 30))
    s = _servicio(vencida)
    linea = s.agregar("1", peso_kg=Decimal("2"), ahora=AHORA)
    assert linea.subtotal == Decimal("40000")
    assert linea.promocion_id is None


def test_promo_se_acumula_con_descuento_de_cliente():
    s = _servicio(_promo())            # precio promo 15000/kg
    s.establecer_descuento(Decimal("0.1"))
    linea = s.agregar("1", peso_kg=Decimal("2"), ahora=AHORA)
    # 15000*2 = 30000 → descuento 10% → 27000
    assert linea.subtotal == Decimal("27000")


def test_promo_porcentaje_recalcula_iva_incluido():
    lomo = Producto(codigo_barras="1", nombre="Lomo", precio=Decimal("2500"),
                    impuesto_id=1, id=1)
    iva = Impuesto(nombre="IVA 19%", tarifa=Decimal("0.19"), id=1)
    s = ServicioVenta(FakeProductos([lomo]), FakeImpuestos([iva]),
                      FakePromos(_promo(tipo_valor="porcentaje", valor=Decimal("0.2"))))
    linea = s.agregar("1", cantidad=2, ahora=AHORA)
    # precio 2500*0.8=2000; subtotal 4000; IVA incluido round(4000*0.19/1.19)=639
    assert linea.subtotal == Decimal("4000")
    assert linea.impuesto == Decimal("639")


def test_gs1_con_importe_embebido_ignora_promo():
    s = _servicio(_promo())
    linea = s.agregar("1", peso_kg=Decimal("2"), importe=Decimal("40000"), ahora=AHORA)
    assert linea.subtotal == Decimal("40000")  # el importe manda
    assert linea.promocion_id is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/core/test_servicio_venta_promocion.py -q`
Expected: FAIL (`ServicioVenta.__init__` no acepta `promociones`).

- [ ] **Step 3: Write minimal implementation**

En `src/core/servicio_venta.py`:

1) Añade imports al bloque de `core`:

```python
from core.promociones import precio_con_promo, promo_vigente
from core.puertos import (
    RepositorioDevoluciones, RepositorioImpuestos, RepositorioInventario,
    RepositorioProductos, RepositorioPromociones, RepositorioVentas,
)
```

2) Añade `promocion_id` a `_Entrada`:

```python
@dataclass
class _Entrada:
    producto_id: int
    descripcion: str
    cantidad_o_peso: Decimal
    precio_unit: Decimal
    subtotal_bruto: Decimal
    tarifa: Decimal
    promocion_id: int | None = None
```

3) Reemplaza `__init__`, `agregar`, `_linea` y `agregar_escaneado` de `ServicioVenta`:

```python
    def __init__(self, productos: RepositorioProductos, impuestos: RepositorioImpuestos,
                 promociones: RepositorioPromociones | None = None) -> None:
        self._productos = productos
        self._impuestos = impuestos
        self._promociones = promociones
        self._entradas: list[_Entrada] = []
        self.descuento_pct: Decimal = CERO

    def _promo_para(self, producto: Producto, importe: Decimal | None,
                    ahora: datetime | None):
        if self._promociones is None or importe is not None:
            return None
        promo = self._promociones.activa_por_producto(producto.id)
        if promo is not None and promo_vigente(promo, ahora or datetime.now()):
            return promo
        return None

    def agregar(self, codigo_barras: str, *, cantidad: Decimal | int = 1,
                peso_kg: Decimal | None = None, importe: Decimal | None = None,
                ahora: datetime | None = None) -> LineaVenta:
        producto = self._productos.por_codigo(codigo_barras)
        if producto is None:
            raise ProductoNoEncontrado(f"producto inexistente: {codigo_barras!r}")
        tarifa = CERO
        if producto.impuesto_id is not None:
            impuesto = self._impuestos.por_id(producto.impuesto_id)
            if impuesto is not None:
                tarifa = impuesto.tarifa
        promo = self._promo_para(producto, importe, ahora)
        precio = precio_con_promo(producto.precio, promo) if promo is not None else producto.precio
        if producto.vendido_por_peso:
            if peso_kg is None:
                raise PesoRequerido(f"{producto.nombre} se vende por peso")
            cantidad_o_peso = peso_kg
            bruto = importe if importe is not None else subtotal_por_peso(precio, peso_kg)
        else:
            if importe is not None:
                raise ValueError(
                    f"{producto.nombre} se vende por unidad; importe no aplica")
            cantidad_o_peso = Decimal(cantidad)
            bruto = subtotal_por_unidad(precio, cantidad_o_peso)
        entrada = _Entrada(
            producto_id=producto.id, descripcion=producto.nombre,
            cantidad_o_peso=cantidad_o_peso, precio_unit=precio,
            subtotal_bruto=bruto, tarifa=tarifa,
            promocion_id=promo.id if promo is not None else None)
        self._entradas.append(entrada)
        return self._linea(entrada)

    def _linea(self, e: _Entrada) -> LineaVenta:
        subtotal = aplicar_descuento(e.subtotal_bruto, self.descuento_pct)
        return LineaVenta(
            producto_id=e.producto_id, descripcion=e.descripcion,
            cantidad_o_peso=e.cantidad_o_peso, precio_unit=e.precio_unit,
            impuesto=impuesto_incluido(subtotal, e.tarifa), subtotal=subtotal,
            promocion_id=e.promocion_id)

    def agregar_escaneado(self, codigo: str,
                          formato: FormatoGS1 = FORMATO_PESO_DEFECTO,
                          ahora: datetime | None = None) -> LineaVenta:
        """Agrega según un código escaneado: GS1 de peso variable o EAN/PLU normal."""
        if not es_peso_variable(codigo, formato):
            return self.agregar(codigo, cantidad=1, ahora=ahora)
        resultado = decodificar_gs1(codigo, formato)
        producto = self._productos.por_codigo(resultado.codigo_producto)
        if producto is None:
            raise ProductoNoEncontrado(
                f"producto inexistente: {resultado.codigo_producto!r} (código {codigo!r})")
        if not producto.vendido_por_peso:
            raise ValueError(
                f"{producto.nombre} no se vende por peso pero el código es de peso variable")
        peso, importe = peso_e_importe_gs1(resultado, producto, formato.valor_es_precio)
        return self.agregar(resultado.codigo_producto, peso_kg=peso, importe=importe, ahora=ahora)
```

4) En `src/caja/contexto.py`: importa el adaptador y el servicio, añade los campos y el wiring.

En el import de `inventario.repositorio_sqlite` añade `RepositorioPromocionesSQLite`; añade
`from core.servicio_promociones import ServicioPromociones`. Añade a la dataclass:

```python
    repo_promociones: RepositorioPromocionesSQLite = None  # type: ignore[assignment]
    svc_promociones: ServicioPromociones = None            # type: ignore[assignment]
```

En `desde_conn`, tras crear `usuarios`:

```python
        promociones = RepositorioPromocionesSQLite(conn)
```

y en el `return cls(...)` añade `repo_promociones=promociones,
svc_promociones=ServicioPromociones(promociones),`.

Cambia `nueva_venta`:

```python
    def nueva_venta(self) -> ServicioVenta:
        return ServicioVenta(self.repo_productos, self.repo_impuestos, self.repo_promociones)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/core/test_servicio_venta_promocion.py tests/caja/test_contexto.py -q`
Expected: PASS.

- [ ] **Step 5: Run full suite (no regression in existing ventas tests)**

Run: `python -m pytest tests/core/test_servicio_venta.py tests/core/test_servicio_venta_descuento.py -q`
Expected: PASS (las llamadas existentes a `agregar`/`ServicioVenta` siguen válidas; `promociones` es opcional).

- [ ] **Step 6: Commit**

```bash
git add src/core/servicio_venta.py src/caja/contexto.py tests/core/test_servicio_venta_promocion.py
git commit -m "feat(promociones): ServicioVenta aplica promo + wiring contexto (PROMO.6)"
```

---

## PROMO.7: Consumo de unidades al registrar la venta

**Files:**
- Modify: `src/core/servicio_venta.py` (`ServicioRegistroVenta`)
- Modify: `src/caja/contexto.py` (`svc_registro` recibe promociones)
- Test: `tests/core/test_registro_venta_promocion.py`

**Interfaces:**
- Consumes: `consumir_unidades` (PROMO.2); `RepositorioPromociones` (PROMO.3).
- Produces: `ServicioRegistroVenta(ventas, inventario, promociones=None)`; al registrar, descuenta unidades de las promos de tipo `unidades` referidas por las líneas.

- [ ] **Step 1: Write the failing test**

```python
# tests/core/test_registro_venta_promocion.py
from dataclasses import replace
from datetime import datetime
from decimal import Decimal

from core.entidades import LineaVenta, Pago, Promocion, Venta
from core.servicio_venta import ServicioRegistroVenta


class _FakeVentas:
    def guardar(self, venta, pagos):
        return replace(venta, id=77)


class _FakeInventario:
    def registrar(self, m):
        return m


class _FakePromos:
    def __init__(self, promo):
        self.items = {promo.id: promo}

    def por_id(self, id):
        return self.items.get(id)

    def actualizar(self, promo):
        self.items[promo.id] = promo


def _venta_con_promo(promocion_id):
    linea = LineaVenta(producto_id=1, descripcion="Lomo", cantidad_o_peso=Decimal("2"),
                       precio_unit=Decimal("15000"), impuesto=Decimal("0"),
                       subtotal=Decimal("30000"), promocion_id=promocion_id)
    return Venta(fecha=datetime(2026, 7, 1, 10, 0), lineas=(linea,),
                 total=Decimal("30000"), total_impuestos=Decimal("0"))


def test_registrar_consume_unidades_de_la_promo():
    promo = Promocion(producto_id=1, tipo_valor="precio_fijo", valor=Decimal("15000"),
                      tipo_duracion="unidades", unidades_limite=Decimal("5"), id=9)
    promos = _FakePromos(promo)
    svc = ServicioRegistroVenta(_FakeVentas(), _FakeInventario(), promos)
    svc.registrar(_venta_con_promo(9), [Pago(medio_pago_id=1, monto=Decimal("30000"))])
    assert promos.por_id(9).unidades_restantes == Decimal("3")


def test_registrar_sin_promo_no_falla():
    svc = ServicioRegistroVenta(_FakeVentas(), _FakeInventario())
    guardada = svc.registrar(_venta_con_promo(None),
                             [Pago(medio_pago_id=1, monto=Decimal("30000"))])
    assert guardada.id == 77
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/core/test_registro_venta_promocion.py -q`
Expected: FAIL (`ServicioRegistroVenta.__init__` no acepta `promociones`).

- [ ] **Step 3: Write minimal implementation**

En `src/core/servicio_venta.py`, añade el import `from core.promociones import consumir_unidades, precio_con_promo, promo_vigente` (extiende el que hiciste en PROMO.6) y reemplaza `ServicioRegistroVenta`:

```python
class ServicioRegistroVenta:
    def __init__(self, ventas: RepositorioVentas, inventario: RepositorioInventario,
                 promociones: RepositorioPromociones | None = None) -> None:
        self._ventas = ventas
        self._inventario = inventario
        self._promociones = promociones

    def registrar(self, venta: Venta, pagos: list[Pago]) -> Venta:
        guardada = self._ventas.guardar(venta, pagos)
        self._consumir_promos(guardada)
        for movimiento in salidas_de_venta(guardada):
            self._inventario.registrar(movimiento)
        return guardada

    def _consumir_promos(self, venta: Venta) -> None:
        if self._promociones is None:
            return
        for linea in venta.lineas:
            if linea.promocion_id is None:
                continue
            promo = self._promociones.por_id(linea.promocion_id)
            if promo is not None and promo.tipo_duracion == "unidades":
                self._promociones.actualizar(consumir_unidades(promo, linea.cantidad_o_peso))
```

En `src/caja/contexto.py`, cambia el wiring de `svc_registro`:

```python
            svc_registro=ServicioRegistroVenta(ventas, inventario, promociones),
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/core/test_registro_venta_promocion.py tests/core/test_registro_venta.py -q`
Expected: PASS (los tests existentes de registro sin promo siguen pasando).

- [ ] **Step 5: Commit**

```bash
git add src/core/servicio_venta.py src/caja/contexto.py tests/core/test_registro_venta_promocion.py
git commit -m "feat(promociones): consumo de unidades al registrar (PROMO.7)"
```

---

## PROMO.8: Persistir promocion_id en el adaptador de ventas

**Files:**
- Modify: `src/ventas/repositorio_sqlite.py` (`_fila_a_linea`, `RepositorioVentasSQLite.guardar`)
- Test: `tests/ventas/test_repositorio_ventas_promocion.py`

**Interfaces:**
- Consumes: columna `venta_lineas.promocion_id` (PROMO.4).
- Produces: `RepositorioVentasSQLite.guardar` escribe `promocion_id`; `por_id` lo lee en `LineaVenta.promocion_id`.

- [ ] **Step 1: Write the failing test**

```python
# tests/ventas/test_repositorio_ventas_promocion.py
from datetime import datetime
from decimal import Decimal

import pytest

from core.entidades import LineaVenta, Pago, Venta
from inventario.db import aplicar_migraciones, conectar
from ventas.repositorio_sqlite import RepositorioVentasSQLite


@pytest.fixture
def conn():
    c = conectar()
    aplicar_migraciones(c)
    c.execute("INSERT INTO productos (codigo_barras, nombre, precio, costo, "
              "vendido_por_peso, unidad) VALUES ('1','Lomo','20000','0',1,'kg')")
    c.execute("INSERT INTO promociones (producto_id, tipo_valor, valor, tipo_duracion, activa) "
              "VALUES (1,'precio_fijo','15000','manual',1)")
    c.commit()
    yield c
    c.close()


def _venta(promocion_id):
    linea = LineaVenta(producto_id=1, descripcion="Lomo", cantidad_o_peso=Decimal("2"),
                       precio_unit=Decimal("15000"), impuesto=Decimal("0"),
                       subtotal=Decimal("30000"), promocion_id=promocion_id)
    return Venta(fecha=datetime(2026, 7, 1, 10, 0), lineas=(linea,),
                 total=Decimal("30000"), total_impuestos=Decimal("0"))


def test_guardar_y_leer_promocion_id(conn):
    repo = RepositorioVentasSQLite(conn)
    guardada = repo.guardar(_venta(1), [Pago(medio_pago_id=1, monto=Decimal("30000"))])
    leida = repo.por_id(guardada.id)
    assert leida.lineas[0].promocion_id == 1


def test_linea_sin_promo_queda_none(conn):
    repo = RepositorioVentasSQLite(conn)
    guardada = repo.guardar(_venta(None), [Pago(medio_pago_id=1, monto=Decimal("30000"))])
    assert repo.por_id(guardada.id).lineas[0].promocion_id is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/ventas/test_repositorio_ventas_promocion.py -q`
Expected: FAIL (el `INSERT` de `venta_lineas` no incluye `promocion_id`; `_fila_a_linea` no lo lee → `promocion_id` siempre `None` en el primer test).

- [ ] **Step 3: Write minimal implementation**

En `src/ventas/repositorio_sqlite.py`:

1) En `_fila_a_linea`, añade `promocion_id=f["promocion_id"],` (antes de `venta_id`).

2) En `RepositorioVentasSQLite.guardar`, cambia el INSERT de líneas:

```python
        for linea in venta.lineas:
            self._conn.execute(
                "INSERT INTO venta_lineas "
                "(venta_id, producto_id, descripcion, cantidad_o_peso, precio_unit, "
                "impuesto, subtotal, promocion_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (venta_id, linea.producto_id, linea.descripcion, linea.cantidad_o_peso,
                 linea.precio_unit, linea.impuesto, linea.subtotal, linea.promocion_id))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/ventas/test_repositorio_ventas_promocion.py tests/ventas/test_repositorio_ventas.py -q`
Expected: PASS (los tests de ventas existentes siguen pasando).

- [ ] **Step 5: Commit**

```bash
git add src/ventas/repositorio_sqlite.py tests/ventas/test_repositorio_ventas_promocion.py
git commit -m "feat(promociones): persistir venta_lineas.promocion_id (PROMO.8)"
```

---

## PROMO.9: Permiso gestionar_promociones (core/permisos.py)

**Files:**
- Modify: `src/core/permisos.py`
- Test: `tests/core/test_permisos.py` (añadir casos)

**Interfaces:**
- Produces: `ACCION_GESTIONAR_PROMOCIONES = "gestionar_promociones"`; `puede(rol, ACCION_GESTIONAR_PROMOCIONES)` es `True` para admin y cajero.

- [ ] **Step 1: Write the failing test**

Añade a `tests/core/test_permisos.py`:

```python
def test_ambos_roles_pueden_gestionar_promociones():
    from core.permisos import ACCION_GESTIONAR_PROMOCIONES, puede
    assert puede("admin", ACCION_GESTIONAR_PROMOCIONES) is True
    assert puede("cajero", ACCION_GESTIONAR_PROMOCIONES) is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/core/test_permisos.py::test_ambos_roles_pueden_gestionar_promociones -q`
Expected: FAIL (`ImportError: cannot import name 'ACCION_GESTIONAR_PROMOCIONES'`).

- [ ] **Step 3: Write minimal implementation**

En `src/core/permisos.py`, añade la constante (fuera de `PERMISOS_ADMIN`, para que ambos roles la tengan):

```python
ACCION_GESTIONAR_PROMOCIONES = "gestionar_promociones"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/core/test_permisos.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/core/permisos.py tests/core/test_permisos.py
git commit -m "feat(promociones): permiso gestionar_promociones para ambos roles (PROMO.9)"
```

---

## PROMO.10: DialogoPromociones + botón en pantalla de inventario

**Files:**
- Create: `src/caja/dialogos/dialogo_promociones.py`
- Modify: `src/caja/pantalla_inventario.py` (botón "Promociones")
- Test: `tests/caja/test_dialogo_promociones.py`

**Interfaces:**
- Consumes: `Promocion` (PROMO.1); `ServicioPromociones` (PROMO.3); `ContextoApp.svc_promociones`, `repo_productos` (PROMO.6); `ACCION_GESTIONAR_PROMOCIONES` (PROMO.9).
- Produces: `DialogoPromociones(productos, svc_promociones, parent=None)` con método `promocion() -> Promocion` que construye la entidad desde los widgets y un botón "Crear" que la persiste vía `svc_promociones.crear`.

- [ ] **Step 1: Write the failing test**

```python
# tests/caja/test_dialogo_promociones.py
import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from decimal import Decimal  # noqa: E402

from PySide6.QtWidgets import QApplication  # noqa: E402

from core.entidades import Producto  # noqa: E402
from core.servicio_promociones import ServicioPromociones  # noqa: E402
from caja.dialogos.dialogo_promociones import DialogoPromociones  # noqa: E402

PRODS = [Producto(codigo_barras="1", nombre="Lomo", precio=Decimal("20000"),
                  vendido_por_peso=True, unidad="kg", id=1)]


class FakePromos:
    def __init__(self):
        self.items = {}
        self._n = 1

    def guardar(self, promo):
        from dataclasses import replace
        g = replace(promo, id=self._n); self.items[self._n] = g; self._n += 1
        return g

    def actualizar(self, promo):
        self.items[promo.id] = promo

    def por_id(self, id):
        return self.items.get(id)

    def activa_por_producto(self, producto_id):
        return next((p for p in self.items.values()
                     if p.producto_id == producto_id and p.activa), None)

    def listar(self):
        return list(self.items.values())


def _dialogo():
    _app = QApplication.instance() or QApplication([])
    return DialogoPromociones(PRODS, ServicioPromociones(FakePromos()))


def test_construye_promo_precio_fijo():
    d = _dialogo()
    d._producto.setCurrentIndex(0)
    d._tipo_valor.setCurrentText("precio_fijo")
    d._valor.setValue(15000)
    d._tipo_duracion.setCurrentText("manual")
    p = d.promocion()
    assert p.producto_id == 1
    assert p.tipo_valor == "precio_fijo"
    assert p.valor == Decimal("15000")
    assert p.tipo_duracion == "manual"


def test_construye_promo_porcentaje_convierte_a_fraccion():
    d = _dialogo()
    d._producto.setCurrentIndex(0)
    d._tipo_valor.setCurrentText("porcentaje")
    d._valor.setValue(20)
    d._tipo_duracion.setCurrentText("manual")
    p = d.promocion()
    assert p.tipo_valor == "porcentaje"
    assert p.valor == Decimal("0.2")


def test_crear_persiste_via_servicio():
    d = _dialogo()
    d._producto.setCurrentIndex(0)
    d._tipo_valor.setCurrentText("precio_fijo")
    d._valor.setValue(15000)
    d._tipo_duracion.setCurrentText("unidades")
    d._unidades.setValue(50)
    d._crear()
    assert len(d._svc.listar()) == 1
    assert d._svc.listar()[0].unidades_limite == Decimal("50")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/caja/test_dialogo_promociones.py -q`
Expected: FAIL (`ModuleNotFoundError: No module named 'caja.dialogos.dialogo_promociones'`).

- [ ] **Step 3: Write minimal implementation**

Crea `src/caja/dialogos/dialogo_promociones.py`:

```python
"""Diálogo crear/listar/desactivar promociones por producto (admin o cajero)."""
from __future__ import annotations

from decimal import Decimal

from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QComboBox, QDateTimeEdit, QDialog, QDoubleSpinBox, QFormLayout, QHBoxLayout,
    QLabel, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from core.entidades import Producto, Promocion
from core.servicio_promociones import PromocionActivaExiste, ServicioPromociones

_COLS = ["ID", "Producto", "Valor", "Duración", "Activa"]


class DialogoPromociones(QDialog):
    def __init__(self, productos: list[Producto], svc_promociones: ServicioPromociones,
                 parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Promociones")
        self._svc = svc_promociones
        self._productos = productos

        self._producto = QComboBox()
        for p in productos:
            self._producto.addItem(p.nombre, p.id)
        self._tipo_valor = QComboBox(); self._tipo_valor.addItems(["precio_fijo", "porcentaje"])
        self._valor = QDoubleSpinBox(); self._valor.setMaximum(99_999_999); self._valor.setDecimals(0)
        self._tipo_duracion = QComboBox()
        self._tipo_duracion.addItems(["manual", "tiempo", "unidades"])
        self._desde = QDateTimeEdit(); self._desde.setCalendarPopup(True)
        self._hasta = QDateTimeEdit(); self._hasta.setCalendarPopup(True)
        self._unidades = QDoubleSpinBox(); self._unidades.setMaximum(99_999_999)
        self._unidades.setDecimals(0)
        self._estado = QLabel(""); self._estado.setObjectName("error")

        form = QFormLayout()
        form.addRow("Producto", self._producto)
        form.addRow("Tipo de valor", self._tipo_valor)
        form.addRow("Valor (pesos o %)", self._valor)
        form.addRow("Duración", self._tipo_duracion)
        form.addRow("Desde", self._desde)
        form.addRow("Hasta", self._hasta)
        form.addRow("Unidades", self._unidades)

        boton_crear = QPushButton("Crear"); boton_crear.setObjectName("primario")
        boton_crear.clicked.connect(self._crear)
        boton_desactivar = QPushButton("Desactivar seleccionada")
        boton_desactivar.clicked.connect(self._desactivar)
        barra = QHBoxLayout(); barra.addWidget(boton_crear); barra.addWidget(boton_desactivar)

        self._tabla = QTableWidget(0, len(_COLS))
        self._tabla.setHorizontalHeaderLabels(_COLS)
        self._tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self._tabla.setSelectionBehavior(QTableWidget.SelectRows)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(barra)
        layout.addWidget(self._estado)
        layout.addWidget(self._tabla)
        self._refrescar()

    def promocion(self) -> Promocion:
        tipo_valor = self._tipo_valor.currentText()
        if tipo_valor == "porcentaje":
            valor = Decimal(str(self._valor.value())) / Decimal("100")
        else:
            valor = Decimal(str(int(self._valor.value())))
        duracion = self._tipo_duracion.currentText()
        desde = self._desde.dateTime().toPython() if duracion == "tiempo" else None
        hasta = self._hasta.dateTime().toPython() if duracion == "tiempo" else None
        unidades = (Decimal(str(int(self._unidades.value())))
                    if duracion == "unidades" else None)
        return Promocion(
            producto_id=self._producto.currentData(),
            tipo_valor=tipo_valor, valor=valor, tipo_duracion=duracion,
            desde=desde, hasta=hasta, unidades_limite=unidades)

    @Slot()
    def _crear(self) -> None:
        try:
            self._svc.crear(self.promocion())
        except (PromocionActivaExiste, ValueError) as exc:
            self._estado.setText(f"Error: {exc}")
            return
        self._estado.setText("")
        self._refrescar()

    @Slot()
    def _desactivar(self) -> None:
        fila = self._tabla.currentRow()
        promos = self._svc.listar()
        if 0 <= fila < len(promos):
            self._svc.desactivar(promos[fila].id)
            self._refrescar()

    def _refrescar(self) -> None:
        nombres = {p.id: p.nombre for p in self._productos}
        promos = self._svc.listar()
        self._tabla.setRowCount(0)
        for promo in promos:
            fila = self._tabla.rowCount()
            self._tabla.insertRow(fila)
            valor = (f"{promo.valor:.0%}" if promo.tipo_valor == "porcentaje"
                     else f"${promo.valor:,.0f}")
            celdas = [str(promo.id), nombres.get(promo.producto_id, "—"), valor,
                      promo.tipo_duracion, "sí" if promo.activa else "no"]
            for col, texto in enumerate(celdas):
                self._tabla.setItem(fila, col, QTableWidgetItem(texto))
```

En `src/caja/pantalla_inventario.py`: importa el diálogo y el permiso, añade un botón "Promociones"
que lo abre. En el import añade:

```python
from caja.dialogos.dialogo_promociones import DialogoPromociones
from core.permisos import ACCION_EDITAR_PRODUCTOS, ACCION_GESTIONAR_PROMOCIONES, puede
```

En `__init__`, tras crear `self._boton_mov`:

```python
        self._boton_promos = QPushButton("Promociones")
        self._boton_promos.clicked.connect(self._abrir_promociones)
        self._boton_promos.setVisible(puede(rol, ACCION_GESTIONAR_PROMOCIONES))
```

Añade `barra.addWidget(self._boton_promos)` tras `barra.addWidget(self._boton_mov)`, y el slot:

```python
    @Slot()
    def _abrir_promociones(self) -> None:
        dlg = DialogoPromociones(self._ctx.repo_productos.listar(),
                                 self._ctx.svc_promociones, parent=self)
        dlg.exec()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/caja/test_dialogo_promociones.py tests/caja/test_pantalla_inventario.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/caja/dialogos/dialogo_promociones.py src/caja/pantalla_inventario.py tests/caja/test_dialogo_promociones.py
git commit -m "feat(promociones): DialogoPromociones + acceso desde inventario (PROMO.10)"
```

---

## PROMO.11: Marca visual del precio promo en la pantalla de venta

**Files:**
- Modify: `src/caja/pantalla_venta.py` (`etiqueta_linea` + uso en `_refrescar_carrito`)
- Test: `tests/caja/test_pantalla_venta_promo.py`

**Interfaces:**
- Consumes: `LineaVenta.promocion_id` (PROMO.1).
- Produces: función de módulo `etiqueta_linea(linea: LineaVenta) -> str` que añade " • promo" si la línea llevó promoción.

- [ ] **Step 1: Write the failing test**

```python
# tests/caja/test_pantalla_venta_promo.py
from decimal import Decimal

from core.entidades import LineaVenta
from caja.pantalla_venta import etiqueta_linea


def _linea(promocion_id):
    return LineaVenta(producto_id=1, descripcion="Lomo", cantidad_o_peso=Decimal("2"),
                      precio_unit=Decimal("15000"), impuesto=Decimal("0"),
                      subtotal=Decimal("30000"), promocion_id=promocion_id)


def test_etiqueta_marca_promo():
    assert "promo" in etiqueta_linea(_linea(3)).lower()


def test_etiqueta_sin_promo_es_solo_descripcion():
    assert etiqueta_linea(_linea(None)) == "Lomo"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/caja/test_pantalla_venta_promo.py -q`
Expected: FAIL (`ImportError: cannot import name 'etiqueta_linea'`).

- [ ] **Step 3: Write minimal implementation**

En `src/caja/pantalla_venta.py`, añade `LineaVenta` al import de `core.entidades` y una función de
módulo (fuera de la clase):

```python
def etiqueta_linea(linea: LineaVenta) -> str:
    """Texto de la descripción en el carrito, con marca si la línea llevó promoción."""
    return f"{linea.descripcion} • promo" if linea.promocion_id else linea.descripcion
```

En `_refrescar_carrito`, cambia la celda de la columna 0:

```python
            self._carrito.setItem(fila, 0, QTableWidgetItem(etiqueta_linea(linea)))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/caja/test_pantalla_venta_promo.py tests/caja/test_pantalla_venta.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/caja/pantalla_venta.py tests/caja/test_pantalla_venta_promo.py
git commit -m "feat(promociones): marca visual del precio promo en la venta (PROMO.11)"
```

---

## CONTEO.1: Denominaciones + total_conteo (caja/conteo.py)

**Files:**
- Create: `src/caja/conteo.py`
- Test: `tests/caja/test_conteo.py`

**Interfaces:**
- Produces: `DENOMINACIONES: tuple[int, ...]` (COP, mayor a menor, una fila para 1000); `total_conteo(conteo: dict[int, int]) -> Decimal`.

- [ ] **Step 1: Write the failing test**

```python
# tests/caja/test_conteo.py
from decimal import Decimal

import pytest

from caja.conteo import DENOMINACIONES, total_conteo


def test_denominaciones_colombianas_una_fila_1000():
    assert DENOMINACIONES == (100000, 50000, 20000, 10000, 5000, 2000, 1000, 500, 200, 100, 50)


def test_total_conteo_suma():
    conteo = {50000: 2, 1000: 3, 100: 5}
    assert total_conteo(conteo) == Decimal("103500")


def test_total_conteo_vacio_es_cero():
    assert total_conteo({}) == Decimal("0")


def test_total_conteo_rechaza_cantidad_negativa():
    with pytest.raises(ValueError):
        total_conteo({1000: -1})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/caja/test_conteo.py -q`
Expected: FAIL (`ModuleNotFoundError: No module named 'caja.conteo'`).

- [ ] **Step 3: Write minimal implementation**

```python
# src/caja/conteo.py
"""Ayudante de conteo de efectivo por denominaciones (COP). Cálculo puro, sin Qt."""
from __future__ import annotations

from decimal import Decimal

# Denominaciones colombianas de mayor a menor; 1000 como una sola fila (moneda+billete).
DENOMINACIONES: tuple[int, ...] = (
    100000, 50000, 20000, 10000, 5000, 2000, 1000, 500, 200, 100, 50)


def total_conteo(conteo: dict[int, int]) -> Decimal:
    """Σ denominación × cantidad. Ignora ceros; rechaza cantidades negativas."""
    total = Decimal("0")
    for denominacion, cantidad in conteo.items():
        if cantidad < 0:
            raise ValueError("la cantidad de una denominación no puede ser negativa")
        total += Decimal(denominacion) * cantidad
    return total
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/caja/test_conteo.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add src/caja/conteo.py tests/caja/test_conteo.py
git commit -m "feat(conteo): denominaciones COP + total_conteo (CONTEO.1)"
```

---

## CONTEO.2: DialogoConteoEfectivo (caja/dialogos)

**Files:**
- Create: `src/caja/dialogos/dialogo_conteo.py`
- Test: `tests/caja/test_dialogo_conteo.py`

**Interfaces:**
- Consumes: `DENOMINACIONES`, `total_conteo` (CONTEO.1).
- Produces: `DialogoConteoEfectivo(parent=None)` con `total() -> Decimal` (suma en vivo del conteo tecleado).

- [ ] **Step 1: Write the failing test**

```python
# tests/caja/test_dialogo_conteo.py
import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from decimal import Decimal  # noqa: E402

from PySide6.QtWidgets import QApplication  # noqa: E402

from caja.dialogos.dialogo_conteo import DialogoConteoEfectivo  # noqa: E402


def test_total_refleja_lo_tecleado():
    _app = QApplication.instance() or QApplication([])
    d = DialogoConteoEfectivo()
    d._spins[50000].setValue(2)
    d._spins[1000].setValue(3)
    assert d.total() == Decimal("103000")


def test_total_inicial_es_cero():
    _app = QApplication.instance() or QApplication([])
    d = DialogoConteoEfectivo()
    assert d.total() == Decimal("0")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/caja/test_dialogo_conteo.py -q`
Expected: FAIL (`ModuleNotFoundError: No module named 'caja.dialogos.dialogo_conteo'`).

- [ ] **Step 3: Write minimal implementation**

```python
# src/caja/dialogos/dialogo_conteo.py
"""Diálogo opcional para contar el efectivo por denominaciones y producir el total."""
from __future__ import annotations

from decimal import Decimal

from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QDialogButtonBox, QDialog, QFormLayout, QLabel, QSpinBox, QVBoxLayout,
)

from caja.conteo import DENOMINACIONES, total_conteo
from caja.formato import formato_moneda


class DialogoConteoEfectivo(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Contar efectivo")
        self._spins: dict[int, QSpinBox] = {}

        form = QFormLayout()
        for denominacion in DENOMINACIONES:
            spin = QSpinBox(); spin.setMaximum(100000)
            spin.valueChanged.connect(self._actualizar_total)
            self._spins[denominacion] = spin
            form.addRow(formato_moneda(Decimal(denominacion)), spin)

        self._lbl_total = QLabel(formato_moneda(Decimal("0")))
        self._lbl_total.setObjectName("kpi-valor")

        botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botones.button(QDialogButtonBox.Ok).setObjectName("primario")
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(QLabel("Total contado"))
        layout.addWidget(self._lbl_total)
        layout.addWidget(botones)

    def total(self) -> Decimal:
        return total_conteo({den: spin.value() for den, spin in self._spins.items()})

    @Slot()
    def _actualizar_total(self) -> None:
        self._lbl_total.setText(formato_moneda(self.total()))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/caja/test_dialogo_conteo.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add src/caja/dialogos/dialogo_conteo.py tests/caja/test_dialogo_conteo.py
git commit -m "feat(conteo): DialogoConteoEfectivo por denominaciones (CONTEO.2)"
```

---

## CONTEO.3: Botón "Contar efectivo" en la pantalla de cierre

**Files:**
- Modify: `src/caja/pantalla_cierre.py` (`__init__`, `_montar_arqueo`, slot `_abrir_conteo`)
- Test: `tests/caja/test_pantalla_cierre_conteo.py`

**Interfaces:**
- Consumes: `DialogoConteoEfectivo` (CONTEO.2).
- Produces: botón "Contar efectivo" que, al aceptar el diálogo, rellena `self._monto_contado`. El cierre sigue funcionando sin usarlo (no obligatorio).

- [ ] **Step 1: Write the failing test**

```python
# tests/caja/test_pantalla_cierre_conteo.py
import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from decimal import Decimal  # noqa: E402

from PySide6.QtWidgets import QApplication, QDialog  # noqa: E402

from caja.contexto import ContextoApp  # noqa: E402
from caja.pantalla_cierre import PantallaCierre  # noqa: E402
import caja.pantalla_cierre as mod  # noqa: E402


class _FakeDialogo:
    def __init__(self, *a, **k):
        pass

    def exec(self):
        return QDialog.Accepted

    def total(self):
        return Decimal("123000")


def test_boton_conteo_rellena_monto_contado(monkeypatch):
    _app = QApplication.instance() or QApplication([])
    ctx = ContextoApp.crear(":memory:")
    win = PantallaCierre(ctx)
    win.al_mostrar()
    win._monto_inicial.setValue(0)
    win._abrir()               # abre caja → vista de arqueo con el botón
    win.al_mostrar()
    monkeypatch.setattr(mod, "DialogoConteoEfectivo", _FakeDialogo)
    win._abrir_conteo()
    assert win._monto_contado.value() == 123000
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/caja/test_pantalla_cierre_conteo.py -q`
Expected: FAIL (`AttributeError: 'PantallaCierre' object has no attribute '_abrir_conteo'`).

- [ ] **Step 3: Write minimal implementation**

En `src/caja/pantalla_cierre.py`:

1) Import: `from caja.dialogos.dialogo_conteo import DialogoConteoEfectivo`.

2) En `__init__`, tras crear `self._boton_cerrar`:

```python
        self._boton_conteo = QPushButton("Contar efectivo")
        self._boton_conteo.clicked.connect(self._abrir_conteo)
```

3) En `_montar_arqueo`, añade el botón a la fila del campo (tras `fila.addWidget(self._monto_contado)`):

```python
        fila.addWidget(self._boton_conteo)
```

4) Añade el slot:

```python
    @Slot()
    def _abrir_conteo(self) -> None:
        dlg = DialogoConteoEfectivo(self)
        if dlg.exec() == DialogoConteoEfectivo.Accepted:
            self._monto_contado.setValue(float(dlg.total()))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/caja/test_pantalla_cierre_conteo.py tests/caja/test_pantalla_cierre.py -q`
Expected: PASS (el flujo de cierre existente sigue pasando; el conteo es opcional).

- [ ] **Step 5: Commit**

```bash
git add src/caja/pantalla_cierre.py tests/caja/test_pantalla_cierre_conteo.py
git commit -m "feat(conteo): botón Contar efectivo en el cierre (CONTEO.3)"
```

---

## Cierre del epic

- [ ] **Suite completa verde**

Run: `python -m pytest -q`
Expected: PASS (269 previos + los nuevos).

- [ ] **Actualizar README-pos.md** (tabla "Estado actual"): añadir filas `PROMO` y `CONTEO` como implementados, con enlaces a esta spec y plan, y actualizar el conteo de tests. Commit:

```bash
git add docs/README-pos.md
git commit -m "docs: README marca PROMO y CONTEO como implementados"
```

---

## Self-Review (autor del plan)

**Cobertura de la spec:**
- Promociones: entidad+validaciones (PROMO.1), reglas vigencia/precio/consumo (PROMO.2), puerto+servicio con "una activa por producto" (PROMO.3), migración 006 (PROMO.4), adaptador SQLite (PROMO.5), integración en venta con acumulación + IVA + GS1-importe (PROMO.6), consumo de unidades (PROMO.7), persistencia `promocion_id` (PROMO.8), permiso ambos roles (PROMO.9), UI de gestión desde inventario (PROMO.10), marca visual (PROMO.11). ✔
- Casos límite de la spec: acumulación promo+descuento y recálculo de IVA (PROMO.6), unidades agotándose por `cantidad_o_peso` (PROMO.2/PROMO.7), GS1 con precio embebido ignora promo (PROMO.6), redondeo a peso entero (subtotales en PROMO.6). ✔
- Conteo: denominaciones+total puro (CONTEO.1), diálogo (CONTEO.2), botón opcional que rellena `monto_contado` sin bloquear el cierre (CONTEO.3). ✔
- Fuera de alcance respetado: sin varias promos por producto (servicio lo impide), sin persistir desglose de conteo, sin restaurar unidades en devolución, conteo en UI.

**Placeholders:** ninguno; cada paso trae código y comando reales.

**Consistencia de tipos:** `ServicioVenta(productos, impuestos, promociones=None)`, `agregar(..., ahora=None)`, `ServicioRegistroVenta(ventas, inventario, promociones=None)`, `RepositorioPromociones` (`guardar/actualizar/por_id/activa_por_producto/listar`), `precio_con_promo(precio_base, promo)`, `promo_vigente(promo, ahora)`, `consumir_unidades(promo, cantidad)`, `total_conteo(conteo)` usados de forma idéntica en todas las tasks y en el wiring de `ContextoApp`.
