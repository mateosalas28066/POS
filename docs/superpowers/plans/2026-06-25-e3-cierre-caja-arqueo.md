# E3 Cierre de caja / arqueo + descuento de inventario — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cerrar el ciclo de caja sobre el dominio estable de E1/E2/E4: entidad `CajaSesion` y valor `Arqueo` en `core`; un `ServicioCaja` puro (apertura, arqueo de efectivo contado vs. esperado, cierre); puerto `RepositorioCajaSesiones` + adaptador SQLite (la tabla `caja_sesiones` ya existe en `002_ventas.sql`); el método `RepositorioVentas.totales_por_medio` para el cuadre por medio de pago; y el **descuento de inventario al registrar una venta** (diferido de E1) vía `ServicioRegistroVenta`. Cierra el flujo crítico #4 de `testing-pos` ("cierre de caja con arqueo").

**Architecture:** Hexagonal estricta, igual que E1. La lógica de caja vive en `src/core/` (entidades frozen, regla `calcular_arqueo` en `calculos.py`, `ServicioCaja` que solo conoce los puertos `RepositorioCajaSesiones`/`RepositorioVentas`). La persistencia de la sesión de caja es un adaptador SQLite que se aloja en `src/ventas/` (persistencia no-UI del dominio de caja/venta), para que `src/caja/` siga siendo **solo** UI Qt. El descuento de inventario es una regla de dominio: `salidas_de_venta(venta)` mapea cada línea a un `MovimientoInventario` de tipo `salida` (puro), y `ServicioRegistroVenta` (solo puertos) orquesta "persistir venta → registrar salidas".

**Tech Stack:** Python 3.11+, stdlib `sqlite3` + `decimal` + `dataclasses` + `typing.Protocol`, `pytest`. Sin Qt en este epic (no hay UI nueva obligatoria; la pantalla de cierre se difiere a E7/refinamiento).

## Decisiones de diseño (revisar antes de ejecutar)

1. **`pago.monto` = monto *aplicado* que salda la venta, no lo *recibido*.** Para que el arqueo cuadre, el efectivo esperado en cajón es `monto_inicial + Σ(pagos en efectivo)`. Si se guardara el dinero recibido (p. ej. 20 000 por una venta de 13 000), el esperado sobrecontaría el vuelto (7 000) y daría un faltante falso. Por tanto: la caja registra el monto que salda la venta; `calcular_vuelto` (E1.2) sigue siendo un ayudante de UI para mostrar el cambio, **no se persiste**. Nota de reconciliación: el test `tests/ventas/test_flujo_venta_simple.py` (E1) guarda un `Pago` de 20 000; esas ventas tienen `caja_sesion_id = NULL`, así que **no entran en ningún arqueo** y no hay bug vivo. Las ventas de E3 registran el monto aplicado (`Σ pagos == venta.total`).

2. **El arqueo (`diferencia`) es solo del efectivo del cajón.** Tarjeta/transferencia no entran al cajón físico. `RepositorioVentas.totales_por_medio(caja_sesion_id)` devuelve el desglose **por todos los medios** (cuadre completo que pide `testing-pos` #4: "efectivo y medios de pago"), y `ServicioCaja` toma solo el efectivo para calcular `esperado` y `diferencia`. El desglose completo queda disponible para el recibo de cierre y los informes (E7).

3. **`efectivo_medio_pago_id` es inyectable**, con default `1` (fila semilla `'Efectivo'` de `002_ventas.sql`). Evita hardcodear el id dentro del cálculo y deja cambiar la convención sin tocar `core`.

4. **Sumas monetarias en Python, no en SQL.** El dinero viaja como `DECIMAL` declarado (adapter/converter en `inventario/db.py`); `SUM()` de SQLite sobre columnas-texto devolvería `float` y rompería la exactitud `Decimal`. `totales_por_medio` selecciona filas y suma con `Decimal` en Python — mismo patrón que `RepositorioInventarioSQLite.stock_de` (E2).

5. **El adaptador `RepositorioCajaSesionesSQLite` vive en `src/ventas/repositorio_sqlite.py`.** La tabla `caja_sesiones` está en `002_ventas.sql` y `src/ventas/` ya es el módulo de persistencia no-UI del dominio venta/caja (clientes, medios de pago, ventas). Mantener `src/caja/` solo para Qt. **Recomendado: pasar el subagente `arquitecto-pos` antes de mergear** para bendecir esta frontera (el spec aún no lista `src/ventas/`; es deuda de documentación heredada de E1).

6. **`ServicioRegistroVenta` orquesta venta + descuento de inventario** y depende **solo de puertos** (`RepositorioVentas`, `RepositorioInventario`), por eso vive en `core`. No bloquea la venta por falta de stock (en carnicería/fruver el stock puede ir negativo transitoriamente; YAGNI no añadir validación de existencias). Atomicidad: ambos repos comparten la `conn` pero hacen `commit()` propio; una transacción única venta+salidas es un refinamiento futuro aceptable para una caja offline (se anota en "Diferido a propósito").

7. **Devolución / anulación (flujo crítico #3) NO entra en este E3.** El plan E1 anotó "devolución entra con E3", pero el alcance pedido para este E3 es arqueo + descuento de inventario. Se difiere a un **E3.b** (la reversa de inventario reutilizará `ServicioRegistroVenta` y `MovimientoInventario` tipo `entrada`). Ver "Diferido a propósito".

## Global Constraints

- **Python ≥ 3.11** — sintaxis `X | None`, `tuple[...]`, `dict[int, Decimal]` nativas.
- **`src/core/` NO importa Qt ni SQLite ni pyserial.** Prohibido `import sqlite3` / `from PySide6` / `import serial` bajo `src/core/`. Los servicios reciben repositorios por inyección (objetos que cumplen los `Protocol`).
- **SQL solo en adaptadores de repositorio** (`src/inventario/`, `src/ventas/`). Nada de SQL en `core`/`caja`.
- **Dinero y cantidades con `decimal.Decimal`**, nunca `float`. Columnas SQLite declaradas `DECIMAL`. **Las sumas se hacen en Python**, nunca con `SUM()` de SQL (ver decisión 4).
- **Redondeo a peso colombiano entero** con `ROUND_HALF_UP` en cifras monetarias de salida (heredado; el arqueo opera sobre cifras ya redondeadas, no re-redondea).
- **Nombres de dominio en español** (`CajaSesion`, `Arqueo`, `ServicioCaja`, `ServicioRegistroVenta`, `abrir`, `cerrar`, `arqueo`).
- **Entidades/valores del dominio = `@dataclass(frozen=True)`**; puertos = `typing.Protocol`. Mutar = `dataclasses.replace`.
- **Tests:** `pytest`, `pythonpath = src` (ya en `pytest.ini`); archivos `test_*.py`, estructura espejo por módulo. Imports tipo `from core.servicio_caja import ServicioCaja`.
- **Ponytail/YAGNI:** mínimo código; no modelar turnos, retiros/ingresos de efectivo (payouts), ni multi-cajón aún. No tocar `outbox` ni DIAN.
- **Migraciones versionadas** en `scripts/migraciones/NNN_*.sql`; integridad referencial activa (`PRAGMA foreign_keys = ON`). **No hay migración nueva en E3**: `caja_sesiones` ya existe en `002_ventas.sql`.

---

## File Structure

**Core (dominio puro)**
- `src/core/entidades.py` — *extender* con `ESTADOS_CAJA`, `CajaSesion`, `Arqueo`.
- `src/core/calculos.py` — *extender* con `calcular_arqueo` (importa `Arqueo` de `core.entidades`).
- `src/core/puertos.py` — *extender* `RepositorioVentas` (`totales_por_medio`) y *añadir* `RepositorioCajaSesiones`.
- `src/core/servicio_caja.py` — **nuevo**: `ServicioCaja` + excepciones `CajaYaAbierta`, `CajaNoEncontrada`, `CajaNoAbierta`.
- `src/core/servicio_venta.py` — *extender* con `salidas_de_venta` y `ServicioRegistroVenta`.

**Persistencia (adaptadores SQLite)**
- `src/ventas/repositorio_sqlite.py` — *extender*: `RepositorioCajaSesionesSQLite` + `RepositorioVentasSQLite.totales_por_medio`.

**Tests**
- `tests/core/test_entidades_caja.py` — **nuevo**: invariantes de `CajaSesion`/`Arqueo`.
- `tests/core/test_calculos_arqueo.py` — **nuevo**: `calcular_arqueo`.
- `tests/core/test_servicio_caja.py` — **nuevo**: `ServicioCaja` con fakes.
- `tests/core/test_registro_venta.py` — **nuevo**: `salidas_de_venta` + `ServicioRegistroVenta` con fakes.
- `tests/ventas/test_repositorio_caja.py` — **nuevo**: adaptador de sesiones + `totales_por_medio`.
- `tests/ventas/test_flujo_cierre_caja.py` — **nuevo**: flujo crítico #4 (integración).

---

### Task E3.1: Entidad `CajaSesion` + valor `Arqueo` (invariantes)

**Files:**
- Modify: `src/core/entidades.py`
- Test: `tests/core/test_entidades_caja.py`

**Interfaces:**
- Consumes: `dataclass`, `datetime`, `Decimal`, `CERO` (ya en el módulo).
- Produces:
  - Constante `ESTADOS_CAJA = ("abierta", "cerrada")`.
  - `CajaSesion(apertura_fecha: datetime, monto_inicial: Decimal, usuario_id: int | None = None, cierre_fecha: datetime | None = None, monto_contado: Decimal | None = None, estado: str = "abierta", id: int | None = None)` — `estado ∈ ESTADOS_CAJA`; `monto_inicial ≥ 0`; `monto_contado ≥ 0` si no es `None`.
  - `Arqueo(monto_inicial: Decimal, efectivo_ventas: Decimal, esperado: Decimal, contado: Decimal, diferencia: Decimal)` — valor de solo lectura (sin invariantes; lo construye `calcular_arqueo`).

- [ ] **Step 1: Write the failing test**

```python
# tests/core/test_entidades_caja.py
from datetime import datetime
from decimal import Decimal

import pytest

from core.entidades import Arqueo, CajaSesion


def test_caja_sesion_minima_abierta():
    s = CajaSesion(apertura_fecha=datetime(2026, 6, 25, 9, 0), monto_inicial=Decimal("100000"))
    assert s.estado == "abierta"
    assert s.cierre_fecha is None
    assert s.monto_contado is None
    assert s.id is None


def test_caja_sesion_monto_inicial_negativo_falla():
    with pytest.raises(ValueError):
        CajaSesion(apertura_fecha=datetime(2026, 6, 25, 9, 0), monto_inicial=Decimal("-1"))


def test_caja_sesion_estado_invalido_falla():
    with pytest.raises(ValueError):
        CajaSesion(apertura_fecha=datetime(2026, 6, 25, 9, 0),
                   monto_inicial=Decimal("0"), estado="pausada")


def test_caja_sesion_monto_contado_negativo_falla():
    with pytest.raises(ValueError):
        CajaSesion(apertura_fecha=datetime(2026, 6, 25, 9, 0),
                   monto_inicial=Decimal("0"), monto_contado=Decimal("-5"))


def test_arqueo_es_valor_de_lectura():
    a = Arqueo(monto_inicial=Decimal("100000"), efectivo_ventas=Decimal("13000"),
               esperado=Decimal("113000"), contado=Decimal("112000"),
               diferencia=Decimal("-1000"))
    assert a.diferencia == Decimal("-1000")
    assert a.esperado == Decimal("113000")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_entidades_caja.py -v`
Expected: FAIL con `ImportError: cannot import name 'CajaSesion' from 'core.entidades'`.

- [ ] **Step 3: Append the entities**

Añadir al final de `src/core/entidades.py` (las importaciones `dataclass`, `datetime`, `Decimal`, y `CERO` ya existen en el módulo):

```python
ESTADOS_CAJA = ("abierta", "cerrada")


@dataclass(frozen=True)
class CajaSesion:
    apertura_fecha: datetime
    monto_inicial: Decimal
    usuario_id: int | None = None
    cierre_fecha: datetime | None = None
    monto_contado: Decimal | None = None
    estado: str = "abierta"
    id: int | None = None

    def __post_init__(self) -> None:
        if self.estado not in ESTADOS_CAJA:
            raise ValueError(f"estado de caja inválido: {self.estado!r}")
        if self.monto_inicial < CERO:
            raise ValueError("monto_inicial no puede ser negativo")
        if self.monto_contado is not None and self.monto_contado < CERO:
            raise ValueError("monto_contado no puede ser negativo")


@dataclass(frozen=True)
class Arqueo:
    monto_inicial: Decimal
    efectivo_ventas: Decimal
    esperado: Decimal           # monto_inicial + efectivo_ventas
    contado: Decimal
    diferencia: Decimal         # contado - esperado: > 0 sobrante, < 0 faltante
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_entidades_caja.py -v`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add src/core/entidades.py tests/core/test_entidades_caja.py
git commit -m "feat(core): entidad CajaSesion y valor Arqueo (invariantes)"
```

---

### Task E3.2: Regla de cálculo de arqueo

**Files:**
- Modify: `src/core/calculos.py`
- Test: `tests/core/test_calculos_arqueo.py`

**Interfaces:**
- Consumes: `Decimal`, `CERO` (ya en el módulo); `Arqueo` (E3.1).
- Produces:
  - `calcular_arqueo(monto_inicial: Decimal, efectivo_ventas: Decimal, monto_contado: Decimal) -> Arqueo` — `esperado = monto_inicial + efectivo_ventas`; `diferencia = monto_contado − esperado`. Rechaza montos negativos con `ValueError`.

- [ ] **Step 1: Write the failing test**

```python
# tests/core/test_calculos_arqueo.py
from decimal import Decimal

import pytest

from core.calculos import calcular_arqueo


def test_arqueo_cuadrado_diferencia_cero():
    a = calcular_arqueo(Decimal("100000"), Decimal("13000"), Decimal("113000"))
    assert a.esperado == Decimal("113000")
    assert a.diferencia == Decimal("0")


def test_arqueo_faltante_es_negativo():
    a = calcular_arqueo(Decimal("100000"), Decimal("13000"), Decimal("112000"))
    assert a.diferencia == Decimal("-1000")


def test_arqueo_sobrante_es_positivo():
    a = calcular_arqueo(Decimal("100000"), Decimal("13000"), Decimal("114000"))
    assert a.diferencia == Decimal("1000")


def test_arqueo_sin_ventas_solo_base():
    a = calcular_arqueo(Decimal("50000"), Decimal("0"), Decimal("50000"))
    assert a.esperado == Decimal("50000")
    assert a.diferencia == Decimal("0")
    assert a.efectivo_ventas == Decimal("0")


def test_arqueo_monto_negativo_falla():
    with pytest.raises(ValueError):
        calcular_arqueo(Decimal("-1"), Decimal("0"), Decimal("0"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_calculos_arqueo.py -v`
Expected: FAIL con `ImportError: cannot import name 'calcular_arqueo' from 'core.calculos'`.

- [ ] **Step 3: Append the rule**

En `src/core/calculos.py`, añadir el import de `Arqueo` arriba (junto a los `from __future__`/`from decimal`):

```python
from core.entidades import Arqueo
```

Y añadir al final del archivo:

```python
def calcular_arqueo(monto_inicial: Decimal, efectivo_ventas: Decimal,
                    monto_contado: Decimal) -> Arqueo:
    """Cuadre de caja: efectivo contado vs. esperado (base + ventas en efectivo)."""
    if monto_inicial < CERO or efectivo_ventas < CERO or monto_contado < CERO:
        raise ValueError("los montos del arqueo deben ser no negativos")
    esperado = monto_inicial + efectivo_ventas
    return Arqueo(
        monto_inicial=monto_inicial,
        efectivo_ventas=efectivo_ventas,
        esperado=esperado,
        contado=monto_contado,
        diferencia=monto_contado - esperado,
    )
```

> Nota: `core.calculos` ya solo dependía de `decimal`; importar `core.entidades` no crea ciclo (`entidades` no importa `calculos`).

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_calculos_arqueo.py -v`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add src/core/calculos.py tests/core/test_calculos_arqueo.py
git commit -m "feat(core): calcular_arqueo (efectivo contado vs esperado)"
```

---

### Task E3.3: Puertos de caja + `ServicioCaja`

**Files:**
- Modify: `src/core/puertos.py`
- Create: `src/core/servicio_caja.py`
- Test: `tests/core/test_servicio_caja.py`

**Interfaces:**
- Consumes: `CajaSesion`, `Arqueo` (E3.1); `calcular_arqueo` (E3.2); `replace` (`dataclasses`).
- Produces (puertos en `core.puertos`):
  - `RepositorioVentas.totales_por_medio(caja_sesion_id: int) -> dict[int, Decimal]` (añadido al `Protocol` existente).
  - `RepositorioCajaSesiones`: `abrir(sesion: CajaSesion) -> CajaSesion`, `cerrar(sesion: CajaSesion) -> CajaSesion`, `por_id(id: int) -> CajaSesion | None`, `abierta() -> CajaSesion | None`.
- Produces (servicio en `core.servicio_caja`):
  - `CajaYaAbierta(RuntimeError)`, `CajaNoEncontrada(ValueError)`, `CajaNoAbierta(ValueError)`.
  - `ServicioCaja(sesiones: RepositorioCajaSesiones, ventas: RepositorioVentas, efectivo_medio_pago_id: int = 1)`:
    - `abrir(*, fecha: datetime, monto_inicial: Decimal, usuario_id: int | None = None) -> CajaSesion` — rechaza si ya hay sesión abierta.
    - `arqueo(sesion_id: int, monto_contado: Decimal) -> Arqueo`.
    - `cerrar(*, sesion_id: int, fecha: datetime, monto_contado: Decimal) -> tuple[CajaSesion, Arqueo]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/core/test_servicio_caja.py
from dataclasses import replace
from datetime import datetime
from decimal import Decimal

import pytest

from core.entidades import CajaSesion
from core.servicio_caja import (
    CajaNoAbierta, CajaNoEncontrada, CajaYaAbierta, ServicioCaja,
)


class _FakeSesiones:
    def __init__(self) -> None:
        self._por_id: dict[int, CajaSesion] = {}
        self._siguiente = 1

    def abrir(self, sesion: CajaSesion) -> CajaSesion:
        guardada = replace(sesion, id=self._siguiente)
        self._por_id[self._siguiente] = guardada
        self._siguiente += 1
        return guardada

    def cerrar(self, sesion: CajaSesion) -> CajaSesion:
        self._por_id[sesion.id] = sesion
        return sesion

    def por_id(self, id: int):
        return self._por_id.get(id)

    def abierta(self):
        return next((s for s in self._por_id.values() if s.estado == "abierta"), None)


class _FakeVentas:
    def __init__(self, totales: dict[int, Decimal] | None = None) -> None:
        self._totales = totales or {}

    def totales_por_medio(self, caja_sesion_id: int) -> dict[int, Decimal]:
        return dict(self._totales)


def _servicio(totales=None) -> ServicioCaja:
    return ServicioCaja(_FakeSesiones(), _FakeVentas(totales))


def test_abrir_devuelve_sesion_con_id():
    s = _servicio().abrir(fecha=datetime(2026, 6, 25, 9, 0), monto_inicial=Decimal("100000"))
    assert s.id is not None
    assert s.estado == "abierta"
    assert s.monto_inicial == Decimal("100000")


def test_abrir_dos_veces_falla():
    serv = _servicio()
    serv.abrir(fecha=datetime(2026, 6, 25, 9, 0), monto_inicial=Decimal("100000"))
    with pytest.raises(CajaYaAbierta):
        serv.abrir(fecha=datetime(2026, 6, 25, 9, 5), monto_inicial=Decimal("0"))


def test_arqueo_usa_solo_efectivo():
    serv = _servicio(totales={1: Decimal("13000"), 2: Decimal("9000")})
    s = serv.abrir(fecha=datetime(2026, 6, 25, 9, 0), monto_inicial=Decimal("100000"))
    a = serv.arqueo(s.id, Decimal("112000"))
    assert a.efectivo_ventas == Decimal("13000")   # ignora tarjeta (medio 2)
    assert a.esperado == Decimal("113000")
    assert a.diferencia == Decimal("-1000")


def test_arqueo_sin_ventas_es_la_base():
    serv = _servicio()
    s = serv.abrir(fecha=datetime(2026, 6, 25, 9, 0), monto_inicial=Decimal("50000"))
    a = serv.arqueo(s.id, Decimal("50000"))
    assert a.efectivo_ventas == Decimal("0")
    assert a.diferencia == Decimal("0")


def test_arqueo_sesion_inexistente_falla():
    with pytest.raises(CajaNoEncontrada):
        _servicio().arqueo(999, Decimal("0"))


def test_cerrar_marca_cerrada_y_devuelve_arqueo():
    serv = _servicio(totales={1: Decimal("13000")})
    s = serv.abrir(fecha=datetime(2026, 6, 25, 9, 0), monto_inicial=Decimal("100000"))
    cerrada, arqueo = serv.cerrar(sesion_id=s.id, fecha=datetime(2026, 6, 25, 20, 0),
                                  monto_contado=Decimal("113000"))
    assert cerrada.estado == "cerrada"
    assert cerrada.cierre_fecha == datetime(2026, 6, 25, 20, 0)
    assert cerrada.monto_contado == Decimal("113000")
    assert arqueo.diferencia == Decimal("0")


def test_cerrar_sesion_ya_cerrada_falla():
    serv = _servicio()
    s = serv.abrir(fecha=datetime(2026, 6, 25, 9, 0), monto_inicial=Decimal("0"))
    serv.cerrar(sesion_id=s.id, fecha=datetime(2026, 6, 25, 20, 0), monto_contado=Decimal("0"))
    with pytest.raises(CajaNoAbierta):
        serv.cerrar(sesion_id=s.id, fecha=datetime(2026, 6, 25, 21, 0), monto_contado=Decimal("0"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_servicio_caja.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'core.servicio_caja'`.

- [ ] **Step 3a: Extend the ports**

En `src/core/puertos.py`, añadir `CajaSesion` al import de `core.entidades`:

```python
from core.entidades import (
    CajaSesion, Categoria, Cliente, Impuesto, MedioPago, MovimientoInventario, Pago, Producto, Venta,
)
```

Reemplazar el `RepositorioVentas` existente por (añade `totales_por_medio`):

```python
class RepositorioVentas(Protocol):
    def guardar(self, venta: Venta, pagos: list[Pago]) -> Venta: ...
    def por_id(self, id: int) -> Venta | None: ...
    def pagos_de(self, venta_id: int) -> list[Pago]: ...
    def totales_por_medio(self, caja_sesion_id: int) -> dict[int, Decimal]: ...
```

Y añadir al final del archivo:

```python
class RepositorioCajaSesiones(Protocol):
    def abrir(self, sesion: CajaSesion) -> CajaSesion: ...
    def cerrar(self, sesion: CajaSesion) -> CajaSesion: ...
    def por_id(self, id: int) -> CajaSesion | None: ...
    def abierta(self) -> CajaSesion | None: ...
```

- [ ] **Step 3b: Write the service**

```python
# src/core/servicio_caja.py
"""Servicio de apertura/cierre y arqueo de caja. Python puro: solo conoce puertos."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from decimal import Decimal

from core.calculos import calcular_arqueo
from core.entidades import Arqueo, CajaSesion
from core.puertos import RepositorioCajaSesiones, RepositorioVentas

CERO = Decimal("0")
EFECTIVO_POR_DEFECTO = 1  # id semilla de 'Efectivo' en 002_ventas.sql


class CajaYaAbierta(RuntimeError):
    pass


class CajaNoEncontrada(ValueError):
    pass


class CajaNoAbierta(ValueError):
    pass


class ServicioCaja:
    """Abre, arquea y cierra la sesión de caja sobre los puertos de persistencia."""

    def __init__(self, sesiones: RepositorioCajaSesiones, ventas: RepositorioVentas,
                 efectivo_medio_pago_id: int = EFECTIVO_POR_DEFECTO) -> None:
        self._sesiones = sesiones
        self._ventas = ventas
        self._efectivo_id = efectivo_medio_pago_id

    def abrir(self, *, fecha: datetime, monto_inicial: Decimal,
              usuario_id: int | None = None) -> CajaSesion:
        if self._sesiones.abierta() is not None:
            raise CajaYaAbierta("ya existe una sesión de caja abierta")
        return self._sesiones.abrir(CajaSesion(
            apertura_fecha=fecha, monto_inicial=monto_inicial, usuario_id=usuario_id))

    def _arqueo(self, sesion: CajaSesion, monto_contado: Decimal) -> Arqueo:
        totales = self._ventas.totales_por_medio(sesion.id)
        return calcular_arqueo(sesion.monto_inicial, totales.get(self._efectivo_id, CERO),
                               monto_contado)

    def arqueo(self, sesion_id: int, monto_contado: Decimal) -> Arqueo:
        sesion = self._sesiones.por_id(sesion_id)
        if sesion is None:
            raise CajaNoEncontrada(f"sesión de caja inexistente: {sesion_id}")
        return self._arqueo(sesion, monto_contado)

    def cerrar(self, *, sesion_id: int, fecha: datetime,
               monto_contado: Decimal) -> tuple[CajaSesion, Arqueo]:
        sesion = self._sesiones.por_id(sesion_id)
        if sesion is None:
            raise CajaNoEncontrada(f"sesión de caja inexistente: {sesion_id}")
        if sesion.estado != "abierta":
            raise CajaNoAbierta(f"la sesión {sesion_id} no está abierta")
        arqueo = self._arqueo(sesion, monto_contado)
        cerrada = self._sesiones.cerrar(replace(
            sesion, cierre_fecha=fecha, monto_contado=monto_contado, estado="cerrada"))
        return cerrada, arqueo
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_servicio_caja.py -v`
Expected: PASS (7 passed).

- [ ] **Step 5: Commit**

```bash
git add src/core/puertos.py src/core/servicio_caja.py tests/core/test_servicio_caja.py
git commit -m "feat(core): puertos de caja y ServicioCaja (apertura, arqueo, cierre)"
```

---

### Task E3.4: Adaptador SQLite de sesiones + `totales_por_medio`

**Files:**
- Modify: `src/ventas/repositorio_sqlite.py`
- Test: `tests/ventas/test_repositorio_caja.py`

**Interfaces:**
- Consumes: `CajaSesion` (E3.1); `sqlite3`, `replace`, `datetime` (ya en el módulo); fixture `conn` de `tests/ventas/conftest.py` (E1.4); `RepositorioCategoriasSQLite`, `RepositorioImpuestosSQLite`, `RepositorioProductosSQLite` (E2.3); `RepositorioVentasSQLite` (E1.5).
- Produces (en `ventas.repositorio_sqlite`):
  - `RepositorioCajaSesionesSQLite(conn)` — `abrir`, `cerrar`, `por_id`, `abierta`.
  - `RepositorioVentasSQLite.totales_por_medio(caja_sesion_id) -> dict[int, Decimal]` — suma en Python los `pagos.monto` de las ventas `'pagada'` de la sesión, agrupados por `medio_pago_id`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/ventas/test_repositorio_caja.py
from dataclasses import replace
from datetime import datetime
from decimal import Decimal

from core.entidades import (
    CajaSesion, Categoria, Impuesto, LineaVenta, Pago, Producto, Venta,
)
from inventario.repositorio_sqlite import (
    RepositorioCategoriasSQLite,
    RepositorioImpuestosSQLite,
    RepositorioProductosSQLite,
)
from ventas.repositorio_sqlite import (
    RepositorioCajaSesionesSQLite,
    RepositorioVentasSQLite,
)


def test_caja_sesion_abrir_cerrar_y_abierta(conn):
    repo = RepositorioCajaSesionesSQLite(conn)
    assert repo.abierta() is None

    s = repo.abrir(CajaSesion(apertura_fecha=datetime(2026, 6, 25, 9, 0),
                              monto_inicial=Decimal("100000")))
    assert s.id is not None
    assert repo.abierta().id == s.id

    repo.cerrar(replace(s, cierre_fecha=datetime(2026, 6, 25, 20, 0),
                        monto_contado=Decimal("113000"), estado="cerrada"))
    assert repo.abierta() is None

    leida = repo.por_id(s.id)
    assert leida.estado == "cerrada"
    assert leida.monto_inicial == Decimal("100000")
    assert leida.monto_contado == Decimal("113000")
    assert leida.cierre_fecha == datetime(2026, 6, 25, 20, 0)


def test_por_id_inexistente_es_none(conn):
    assert RepositorioCajaSesionesSQLite(conn).por_id(999) is None


def _venta_en_sesion(conn, sesion_id, pagos, producto_id):
    linea = LineaVenta(producto_id=producto_id, descripcion="Gaseosa",
                       cantidad_o_peso=Decimal("2"), precio_unit=Decimal("3500"),
                       impuesto=Decimal("1118"), subtotal=Decimal("7000"))
    venta = Venta(fecha=datetime(2026, 6, 25, 10, 0), lineas=(linea,),
                  total=Decimal("7000"), total_impuestos=Decimal("1118"),
                  caja_sesion_id=sesion_id)
    RepositorioVentasSQLite(conn).guardar(venta, pagos)


def test_totales_por_medio_suma_pagos_de_la_sesion(conn):
    cat = RepositorioCategoriasSQLite(conn).guardar(Categoria(nombre="Bebidas"))
    imp = RepositorioImpuestosSQLite(conn).guardar(Impuesto(nombre="IVA", tarifa=Decimal("0.19")))
    prod = RepositorioProductosSQLite(conn).guardar(
        Producto(codigo_barras="B", nombre="Gaseosa", precio=Decimal("3500"),
                 categoria_id=cat.id, impuesto_id=imp.id))
    sesion = RepositorioCajaSesionesSQLite(conn).abrir(
        CajaSesion(apertura_fecha=datetime(2026, 6, 25, 9, 0), monto_inicial=Decimal("0")))

    _venta_en_sesion(conn, sesion.id, [Pago(medio_pago_id=1, monto=Decimal("7000"))], prod.id)
    _venta_en_sesion(conn, sesion.id,
                     [Pago(medio_pago_id=1, monto=Decimal("7000")),
                      Pago(medio_pago_id=2, monto=Decimal("3000"))], prod.id)

    totales = RepositorioVentasSQLite(conn).totales_por_medio(sesion.id)
    assert totales == {1: Decimal("14000"), 2: Decimal("3000")}


def test_totales_por_medio_sesion_sin_ventas_es_vacio(conn):
    assert RepositorioVentasSQLite(conn).totales_por_medio(999) == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/ventas/test_repositorio_caja.py -v`
Expected: FAIL con `ImportError: cannot import name 'RepositorioCajaSesionesSQLite' from 'ventas.repositorio_sqlite'`.

- [ ] **Step 3a: Add `totales_por_medio` to the sales adapter**

En `src/ventas/repositorio_sqlite.py`, añadir `Decimal` al import de `decimal` arriba del módulo (junto a los imports existentes):

```python
from decimal import Decimal
```

Y añadir el método al final de la clase `RepositorioVentasSQLite` (suma en Python, no con `SUM()` de SQL, para no perder exactitud `Decimal`; mismo patrón que `RepositorioInventarioSQLite.stock_de`):

```python
    def totales_por_medio(self, caja_sesion_id: int) -> dict[int, Decimal]:
        filas = self._conn.execute(
            "SELECT p.medio_pago_id AS medio_pago_id, p.monto AS monto "
            "FROM pagos p JOIN ventas v ON v.id = p.venta_id "
            "WHERE v.caja_sesion_id = ? AND v.estado = 'pagada'",
            (caja_sesion_id,)).fetchall()
        totales: dict[int, Decimal] = {}
        for f in filas:
            totales[f["medio_pago_id"]] = totales.get(f["medio_pago_id"], Decimal("0")) + f["monto"]
        return totales
```

- [ ] **Step 3b: Add the caja-sesiones adapter**

En `src/ventas/repositorio_sqlite.py`, añadir `CajaSesion` al import de `core.entidades`:

```python
from core.entidades import CajaSesion, Cliente, LineaVenta, MedioPago, Pago, Venta
```

Y añadir al final del archivo:

```python
def _fila_a_sesion(f: sqlite3.Row) -> CajaSesion:
    return CajaSesion(
        apertura_fecha=datetime.fromisoformat(f["apertura_fecha"]),
        monto_inicial=f["monto_inicial"],
        usuario_id=f["usuario_id"],
        cierre_fecha=datetime.fromisoformat(f["cierre_fecha"]) if f["cierre_fecha"] else None,
        monto_contado=f["monto_contado"],
        estado=f["estado"],
        id=f["id"],
    )


class RepositorioCajaSesionesSQLite:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def abrir(self, s: CajaSesion) -> CajaSesion:
        cur = self._conn.execute(
            "INSERT INTO caja_sesiones (usuario_id, apertura_fecha, monto_inicial, estado) "
            "VALUES (?, ?, ?, ?)",
            (s.usuario_id, s.apertura_fecha.isoformat(), s.monto_inicial, s.estado))
        self._conn.commit()
        return replace(s, id=cur.lastrowid)

    def cerrar(self, s: CajaSesion) -> CajaSesion:
        self._conn.execute(
            "UPDATE caja_sesiones SET cierre_fecha = ?, monto_contado = ?, estado = ? "
            "WHERE id = ?",
            (s.cierre_fecha.isoformat() if s.cierre_fecha else None,
             s.monto_contado, s.estado, s.id))
        self._conn.commit()
        return s

    def por_id(self, id: int) -> CajaSesion | None:
        f = self._conn.execute("SELECT * FROM caja_sesiones WHERE id = ?", (id,)).fetchone()
        return _fila_a_sesion(f) if f else None

    def abierta(self) -> CajaSesion | None:
        f = self._conn.execute(
            "SELECT * FROM caja_sesiones WHERE estado = 'abierta' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return _fila_a_sesion(f) if f else None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/ventas/test_repositorio_caja.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add src/ventas/repositorio_sqlite.py tests/ventas/test_repositorio_caja.py
git commit -m "feat(ventas): adaptador SQLite de caja_sesiones y totales_por_medio"
```

---

### Task E3.5: Descuento de inventario al registrar la venta

> Diferido de E1: al persistir una venta debe emitirse una `salida` de inventario por cada línea. Regla pura (`salidas_de_venta`) + orquestador `ServicioRegistroVenta` que solo conoce puertos.

**Files:**
- Modify: `src/core/servicio_venta.py`
- Test: `tests/core/test_registro_venta.py`

**Interfaces:**
- Consumes: `Venta`, `LineaVenta`, `Pago`, `MovimientoInventario` (E3.1/E1.1/E2.1); `RepositorioVentas`, `RepositorioInventario` (puertos existentes).
- Produces (en `core.servicio_venta`):
  - `salidas_de_venta(venta: Venta) -> list[MovimientoInventario]` — una `salida` por línea: `producto_id`, `cantidad = cantidad_o_peso`, `fecha = venta.fecha`, `ref = f"venta:{venta.id}"`.
  - `ServicioRegistroVenta(ventas: RepositorioVentas, inventario: RepositorioInventario)`:
    - `registrar(venta: Venta, pagos: list[Pago]) -> Venta` — persiste la venta (`ventas.guardar`) y registra las salidas (`inventario.registrar`) usando la venta ya con `id`.

- [ ] **Step 1: Write the failing test**

```python
# tests/core/test_registro_venta.py
from dataclasses import replace
from datetime import datetime
from decimal import Decimal

from core.entidades import LineaVenta, Pago, Venta
from core.servicio_venta import ServicioRegistroVenta, salidas_de_venta


def _venta(id=None) -> Venta:
    lineas = (
        LineaVenta(producto_id=1, descripcion="Gaseosa", cantidad_o_peso=Decimal("2"),
                   precio_unit=Decimal("3500"), impuesto=Decimal("1118"), subtotal=Decimal("7000")),
        LineaVenta(producto_id=2, descripcion="Manzana", cantidad_o_peso=Decimal("1.5"),
                   precio_unit=Decimal("4000"), impuesto=Decimal("0"), subtotal=Decimal("6000")),
    )
    return Venta(fecha=datetime(2026, 6, 25, 10, 0), lineas=lineas,
                 total=Decimal("13000"), total_impuestos=Decimal("1118"), id=id)


class _FakeVentas:
    def __init__(self) -> None:
        self.guardada = None

    def guardar(self, venta: Venta, pagos: list[Pago]) -> Venta:
        self.guardada = replace(venta, id=77)
        self.pagos = pagos
        return self.guardada


class _FakeInventario:
    def __init__(self) -> None:
        self.movimientos = []

    def registrar(self, m):
        self.movimientos.append(m)
        return m


def test_salidas_de_venta_una_por_linea():
    salidas = salidas_de_venta(_venta(id=77))
    assert len(salidas) == 2
    assert all(m.tipo == "salida" for m in salidas)
    assert salidas[0].producto_id == 1
    assert salidas[0].cantidad == Decimal("2")
    assert salidas[1].cantidad == Decimal("1.5")
    assert salidas[0].ref == "venta:77"


def test_registrar_persiste_y_descuenta_inventario():
    ventas, inventario = _FakeVentas(), _FakeInventario()
    servicio = ServicioRegistroVenta(ventas, inventario)

    guardada = servicio.registrar(_venta(), [Pago(medio_pago_id=1, monto=Decimal("13000"))])

    assert guardada.id == 77
    assert [m.producto_id for m in inventario.movimientos] == [1, 2]
    assert [m.cantidad for m in inventario.movimientos] == [Decimal("2"), Decimal("1.5")]
    assert all(m.ref == "venta:77" for m in inventario.movimientos)  # usa la venta ya con id
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_registro_venta.py -v`
Expected: FAIL con `ImportError: cannot import name 'ServicioRegistroVenta' from 'core.servicio_venta'`.

- [ ] **Step 3: Extend the service module**

En `src/core/servicio_venta.py`, ampliar los imports de `core.entidades` y `core.puertos`:

```python
from core.entidades import LineaVenta, MovimientoInventario, Pago, Venta
from core.puertos import (
    RepositorioImpuestos, RepositorioInventario, RepositorioProductos, RepositorioVentas,
)
```

Y añadir al final del archivo:

```python
def salidas_de_venta(venta: Venta) -> list[MovimientoInventario]:
    """Mapea cada línea de la venta a una salida de inventario (regla de dominio pura)."""
    return [
        MovimientoInventario(
            producto_id=linea.producto_id,
            tipo="salida",
            cantidad=linea.cantidad_o_peso,
            fecha=venta.fecha,
            ref=f"venta:{venta.id}",
        )
        for linea in venta.lineas
    ]


class ServicioRegistroVenta:
    """Persiste la venta y descuenta el inventario. Solo conoce puertos."""

    def __init__(self, ventas: RepositorioVentas, inventario: RepositorioInventario) -> None:
        self._ventas = ventas
        self._inventario = inventario

    def registrar(self, venta: Venta, pagos: list[Pago]) -> Venta:
        guardada = self._ventas.guardar(venta, pagos)
        for movimiento in salidas_de_venta(guardada):
            self._inventario.registrar(movimiento)
        return guardada
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_registro_venta.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add src/core/servicio_venta.py tests/core/test_registro_venta.py
git commit -m "feat(core): ServicioRegistroVenta descuenta inventario al vender"
```

---

### Task E3.6: Flujo crítico — cierre de caja con arqueo de extremo a extremo

> Cierra el flujo crítico #4 de `testing-pos` ("cierre de caja con arqueo: cuadre de efectivo y medios de pago") con repos SQLite reales: abrir sesión, vender (descontando inventario), cerrar con arqueo, y verificar el cuadre por medio y el stock resultante.

**Files:**
- Test: `tests/ventas/test_flujo_cierre_caja.py`

**Interfaces:**
- Consumes: `RepositorioCategoriasSQLite`, `RepositorioImpuestosSQLite`, `RepositorioProductosSQLite`, `RepositorioInventarioSQLite` (E2.3); `RepositorioVentasSQLite`, `RepositorioCajaSesionesSQLite` (E1.5/E3.4); `ServicioVenta` (E1.3); `ServicioRegistroVenta` (E3.5); `ServicioCaja` (E3.3); fixture `conn` (E1.4).

- [ ] **Step 1: Write the test**

```python
# tests/ventas/test_flujo_cierre_caja.py
from datetime import datetime
from decimal import Decimal

from core.entidades import Categoria, Impuesto, MovimientoInventario, Pago, Producto
from core.servicio_caja import ServicioCaja
from core.servicio_venta import ServicioRegistroVenta, ServicioVenta
from inventario.repositorio_sqlite import (
    RepositorioCategoriasSQLite,
    RepositorioImpuestosSQLite,
    RepositorioInventarioSQLite,
    RepositorioProductosSQLite,
)
from ventas.repositorio_sqlite import (
    RepositorioCajaSesionesSQLite,
    RepositorioVentasSQLite,
)


def _seed(conn):
    cat = RepositorioCategoriasSQLite(conn).guardar(Categoria(nombre="Surtido"))
    imp = RepositorioImpuestosSQLite(conn)
    iva = imp.guardar(Impuesto(nombre="IVA", tarifa=Decimal("0.19")))
    excl = imp.guardar(Impuesto(nombre="Excluido", tarifa=Decimal("0")))
    prods = RepositorioProductosSQLite(conn)
    gaseosa = prods.guardar(Producto(codigo_barras="B", nombre="Gaseosa", precio=Decimal("3500"),
                                     categoria_id=cat.id, impuesto_id=iva.id))
    manzana = prods.guardar(Producto(codigo_barras="A", nombre="Manzana", precio=Decimal("4000"),
                                     categoria_id=cat.id, impuesto_id=excl.id,
                                     vendido_por_peso=True, unidad="kg"))
    inv = RepositorioInventarioSQLite(conn)
    inv.registrar(MovimientoInventario(producto_id=gaseosa.id, tipo="entrada",
                                       cantidad=Decimal("10"), fecha=datetime(2026, 6, 25, 8, 0)))
    inv.registrar(MovimientoInventario(producto_id=manzana.id, tipo="entrada",
                                       cantidad=Decimal("5"), fecha=datetime(2026, 6, 25, 8, 0)))
    return gaseosa, manzana, inv


def test_cierre_de_caja_cuadra_efectivo_y_descuenta_inventario(conn):
    gaseosa, manzana, inv = _seed(conn)
    sesiones = RepositorioCajaSesionesSQLite(conn)
    ventas = RepositorioVentasSQLite(conn)
    caja = ServicioCaja(sesiones, ventas)
    registro = ServicioRegistroVenta(ventas, inv)

    sesion = caja.abrir(fecha=datetime(2026, 6, 25, 9, 0), monto_inicial=Decimal("100000"))

    def vender(codigo, *, pago_medio, pago_monto, **kw):
        s = ServicioVenta(RepositorioProductosSQLite(conn), RepositorioImpuestosSQLite(conn))
        s.agregar(codigo, **kw)
        venta = s.confirmar(fecha=datetime(2026, 6, 25, 10, 0), caja_sesion_id=sesion.id)
        registro.registrar(venta, [Pago(medio_pago_id=pago_medio, monto=pago_monto)])

    vender("B", cantidad=2, pago_medio=1, pago_monto=Decimal("7000"))            # efectivo
    vender("A", peso_kg=Decimal("1.5"), pago_medio=1, pago_monto=Decimal("6000"))  # efectivo
    vender("B", cantidad=1, pago_medio=2, pago_monto=Decimal("3500"))            # tarjeta

    cerrada, arqueo = caja.cerrar(sesion_id=sesion.id, fecha=datetime(2026, 6, 25, 20, 0),
                                  monto_contado=Decimal("112000"))

    # Cuadre: efectivo esperado = base 100000 + 13000 en efectivo (tarjeta no entra al cajón)
    assert arqueo.efectivo_ventas == Decimal("13000")
    assert arqueo.esperado == Decimal("113000")
    assert arqueo.diferencia == Decimal("-1000")          # faltante de 1000
    assert cerrada.estado == "cerrada"
    assert cerrada.monto_contado == Decimal("112000")

    # Desglose completo por medio (efectivo + tarjeta)
    assert ventas.totales_por_medio(sesion.id) == {1: Decimal("13000"), 2: Decimal("3500")}

    # Inventario descontado por cada venta
    assert inv.stock_de(gaseosa.id) == Decimal("7")       # 10 - 2 - 1
    assert inv.stock_de(manzana.id) == Decimal("3.5")     # 5 - 1.5
```

- [ ] **Step 2: Run the test**

Run: `pytest tests/ventas/test_flujo_cierre_caja.py -v`
Expected: PASS (1 passed).

- [ ] **Step 3: Run the full suite**

Run: `pytest -v`
Expected: PASS (toda la suite E2 + E4 + E1 + E3 verde; el smoke de caja pasa o se salta según PySide6).

- [ ] **Step 4: Commit**

```bash
git add tests/ventas/test_flujo_cierre_caja.py
git commit -m "test(caja): flujo critico de cierre con arqueo y descuento de inventario"
```

---

## Definición de "hecho" (E3)

- `pytest -v` en verde; sin SQL fuera de `src/inventario/` y `src/ventas/`; sin imports de Qt/SQLite/pyserial dentro de `src/core/`.
- `ServicioCaja` abre/arquea/cierra sobre puertos; el arqueo cuadra efectivo contado vs. esperado y la diferencia distingue faltante (`< 0`) de sobrante (`> 0`).
- Registrar una venta descuenta el inventario (una `salida` por línea, con `ref = venta:<id>`).
- El flujo crítico #4 (cierre de caja con arqueo: cuadre de efectivo y medios de pago) tiene test de integración verde, e incluye la verificación del stock resultante.
- **Housekeeping de documentación** (heredado de E1, conviene cerrarlo aquí): actualizar el mapa de módulos en `CLAUDE.md` y `docs/README-pos.md` para incluir `src/ventas/` (ahora con `RepositorioCajaSesionesSQLite`) y marcar E3 como implementado. **Recomendado pasar el subagente `arquitecto-pos`** para bendecir que la persistencia de caja viva en `src/ventas/`.

## Self-Review (cobertura del encargo E3)

| Requisito (encargo / spec / testing-pos) | Task |
|---|---|
| Entidad `CajaSesion` | E3.1 |
| Valor `Arqueo` (resultado del cuadre) | E3.1 |
| Cálculo de arqueo (efectivo contado vs. esperado) | E3.2 |
| Servicio de apertura/cierre de caja | E3.3 |
| Puerto `RepositorioCajaSesiones` | E3.3 (puerto), E3.4 (adaptador) |
| `RepositorioVentas.totales_por_medio` (cuadre por medio) | E3.3 (puerto), E3.4 (adaptador) |
| Adaptador SQLite de `caja_sesiones` (tabla ya existe en 002) | E3.4 |
| Descuento de inventario al confirmar venta (diferido de E1) | E3.5 |
| Flujo crítico #4 "cierre de caja con arqueo" con test | E3.6 |
| Dinero/cantidades con `Decimal` exacto (sin `SUM()` de SQL) | Constraint global; E3.4 |
| core sin Qt/SQLite | Constraint global; servicios solo sobre puertos |

**Diferido a propósito (YAGNI):**
- **Devolución / anulación (flujo crítico #3):** fuera del alcance pedido para E3. En un **E3.b**, la reversa reutilizará `ServicioRegistroVenta` (movimientos `entrada`) y un nuevo estado/flujo de `Venta` `'anulada'`.
- **Atomicidad transaccional venta + salidas:** hoy ambos repos comparten la `conn` pero hacen `commit()` propio. Para una caja offline de un solo cajón es aceptable; un envoltorio transaccional único (begin/commit en el orquestador, repos sin `commit` interno) es refinamiento futuro.
- **UI de cierre/arqueo en Qt:** el dominio está completo y testeado; una `PantallaCierre` (cáscara sobre `ServicioCaja`) entra con E7 (reportes) o como refinamiento de `src/caja/`.
- **Retiros/ingresos de efectivo (payouts), turnos y multi-cajón:** no hay requisito presente; se modelan cuando aparezcan.
- **Validación de stock al vender (no permitir negativos):** no se bloquea la venta por existencias (carnicería/fruver); se añade si el negocio lo pide.

## Nota de arquitectura

Este plan **no** introduce módulos nuevos: extiende `src/core/` (entidades, cálculo, dos servicios y dos puertos) y `src/ventas/` (un adaptador y un método). Reafirma la decisión de E1 de alojar la persistencia no-UI del dominio venta/caja en `src/ventas/` — ahora también las sesiones de caja. Antes de mergear, **pasar el subagente `arquitecto-pos`** para validar la frontera y, si se aprueba, actualizar el mapa de módulos en `CLAUDE.md` y `docs/README-pos.md` (deuda de documentación pendiente desde E1).
