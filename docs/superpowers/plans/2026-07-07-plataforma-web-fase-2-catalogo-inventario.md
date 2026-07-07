# Plataforma web Fase 2 (NUBE2) — catálogo bidireccional + inventario multi-ubicación — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convertir la nube en la fuente de verdad del catálogo (maestro + precio/costo por local + promos) y montar el inventario multi-ubicación con movimientos entre cualquier par de ubicaciones, con sync bidireccional híbrido (catálogo por snapshot, inventario por delta), manteniendo el POS offline-first.

**Architecture:** Dos repos hermanos con `core` compartido (`pos-core`). El backend nube (FastAPI + Supabase Postgres) gana el maestro de catálogo (`productos` + overlay `productos_local` + `promociones`) y la topología de inventario (`ubicaciones` + `movimientos_inventario` append-only). El POS baja una réplica RO del catálogo por snapshot y aplica el delta de inventario por cursor por ubicación; el admin edita catálogo/inventario desde la web **y** desde el POS, empujando por el outbox existente (`/sync/push`). Conflictos de catálogo = last-write-wins por fila vía `actualizado_en`; inventario = append-only sin conflicto (única excepción: el flip `pendiente→confirmado` de un traslado).

**Tech Stack:** Python 3.11+, FastAPI, psycopg v3, Supabase Postgres, PySide6/SQLite (POS), React+Vite (frontend), pytest. `core/` es Python puro (sin Qt/SQLite).

## Global Constraints

- **Aislamiento hexagonal (no negociable):** `core/` NO conoce Qt ni SQLite ni psycopg. SQL solo en adaptadores de repositorio (`inventario/repositorio_sqlite.py`, `backend/app/repos_pg.py`, `backend/app/*.py`). Reglas de negocio (stock por ubicación, conversión, confirmación de traslado, LWW) viven en `core/`.
- **Ponytail (mínimo código):** reusar lo existente — outbox/`ClienteSync`/`HiloSincronizacion`, `ServicioReportes`, `promociones.py`/`servicio_promociones.py`, el patrón `stock_de` (suma de movimientos), el patrón de tests de `backend/tests/test_dashboard.py` (conexión fake unitaria + integración gated por `TEST_DB_URL`).
- **TDD donde aplique:** core y backend nube tienen pytest → test primero. El frontend NO tiene test runner (solo `npm run build` + `oxlint`) → verificación **manual en navegador**; no se reclama cobertura de test que no existe.
- **Dinero/cantidades:** siempre `Decimal`, nunca `float`. En JSON viajan como `str`. SQLite: adaptadores `DECIMAL`↔`Decimal` ya registrados en `inventario/db.py`. Postgres: `NUMERIC`↔`Decimal` por defecto en psycopg v3.
- **Idempotencia de sync:** upsert por `uuid` en ambos sentidos. En inventario el upsert solo crea la fila o aplica el flip `pendiente→confirmado`; nunca reescribe `cantidad`/`origen`/`destino`.
- **`actualizado_en` = base del LWW.** En ediciones web (online) lo pone el servidor (`now()`); en eventos POS lo trae el evento (cuándo editó el admin). El upsert conserva el máximo (`WHERE existente.actualizado_en < entrante.actualizado_en`).
- **Migraciones versionadas:** nube en `backend/migraciones/NNN_*.sql` (runner `migraciones_runner.py`, aplica ordenado, registra en `schema_migraciones`); POS en `scripts/migraciones/NNN_*.sql` (runner `inventario/db.py::aplicar_migraciones`). Nombres de archivo con prefijo numérico correlativo.
- **Baselines (verde antes de empezar):** `cd w:\POS && python -m pytest -q` = 420 passed. `cd w:\pos-plataforma-web\backend && .venv\Scripts\python -m pytest -q` = 18 passed, 5 skipped (sin `TEST_DB_URL`). ⚠️ La fixture de integración hace `DROP SCHEMA public CASCADE` — **NO** apuntes `TEST_DB_URL` a la BD real con datos; usa una BD/branch de prueba (Supabase branch vía MCP).
- **Git:** commits pequeños en español (`docs(nube2): …`, `feat(backend): …`, `feat(pos): …`, `feat(core): …`, `test(...)`). Los hooks bloquean heredocs en bash: para mensajes multilínea, escribe el mensaje a un archivo y usa `git commit -F <archivo>`. **NO** merge ni push sin preguntar. Rama de trabajo: `w:\POS` = `feature/plataforma-web-fase-0-1`; `w:\pos-plataforma-web` = `master`.

## Decisiones cerradas con el dueño (2026-07-07)

1. **`impuesto_id` = global en el maestro** (`productos.impuesto_id`). El IVA es nacional; una sola fuente de verdad.
2. **`costo` = en AMBAS tablas.** `productos.costo` es el **default/referencia** del maestro; `productos_local.costo` es el **costo local** (se **siembra** desde el maestro al importar y luego se edita a elección desde POS o web). Al igual que el resto de campos comerciales del overlay (`precio`, `activo`), es LWW por `actualizado_en`. *(Refina el spec §3.1, que ponía `costo` solo en el overlay.)*
3. **Confirmación de traslado = flip en la misma fila.** El movimiento de entrada del traslado nace `estado='pendiente'`; confirmar hace `UPDATE ... SET estado='confirmado', actualizado_en=now()`. El cursor de inventario propaga el flip. Append-only con esa única excepción.

## Reconciliaciones con el spec (léelas antes de codificar)

- **Promociones nube = campos reales de `core.Promocion`.** El spec §3.1 escribió `tipo('fijo'|'porcentaje')` / `vigencia`, pero `core.Promocion` usa `tipo_valor ('precio_fijo'|'porcentaje')`, `valor`, `tipo_duracion ('tiempo'|'unidades'|'manual')`, `activa`, `desde`, `hasta`, `unidades_limite`, `unidades_restantes`. La tabla nube `promociones` replica **esos** nombres + `local_id` + `actualizado_en`, para que la evaluación siga en `core` sin traducción.
- **Rol admin en la web = allowlist por email (demo).** El spec §6 dice "falta un check de rol". Ponytail para demo: env `ADMIN_EMAILS` (coma-separado) + dependencia `admin_web` que exige que el email del JWT esté en la lista. Se cambia por una tabla de roles cuando se endurezca RLS (spec §11 riesgo 4) — fuera de NUBE2.
- **`almacenes` → `ubicaciones` = rename + relax, sin vista de compat.** Se renombra la tabla, se agregan `tipo`/`activo` y se relaja `local_id NOT NULL`; las consultas de Fase 1 (`dashboard.py`) se migran a `FROM ubicaciones WHERE tipo='local'` (más limpio que una vista auto-actualizable, que rompe los INSERT de los fixtures). Las columnas `almacen_id` de Fase 1 se conservan (apuntan a `ubicaciones.id`).

## Notas de ejecución en vivo — Ola A (2026-07-07)

Aprendizajes reales al verificar la Ola A end-to-end (POS + backend + navegador). **Aplican a la Ola B.**

1. **Desplegar migraciones a la BD real, no solo a `pos_test`.** Los tests corren contra `pos_test`;
   la BD demo (`SUPABASE_DB_URL` → `/postgres`) NO se migra sola. La 005 faltaba en producción y
   `/sync/catalogo` daba 500 (`relation "productos_local" does not exist`). Paso de deploy por fase:
   `python -c "import psycopg,os; from app.migraciones_runner import aplicar_migraciones; aplicar_migraciones(psycopg.connect(os.environ['SUPABASE_DB_URL']))"`.
   **La Ola B (migración 006) necesita el mismo paso.**
2. **Alineación de ids POS↔nube = requisito.** La réplica busca precio por `producto_id` asumiendo
   `nube.productos.id == POS.productos.id`. Si no coinciden, el precio degrada al local (no rompe).
   Bootstrap hecho: sembrar el maestro nube + overlays `local-01` desde `w:\POS\pos.db`. Mantener
   este invariante en inventario (Ola B): `ubicaciones`/movimientos deben referenciar ids consistentes.
3. **`ADMIN_EMAILS` debe incluir el email real con que se entra a la web** (la cuenta demo era
   `admin@test.com`, no el email del dueño). Va en `backend/.env` (no versionado).
4. **Overlay = sync híbrido "aplica + avisa" (decisión del dueño, ya implementada en Ola A).** El precio
   de la nube se aplica solo (venta **e** inventario, ambos leen la réplica vía decorator; el maestro
   local no se toca desde el hilo). `RepositorioReplicaSQLite.aplicar_catalogo` detecta precios que
   cambiaron y los registra en `novedades_catalogo` (migración POS 014); `VentanaPrincipal` los muestra
   con un aviso no bloqueante en la barra de estado + diálogo "Entendido". Menor conocido: una edición
   hecha en el POS vuelve por la nube y se auto-avisa. Para inventario multi-ubicación (Ola B), considerar
   el mismo patrón de aviso si un movimiento/traslado llega desde la nube.

## File Structure

**Repo `w:\pos-plataforma-web` (backend + frontend):**
- Create `backend/migraciones/005_catalogo_maestro.sql` — impuestos, extend productos, productos_local, promociones, actualizado_en en categorias.
- Create `backend/migraciones/006_ubicaciones_movimientos.sql` — rename almacenes→ubicaciones, extend movimientos_inventario.
- Create `backend/app/catalogo.py` — endpoints `/sync/catalogo` (pull) + `/catalogo/*` (gestión web admin).
- Create `backend/app/inventario.py` — endpoints `/sync/inventario` (pull delta) + `/inventario/*` (gestión web admin).
- Modify `backend/app/sync.py` — materializar eventos catálogo/inventario del POS (upsert LWW / append + flip).
- Modify `backend/app/auth.py` — dependencia `admin_web`.
- Modify `backend/app/config.py` — `admin_emails`.
- Modify `backend/app/dashboard.py` — `FROM ubicaciones WHERE tipo='local'`.
- Modify `backend/app/main.py` — incluir routers nuevos.
- Create `backend/tests/test_catalogo.py`, `backend/tests/test_inventario.py`.
- Modify `backend/tests/test_dashboard.py`, `backend/tests/test_sync_push.py` — fixtures a `ubicaciones`.
- Create `frontend/src/catalogo/*` y `frontend/src/inventario/*` (React), enlazadas desde `App.tsx` con pestañas.

**Repo `w:\POS` (POS + core compartido):**
- Create `w:\POS\src\core\sync_lww.py` — regla pura LWW.
- Create `w:\POS\src\core\servicio_inventario_ubicaciones.py` — stock por ubicación, operaciones, confirmación (Python puro sobre un puerto nuevo).
- Modify `w:\POS\src\core\puertos.py` — puerto `RepositorioMovimientosUbicacion`.
- Create `w:\POS\scripts\migraciones\012_catalogo_replica.sql` — réplica RO + cursores.
- Create `w:\POS\scripts\migraciones\013_inventario_ubicaciones.sql` — ubicaciones + movimientos multi-ubicación + cursor por ubicación.
- Create `w:\POS\src\sync_pdv\replica.py` — adaptador que aplica snapshot de catálogo y delta de inventario.
- Modify `w:\POS\src\sync_pdv\cliente.py` — pull catálogo + inventario además del push.
- Modify `w:\POS\src\sync_pdv\outbox.py` — serializadores de eventos catálogo/movimiento.
- Modify `w:\POS\src\caja\contexto.py` — cablear pull en `HiloSincronizacion`, leer precios de la réplica.
- Tests espejo en `w:\POS\tests\...`.

---

# OLA A — Catálogo bidireccional

> **Verificable e2e al cerrar la ola:** editar precio en web → el POS lo baja al siguiente ciclo de sync; importar/editar en el POS (admin) → aparece en la web. LWW resuelve el único choque posible (mismo admin editando web+POS a la vez).

### Task NUBE2A.1: Migración nube `005_catalogo_maestro.sql` (maestro + overlay + promos)

**Files:**
- Create: `w:\pos-plataforma-web\backend\migraciones\005_catalogo_maestro.sql`
- Test: `w:\pos-plataforma-web\backend\tests\test_migraciones.py` (extender)

**Interfaces:**
- Produces: tablas `impuestos(id,nombre,tarifa,codigo_dian)`; `productos` extendida con `codigo_barras,unidad,vendido_por_peso,impuesto_id,costo,actualizado_en`; `productos_local(local_id,producto_id,precio,costo,activo,actualizado_en)` PK `(local_id,producto_id)`; `promociones(id,producto_id,local_id,tipo_valor,valor,tipo_duracion,activa,desde,hasta,unidades_limite,unidades_restantes,actualizado_en)`; `categorias.actualizado_en`.

- [ ] **Step 1: Escribir la migración**

```sql
-- 005_catalogo_maestro.sql
-- NUBE2 Ola A: la nube se vuelve maestro del catálogo (maestro + overlay por local + promos).

-- Impuesto nacional (IVA): global en el maestro (decisión 1).
CREATE TABLE impuestos (
  id          BIGINT PRIMARY KEY,
  nombre      TEXT NOT NULL,
  tarifa      NUMERIC NOT NULL,
  codigo_dian TEXT                      -- reservado DIAN
);

-- El maestro pasa de "espejo delgado del POS" (002) a fuente de verdad.
ALTER TABLE productos
  ADD COLUMN codigo_barras    TEXT,
  ADD COLUMN unidad           TEXT NOT NULL DEFAULT 'und',
  ADD COLUMN vendido_por_peso BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN impuesto_id      BIGINT REFERENCES impuestos(id),
  ADD COLUMN costo            NUMERIC NOT NULL DEFAULT 0,   -- default/referencia (decisión 2)
  ADD COLUMN actualizado_en   TIMESTAMPTZ NOT NULL DEFAULT now();

ALTER TABLE categorias
  ADD COLUMN actualizado_en TIMESTAMPTZ NOT NULL DEFAULT now();

-- Overlay: tener fila = ese local vende el producto (opt-in / import).
CREATE TABLE productos_local (
  local_id       TEXT NOT NULL REFERENCES locales(local_id),
  producto_id    BIGINT NOT NULL REFERENCES productos(id),
  precio         NUMERIC NOT NULL,
  costo          NUMERIC NOT NULL DEFAULT 0,   -- costo local (se siembra del maestro al importar)
  activo         BOOLEAN NOT NULL DEFAULT TRUE,
  actualizado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (local_id, producto_id)
);

-- Promos por local; campos = core.Promocion (ver reconciliación).
CREATE TABLE promociones (
  id                 BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  producto_id        BIGINT NOT NULL REFERENCES productos(id),
  local_id           TEXT NOT NULL REFERENCES locales(local_id),
  tipo_valor         TEXT NOT NULL,          -- 'precio_fijo' | 'porcentaje'
  valor              NUMERIC NOT NULL,
  tipo_duracion      TEXT NOT NULL,          -- 'tiempo' | 'unidades' | 'manual'
  activa             BOOLEAN NOT NULL DEFAULT TRUE,
  desde              TIMESTAMPTZ,
  hasta              TIMESTAMPTZ,
  unidades_limite    NUMERIC,
  unidades_restantes NUMERIC,
  actualizado_en     TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- Una activa por (producto, local): índice parcial único.
CREATE UNIQUE INDEX ux_promo_activa ON promociones (producto_id, local_id) WHERE activa;
CREATE INDEX ix_overlay_local ON productos_local (local_id);

ALTER TABLE impuestos ENABLE ROW LEVEL SECURITY;
ALTER TABLE productos_local ENABLE ROW LEVEL SECURITY;
ALTER TABLE promociones ENABLE ROW LEVEL SECURITY;
```

- [ ] **Step 2: Escribir el test de que la migración aplica y crea las tablas**

En `test_migraciones.py`, extiende el test gated por `TEST_DB_URL` (mismo patrón que el archivo ya tiene). Añade:

```python
def test_migracion_005_catalogo(conn_migrada):   # conn_migrada = fixture que corre aplicar_migraciones
    tablas = {r[0] for r in conn_migrada.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema='public'")}
    assert {"impuestos", "productos_local", "promociones"} <= tablas
    cols = {r[0] for r in conn_migrada.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name='productos'")}
    assert {"codigo_barras", "unidad", "impuesto_id", "costo", "actualizado_en"} <= cols
```

Si `test_migraciones.py` aún no tiene una fixture `conn_migrada`, créala con el patrón de `sembrada` (drop schema + `aplicar_migraciones`), gated por `TEST_DB_URL`.

- [ ] **Step 3: Ejecutar el test — debe pasar contra una BD de prueba**

Run: `cd w:\pos-plataforma-web\backend && $env:TEST_DB_URL="<branch-de-prueba>"; .venv\Scripts\python -m pytest tests/test_migraciones.py -q`
Expected: PASS (sin `TEST_DB_URL`, SKIP). Verifica también con MCP Supabase `list_tables` en el branch de prueba.

- [ ] **Step 4: Commit**

```bash
cd w:/pos-plataforma-web && git add backend/migraciones/005_catalogo_maestro.sql backend/tests/test_migraciones.py && git commit -F- <<'MSG'
feat(backend): migracion 005 catalogo maestro (overlay por local + promos)
MSG
```
*(Recuerda: los hooks bloquean heredoc en bash — escribe el mensaje a un archivo y usa `git commit -F mensaje.txt`.)*

---

### Task NUBE2A.2: Regla pura LWW en `core/sync_lww.py`

**Files:**
- Create: `w:\POS\src\core\sync_lww.py`
- Test: `w:\POS\tests\core\test_sync_lww.py`

**Interfaces:**
- Produces: `gana_escritura(entrante: datetime, existente: datetime | None) -> bool` — True si la escritura entrante debe sobrescribir. Se usa como guardia del upsert en el backend (`WHERE ... < entrante`) y en la réplica del POS.

- [ ] **Step 1: Escribir el test que falla**

```python
from datetime import datetime, timedelta
from core.sync_lww import gana_escritura

T0 = datetime(2026, 7, 7, 10, 0, 0)

def test_entrante_mas_nueva_gana():
    assert gana_escritura(T0 + timedelta(seconds=1), T0) is True

def test_entrante_mas_vieja_pierde():
    assert gana_escritura(T0 - timedelta(seconds=1), T0) is False

def test_igual_no_sobrescribe():
    assert gana_escritura(T0, T0) is False   # LWW estricto: empate conserva lo existente

def test_sin_existente_gana():
    assert gana_escritura(T0, None) is True
```

- [ ] **Step 2: Ejecutar el test — debe fallar**

Run: `cd w:\POS && python -m pytest tests/core/test_sync_lww.py -q`
Expected: FAIL con `ModuleNotFoundError: core.sync_lww`.

- [ ] **Step 3: Implementación mínima**

```python
"""Regla pura de last-write-wins por fila (base del sync bidireccional de catálogo)."""
from __future__ import annotations

from datetime import datetime


def gana_escritura(entrante: datetime, existente: datetime | None) -> bool:
    """True si la escritura entrante (su actualizado_en) debe sobrescribir a la existente.
    Empate conserva lo existente (no reescribe)."""
    return existente is None or entrante > existente
```

- [ ] **Step 4: Ejecutar el test — debe pasar**

Run: `cd w:\POS && python -m pytest tests/core/test_sync_lww.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
cd w:/POS && git add src/core/sync_lww.py tests/core/test_sync_lww.py && git commit -F mensaje.txt
# mensaje: feat(core): regla pura LWW gana_escritura para sync de catalogo
```

---

### Task NUBE2A.3: Endpoint pull `GET /sync/catalogo` (snapshot por local)

**Files:**
- Create: `w:\pos-plataforma-web\backend\app\catalogo.py`
- Modify: `w:\pos-plataforma-web\backend\app\main.py`
- Test: `w:\pos-plataforma-web\backend\tests\test_catalogo.py`

**Interfaces:**
- Consumes: `local_autenticado` (auth por token de local, de `app.auth`), `conectar` (de `app.db`).
- Produces: `GET /sync/catalogo` → `{"productos":[...], "promociones":[...]}` donde cada producto es el maestro **resuelto con su overlay activo** para ese local: `{producto_id, codigo_barras, nombre, unidad, vendido_por_peso, categoria_id, categoria_nombre, impuesto_id, tarifa_impuesto, precio, costo, actualizado_en}`; cada promo = campos de `core.Promocion` + `actualizado_en`. Solo productos con overlay `activo`.

- [ ] **Step 1: Escribir los tests (unitario con conexión fake + integración gated)**

```python
# test_catalogo.py — mismo andamiaje que test_dashboard.py (JWKS fake no hace falta: auth por token de local)
import os
import psycopg
import pytest
from fastapi.testclient import TestClient

import app.auth as auth_mod
import app.catalogo as cat_mod
from app.config import Settings
from app.main import app
from app.migraciones_runner import aplicar_migraciones

DB = os.environ.get("TEST_DB_URL")
HDR = {"Authorization": "Bearer local-01:tok1"}


@pytest.fixture(autouse=True)
def tokens(monkeypatch):
    monkeypatch.setattr(auth_mod, "settings", Settings(local_tokens={"local-01": "tok1"}))


# --- unitario: conexión fake con las tres consultas del snapshot -----------------
PRODS = [(1, "0001", "Lomo", "kg", True, 10, "Carnes", 5, "0.19",
          "20000", "12000", "2026-07-07T10:00:00")]
PROMOS = [(7, 1, "porcentaje", "0.10", "manual", True, None, None, None, None,
           "2026-07-07T10:00:00")]


class _Res:
    def __init__(self, filas): self._f = filas
    def fetchall(self): return self._f


class _ConnFake:
    def execute(self, sql, params=()):
        if "FROM productos" in sql:  # el JOIN maestro+overlay+categoria+impuesto
            return _Res(PRODS)
        if "FROM promociones" in sql:
            return _Res(PROMOS)
        raise AssertionError(sql)
    def __enter__(self): return self
    def __exit__(self, *e): return False


@pytest.fixture()
def conn_fake(monkeypatch):
    monkeypatch.setattr(cat_mod, "conectar", lambda: _ConnFake())


def test_snapshot_resuelve_overlay(conn_fake):
    r = TestClient(app).get("/sync/catalogo?local_id=local-01", headers=HDR)
    assert r.status_code == 200
    cuerpo = r.json()
    p = cuerpo["productos"][0]
    assert p["nombre"] == "Lomo" and p["precio"] == "20000" and p["costo"] == "12000"
    assert p["categoria_nombre"] == "Carnes" and p["tarifa_impuesto"] == "0.19"
    assert cuerpo["promociones"][0]["tipo_valor"] == "porcentaje"


def test_snapshot_sin_token_rechaza(conn_fake):
    assert TestClient(app).get("/sync/catalogo?local_id=local-01").status_code == 401
```

- [ ] **Step 2: Ejecutar los tests — deben fallar**

Run: `cd w:\pos-plataforma-web\backend && .venv\Scripts\python -m pytest tests/test_catalogo.py -q`
Expected: FAIL (`ModuleNotFoundError: app.catalogo` / 404).

- [ ] **Step 3: Implementar el endpoint**

```python
# backend/app/catalogo.py
"""Catálogo: pull snapshot para el POS (/sync/catalogo) + gestión web admin (/catalogo/*)."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth import local_autenticado
from app.db import conectar

router = APIRouter()

_SNAP_PRODUCTOS = """
  SELECT p.id, p.codigo_barras, p.nombre, p.unidad, p.vendido_por_peso,
         p.categoria_id, c.nombre AS categoria_nombre, p.impuesto_id, i.tarifa,
         pl.precio, pl.costo, pl.actualizado_en
  FROM productos_local pl
  JOIN productos p   ON p.id = pl.producto_id
  LEFT JOIN categorias c ON c.id = p.categoria_id
  LEFT JOIN impuestos  i ON i.id = p.impuesto_id
  WHERE pl.local_id = %s AND pl.activo
  ORDER BY p.id
"""
_SNAP_PROMOS = """
  SELECT id, producto_id, tipo_valor, valor, tipo_duracion, activa,
         desde, hasta, unidades_limite, unidades_restantes, actualizado_en
  FROM promociones WHERE local_id = %s AND activa ORDER BY id
"""


@router.get("/sync/catalogo")
def catalogo(local_id: str, _: str = Depends(local_autenticado)) -> dict:
    with conectar() as conn:
        prods = conn.execute(_SNAP_PRODUCTOS, (local_id,)).fetchall()
        promos = conn.execute(_SNAP_PROMOS, (local_id,)).fetchall()
    return {
        "productos": [{
            "producto_id": r[0], "codigo_barras": r[1], "nombre": r[2], "unidad": r[3],
            "vendido_por_peso": r[4], "categoria_id": r[5], "categoria_nombre": r[6],
            "impuesto_id": r[7], "tarifa_impuesto": None if r[8] is None else str(r[8]),
            "precio": str(r[9]), "costo": str(r[10]),
            "actualizado_en": r[11].isoformat() if hasattr(r[11], "isoformat") else r[11],
        } for r in prods],
        "promociones": [{
            "id": r[0], "producto_id": r[1], "tipo_valor": r[2], "valor": str(r[3]),
            "tipo_duracion": r[4], "activa": r[5],
            "desde": r[6].isoformat() if hasattr(r[6], "isoformat") and r[6] else r[6],
            "hasta": r[7].isoformat() if hasattr(r[7], "isoformat") and r[7] else r[7],
            "unidades_limite": None if r[8] is None else str(r[8]),
            "unidades_restantes": None if r[9] is None else str(r[9]),
            "actualizado_en": r[10].isoformat() if hasattr(r[10], "isoformat") else r[10],
        } for r in promos],
    }
```

En `main.py` añade el import y `app.include_router(catalogo_router)`:

```python
from app.catalogo import router as catalogo_router
# ...
app.include_router(catalogo_router)
```

- [ ] **Step 4: Ejecutar los tests — deben pasar**

Run: `cd w:\pos-plataforma-web\backend && .venv\Scripts\python -m pytest tests/test_catalogo.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Test de integración (opcional pero recomendado) + Commit**

Añade a `test_catalogo.py` una fixture `sembrada` gated por `TEST_DB_URL` (patrón de `test_dashboard.py`): inserta `locales`, `impuestos`, `categorias`, `productos` (maestro), `productos_local` (overlay activo), `promociones`, y verifica el snapshot real. Luego:

```bash
cd w:/pos-plataforma-web && git add backend/app/catalogo.py backend/app/main.py backend/tests/test_catalogo.py && git commit -F mensaje.txt
# mensaje: feat(backend): endpoint pull /sync/catalogo (snapshot maestro+overlay por local)
```

---

### Task NUBE2A.4: Dependencia `admin_web` (check de rol por allowlist de email)

**Files:**
- Modify: `w:\pos-plataforma-web\backend\app\auth.py`
- Modify: `w:\pos-plataforma-web\backend\app\config.py`
- Test: `w:\pos-plataforma-web\backend\tests\test_auth.py` (extender)

**Interfaces:**
- Consumes: `usuario_web` (JWT Supabase), `settings.admin_emails`.
- Produces: `admin_web(...) -> dict` — igual que `usuario_web` pero 403 si el email no está en `ADMIN_EMAILS`. Se usará como `dependencies=[Depends(admin_web)]` en los routers de gestión.

- [ ] **Step 1: Escribir el test que falla**

En `test_auth.py` (reusa el JWKS fake / `CLAVE` de `test_dashboard.py` — o replica ese andamiaje):

```python
def test_admin_web_rechaza_no_admin(monkeypatch):
    monkeypatch.setattr(auth_mod, "settings", Settings(admin_emails=("jefe@b.co",)))
    monkeypatch.setattr(auth_mod, "_jwks", lambda: _JwksFake())
    # token con email NO admin -> 403 en un endpoint protegido por admin_web
    ...
def test_admin_web_acepta_admin(monkeypatch):
    ...
```

*(El plan de detalle del test usa un endpoint de prueba montado sobre `admin_web`; alternativamente, verifícalo indirectamente en NUBE2A.5 sobre un endpoint real de gestión. Si prefieres, pospón este test a NUBE2A.5 y aquí solo implementa.)*

- [ ] **Step 2: Ejecutar — falla** (`AttributeError: settings.admin_emails` / `admin_web` no existe).

- [ ] **Step 3: Implementar**

En `config.py`, añade el campo y su carga:

```python
    admin_emails: tuple[str, ...] = ()
    # en cargar():
    admins = os.environ.get("ADMIN_EMAILS", "")
    # ...
        admin_emails=tuple(e.strip() for e in admins.split(",") if e.strip()),
```

En `auth.py`:

```python
def admin_web(usuario: dict = Depends(usuario_web)) -> dict:
    """usuario_web + exige que el email esté en ADMIN_EMAILS (rol admin demo)."""
    if usuario.get("email") not in settings.admin_emails:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "requiere rol admin")
    return usuario
```

(Import `Depends` en `auth.py` si no está.)

- [ ] **Step 4: Ejecutar — pasa.** Run: `.venv\Scripts\python -m pytest tests/test_auth.py -q` → PASS.

- [ ] **Step 5: Commit**

```
feat(backend): dependencia admin_web (allowlist ADMIN_EMAILS) para gestion
```

---

### Task NUBE2A.5: Endpoints de gestión web del catálogo (`/catalogo/*`, admin)

**Files:**
- Modify: `w:\pos-plataforma-web\backend\app\catalogo.py`
- Test: `w:\pos-plataforma-web\backend\tests\test_catalogo.py` (extender)

**Interfaces:**
- Consumes: `admin_web`, `conectar`, `core.sync_lww.gana_escritura` (para la guardia LWW en el upsert).
- Produces (todos `dependencies=[Depends(admin_web)]`):
  - `GET /catalogo/productos` → maestro completo (para la UI).
  - `POST /catalogo/productos` (upsert maestro) body `{id?, codigo_barras, nombre, unidad, vendido_por_peso, categoria_id, impuesto_id, costo}` → setea `actualizado_en=now()`.
  - `GET /catalogo/overlay?local_id=X` → overlays del local.
  - `POST /catalogo/overlay` (upsert masivo) body `{producto_id, precio?, costo?, activo?, locales: ["local-01",...] | "todos"}` → upsert por cada local (importar = crear fila; si falta `costo`, siembra del maestro), `actualizado_en=now()`. Devuelve nº de filas afectadas.
  - `POST /catalogo/promociones` (upsert promo) body = campos de `core.Promocion` + `local_id` → `actualizado_en=now()`; respeta el índice único de "una activa por (producto, local)".

- [ ] **Step 1: Escribir los tests** (con conexión fake que registra las sentencias, patrón `test_sync_push.py::_ConnFake`; y un caso de integración gated que verifique el upsert masivo "aplicar a todos"). Ejemplos de aserción:

```python
def test_overlay_aplicar_a_todos_upserta_por_local(conn_fake_reg):
    # body con locales="todos" -> el fake tiene 2 locales -> 2 upserts a productos_local
    ...
def test_upsert_maestro_setea_actualizado_en(conn_fake_reg):
    # la sentencia INSERT ... ON CONFLICT DO UPDATE incluye actualizado_en = now()
    ...
```

- [ ] **Step 2: Ejecutar — fallan.**

- [ ] **Step 3: Implementar** (añadir a `catalogo.py`; router de gestión con `admin_web`):

```python
from decimal import Decimal
from fastapi import APIRouter, Depends
from app.auth import admin_web

gestion = APIRouter(prefix="/catalogo", dependencies=[Depends(admin_web)])


@gestion.post("/productos")
def upsert_producto(p: dict) -> dict:
    with conectar() as conn:
        row = conn.execute(
            "INSERT INTO productos (id, codigo_barras, nombre, unidad, vendido_por_peso, "
            "categoria_id, impuesto_id, costo, actualizado_en) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s, now()) "
            "ON CONFLICT (id) DO UPDATE SET codigo_barras=EXCLUDED.codigo_barras, "
            "nombre=EXCLUDED.nombre, unidad=EXCLUDED.unidad, "
            "vendido_por_peso=EXCLUDED.vendido_por_peso, categoria_id=EXCLUDED.categoria_id, "
            "impuesto_id=EXCLUDED.impuesto_id, costo=EXCLUDED.costo, actualizado_en=now() "
            "RETURNING id",
            (p.get("id"), p.get("codigo_barras"), p["nombre"], p.get("unidad", "und"),
             p.get("vendido_por_peso", False), p.get("categoria_id"), p.get("impuesto_id"),
             Decimal(str(p.get("costo", "0"))))).fetchone()
        conn.commit()
    return {"id": row[0]}


@gestion.post("/overlay")
def upsert_overlay(body: dict) -> dict:
    prod = body["producto_id"]
    with conectar() as conn:
        if body.get("locales") == "todos":
            locales = [r[0] for r in conn.execute(
                "SELECT local_id FROM locales WHERE activo").fetchall()]
        else:
            locales = list(body["locales"])
        # costo por defecto = costo del maestro (siembra al importar)
        costo_master = conn.execute(
            "SELECT costo FROM productos WHERE id=%s", (prod,)).fetchone()
        costo_def = costo_master[0] if costo_master else Decimal("0")
        n = 0
        for loc in locales:
            conn.execute(
                "INSERT INTO productos_local (local_id, producto_id, precio, costo, activo, "
                "actualizado_en) VALUES (%s,%s,%s,%s,%s, now()) "
                "ON CONFLICT (local_id, producto_id) DO UPDATE SET "
                "precio=COALESCE(EXCLUDED.precio, productos_local.precio), "
                "costo=COALESCE(EXCLUDED.costo, productos_local.costo), "
                "activo=COALESCE(EXCLUDED.activo, productos_local.activo), "
                "actualizado_en=now()",
                (loc, prod,
                 None if body.get("precio") is None else Decimal(str(body["precio"])),
                 costo_def if body.get("costo") is None else Decimal(str(body["costo"])),
                 body.get("activo", True)))
            n += 1
        conn.commit()
    return {"afectados": n}


@gestion.post("/promociones")
def upsert_promocion(p: dict) -> dict:
    with conectar() as conn:
        # al activar una nueva, desactivar la activa previa del par (respeta ux_promo_activa)
        if p.get("activa", True):
            conn.execute("UPDATE promociones SET activa=false, actualizado_en=now() "
                         "WHERE producto_id=%s AND local_id=%s AND activa",
                         (p["producto_id"], p["local_id"]))
        row = conn.execute(
            "INSERT INTO promociones (producto_id, local_id, tipo_valor, valor, tipo_duracion, "
            "activa, desde, hasta, unidades_limite, unidades_restantes, actualizado_en) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, now()) RETURNING id",
            (p["producto_id"], p["local_id"], p["tipo_valor"], Decimal(str(p["valor"])),
             p["tipo_duracion"], p.get("activa", True), p.get("desde"), p.get("hasta"),
             p.get("unidades_limite"), p.get("unidades_restantes"))).fetchone()
        conn.commit()
    return {"id": row[0]}
```

Añade `GET /catalogo/productos` y `GET /catalogo/overlay` (SELECT simples). Registra el router en `main.py`: `app.include_router(catalogo_gestion_router)` (importa `gestion as catalogo_gestion_router`). Añade `POST` a `allow_methods` de CORS si aún no incluye lo necesario (ya están `GET`/`POST`).

- [ ] **Step 4: Ejecutar — pasan.** Run: `.venv\Scripts\python -m pytest tests/test_catalogo.py -q` → PASS.

- [ ] **Step 5: Commit**

```
feat(backend): gestion web de catalogo (upsert maestro/overlay masivo/promos, admin)
```

---

### Task NUBE2A.6: `/sync/push` materializa eventos de catálogo del POS (LWW)

**Files:**
- Modify: `w:\pos-plataforma-web\backend\app\sync.py`
- Test: `w:\pos-plataforma-web\backend\tests\test_sync_push.py` (extender)

**Interfaces:**
- Consumes: `core.sync_lww` (conceptual; en SQL la guardia es `WHERE existente.actualizado_en < EXCLUDED.actualizado_en`).
- Produces: `push` maneja `ev["tipo"]` ∈ {`venta` (ya), `catalogo_producto`, `catalogo_overlay`, `catalogo_promo`}. Payloads:
  - `catalogo_producto`: `{id, codigo_barras, nombre, unidad, vendido_por_peso, categoria_id, impuesto_id, costo, actualizado_en}`.
  - `catalogo_overlay`: `{local_id, producto_id, precio, costo, activo, actualizado_en}`.
  - `catalogo_promo`: campos de `core.Promocion` + `{local_id, actualizado_en}`.

- [ ] **Step 1: Test que falla** — un evento `catalogo_overlay` con `actualizado_en` mayor sobrescribe; uno con `actualizado_en` menor NO (LWW). Unitario con `_ConnFake` extendido + integración gated:

```python
def test_overlay_entrante_mas_viejo_no_sobrescribe(conn):  # integración
    # sembrar overlay con actualizado_en = T1; empujar evento con T0<T1; precio no cambia
    ...
```

- [ ] **Step 2: Ejecutar — falla.**

- [ ] **Step 3: Implementar** — en `sync.py::push`, tras el ledger idempotente, despachar por tipo:

```python
            tipo = ev["tipo"]
            if tipo == "venta":
                _materializar_venta(conn, ev["uuid"], ev["payload"])
            elif tipo == "catalogo_producto":
                _upsert_producto_maestro(conn, ev["payload"])
            elif tipo == "catalogo_overlay":
                _upsert_overlay(conn, ev["payload"])
            elif tipo == "catalogo_promo":
                _upsert_promo(conn, ev["payload"])
```

Con las funciones (LWW por `actualizado_en` traído del evento):

```python
def _upsert_overlay(conn, p: dict) -> None:
    conn.execute(
        "INSERT INTO productos_local (local_id, producto_id, precio, costo, activo, actualizado_en) "
        "VALUES (%s,%s,%s,%s,%s,%s) "
        "ON CONFLICT (local_id, producto_id) DO UPDATE SET "
        "precio=EXCLUDED.precio, costo=EXCLUDED.costo, activo=EXCLUDED.activo, "
        "actualizado_en=EXCLUDED.actualizado_en "
        "WHERE productos_local.actualizado_en < EXCLUDED.actualizado_en",
        (p["local_id"], p["producto_id"], Decimal(p["precio"]), Decimal(p["costo"]),
         p["activo"], p["actualizado_en"]))
```

`_upsert_producto_maestro` y `_upsert_promo` siguen el mismo molde (INSERT … ON CONFLICT DO UPDATE … WHERE existente.actualizado_en < EXCLUDED.actualizado_en). Para promos, la clave de conflicto es `id`; si el evento activa una nueva promo, primero desactiva la activa previa del par (como en NUBE2A.5).

- [ ] **Step 4: Ejecutar — pasa.** Run: `.venv\Scripts\python -m pytest tests/test_sync_push.py -q` → PASS.

- [ ] **Step 5: Commit**

```
feat(backend): /sync/push materializa eventos de catalogo del POS con LWW
```

---

### Task NUBE2A.7: Migración POS `012_catalogo_replica.sql` (réplica RO + cursores)

**Files:**
- Create: `w:\POS\scripts\migraciones\012_catalogo_replica.sql`
- Test: `w:\POS\tests\...\test_replica_schema.py` (o extender un test de migraciones existente)

**Interfaces:**
- Produces: tabla `catalogo_replica` (vista resuelta por producto que el POS vende) + `promo_replica` + `sync_cursor(clave TEXT PK, valor TEXT)` para guardar el cursor de catálogo/inventario.

- [ ] **Step 1: Escribir la migración**

```sql
-- 012_catalogo_replica.sql
-- NUBE2 Ola A: espejo RO del catálogo que el POS baja por snapshot y contra el que vende.
CREATE TABLE IF NOT EXISTS catalogo_replica (
    producto_id       INTEGER PRIMARY KEY,
    codigo_barras     TEXT,
    nombre            TEXT NOT NULL,
    unidad            TEXT NOT NULL DEFAULT 'und',
    vendido_por_peso  INTEGER NOT NULL DEFAULT 0,
    categoria_id      INTEGER,
    categoria_nombre  TEXT,
    impuesto_id       INTEGER,
    tarifa_impuesto   DECIMAL,
    precio            DECIMAL NOT NULL,
    costo             DECIMAL NOT NULL DEFAULT '0',
    activo            INTEGER NOT NULL DEFAULT 1,
    actualizado_en    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS promo_replica (
    id                 INTEGER PRIMARY KEY,
    producto_id        INTEGER NOT NULL,
    tipo_valor         TEXT NOT NULL,
    valor              DECIMAL NOT NULL,
    tipo_duracion      TEXT NOT NULL,
    activa             INTEGER NOT NULL DEFAULT 1,
    desde              TEXT,
    hasta              TEXT,
    unidades_limite    DECIMAL,
    unidades_restantes DECIMAL,
    actualizado_en     TEXT NOT NULL
);

-- Cursor genérico de sync (catálogo: última bajada; inventario: por ubicación en Ola B).
CREATE TABLE IF NOT EXISTS sync_cursor (
    clave TEXT PRIMARY KEY,
    valor TEXT NOT NULL
);
```

- [ ] **Step 2: Test** — aplica migraciones a una BD en memoria y verifica que existen las tablas:

```python
from inventario.db import conectar, aplicar_migraciones

def test_replica_tablas_existen():
    conn = conectar(":memory:")
    aplicar_migraciones(conn)
    tablas = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"catalogo_replica", "promo_replica", "sync_cursor"} <= tablas
```

- [ ] **Step 3: Ejecutar — pasa.** Run: `cd w:\POS && python -m pytest tests/<ruta>/test_replica_schema.py -q` → PASS.

- [ ] **Step 4: Commit**

```
feat(pos): migracion 012 replica RO de catalogo + tabla sync_cursor
```

---

### Task NUBE2A.8: Adaptador de réplica en el POS (aplica snapshot + lee precio)

**Files:**
- Create: `w:\POS\src\sync_pdv\replica.py`
- Test: `w:\POS\tests\sync_pdv\test_replica.py`

**Interfaces:**
- Consumes: conexión SQLite del POS.
- Produces: `RepositorioReplicaSQLite(conn)` con:
  - `aplicar_catalogo(snapshot: dict) -> None` — reemplaza `catalogo_replica` y `promo_replica` con el snapshot (`DELETE` + `INSERT` en una transacción); guarda `sync_cursor['catalogo']=max(actualizado_en)`.
  - `precio_de(producto_id: int) -> Decimal | None` y `producto(producto_id) -> dict | None` — lectura para la venta.
  - `listar() -> list[dict]` — para la pantalla de venta.

- [ ] **Step 1: Escribir el test que falla**

```python
from decimal import Decimal
from inventario.db import conectar, aplicar_migraciones
from sync_pdv.replica import RepositorioReplicaSQLite

SNAP = {"productos": [{
    "producto_id": 1, "codigo_barras": "0001", "nombre": "Lomo", "unidad": "kg",
    "vendido_por_peso": True, "categoria_id": 10, "categoria_nombre": "Carnes",
    "impuesto_id": 5, "tarifa_impuesto": "0.19", "precio": "20000", "costo": "12000",
    "actualizado_en": "2026-07-07T10:00:00"}], "promociones": []}

def _repo():
    conn = conectar(":memory:"); aplicar_migraciones(conn)
    return RepositorioReplicaSQLite(conn)

def test_aplicar_y_leer_precio():
    repo = _repo()
    repo.aplicar_catalogo(SNAP)
    assert repo.precio_de(1) == Decimal("20000")
    assert repo.listar()[0]["nombre"] == "Lomo"

def test_reemplaza_no_acumula():
    repo = _repo()
    repo.aplicar_catalogo(SNAP)
    repo.aplicar_catalogo({"productos": [], "promociones": []})
    assert repo.listar() == []            # snapshot vacío => réplica vacía (RO reemplazable)
```

- [ ] **Step 2: Ejecutar — falla** (`ModuleNotFoundError`).

- [ ] **Step 3: Implementar** `replica.py`:

```python
"""Adaptador SQLite de la réplica RO del catálogo. Reemplaza el espejo con el snapshot."""
from __future__ import annotations

from decimal import Decimal


class RepositorioReplicaSQLite:
    def __init__(self, conn) -> None:
        self._conn = conn

    def aplicar_catalogo(self, snapshot: dict) -> None:
        prods = snapshot.get("productos", [])
        promos = snapshot.get("promociones", [])
        self._conn.execute("DELETE FROM catalogo_replica")
        self._conn.execute("DELETE FROM promo_replica")
        self._conn.executemany(
            "INSERT INTO catalogo_replica (producto_id, codigo_barras, nombre, unidad, "
            "vendido_por_peso, categoria_id, categoria_nombre, impuesto_id, tarifa_impuesto, "
            "precio, costo, activo, actualizado_en) VALUES (?,?,?,?,?,?,?,?,?,?,?,1,?)",
            [(p["producto_id"], p["codigo_barras"], p["nombre"], p["unidad"],
              int(p["vendido_por_peso"]), p["categoria_id"], p["categoria_nombre"],
              p["impuesto_id"],
              None if p["tarifa_impuesto"] is None else Decimal(p["tarifa_impuesto"]),
              Decimal(p["precio"]), Decimal(p["costo"]), p["actualizado_en"]) for p in prods])
        self._conn.executemany(
            "INSERT INTO promo_replica (id, producto_id, tipo_valor, valor, tipo_duracion, "
            "activa, desde, hasta, unidades_limite, unidades_restantes, actualizado_en) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            [(pr["id"], pr["producto_id"], pr["tipo_valor"], Decimal(pr["valor"]),
              pr["tipo_duracion"], int(pr["activa"]), pr["desde"], pr["hasta"],
              None if pr["unidades_limite"] is None else Decimal(pr["unidades_limite"]),
              None if pr["unidades_restantes"] is None else Decimal(pr["unidades_restantes"]),
              pr["actualizado_en"]) for pr in promos])
        if prods:
            cursor = max(p["actualizado_en"] for p in prods)
            self._conn.execute(
                "INSERT INTO sync_cursor (clave, valor) VALUES ('catalogo', ?) "
                "ON CONFLICT (clave) DO UPDATE SET valor=excluded.valor", (cursor,))
        self._conn.commit()

    def precio_de(self, producto_id: int) -> Decimal | None:
        f = self._conn.execute(
            "SELECT precio FROM catalogo_replica WHERE producto_id=?", (producto_id,)).fetchone()
        return f["precio"] if f else None

    def producto(self, producto_id: int) -> dict | None:
        f = self._conn.execute(
            "SELECT * FROM catalogo_replica WHERE producto_id=?", (producto_id,)).fetchone()
        return dict(f) if f else None

    def listar(self) -> list[dict]:
        return [dict(f) for f in self._conn.execute(
            "SELECT * FROM catalogo_replica WHERE activo ORDER BY nombre").fetchall()]
```

- [ ] **Step 4: Ejecutar — pasa.** Run: `python -m pytest tests/sync_pdv/test_replica.py -q` → PASS.

- [ ] **Step 5: Commit**

```
feat(pos): adaptador RepositorioReplicaSQLite (aplica snapshot, lee precio para venta)
```

---

### Task NUBE2A.9: Pull de catálogo en `ClienteSync`/`HiloSincronizacion`

**Files:**
- Modify: `w:\POS\src\sync_pdv\cliente.py`
- Test: `w:\POS\tests\sync_pdv\test_cliente_pull.py`

**Interfaces:**
- Consumes: `RepositorioReplicaSQLite.aplicar_catalogo`, `TransporteSync`.
- Produces: `TransporteSync` gana `pull_catalogo(local_id) -> dict`; `ClienteSync.__init__` acepta `replica=None, local_id=None`; `ClienteSync.sincronizar()` primero hace push (como hoy) y luego, si hay `replica`, baja el snapshot y lo aplica. `TransporteHTTP.pull_catalogo` hace `GET {url}/sync/catalogo?local_id=...` con el mismo Bearer.

- [ ] **Step 1: Test que falla** — con un transporte fake que devuelve un snapshot, `sincronizar()` llama `replica.aplicar_catalogo(snapshot)`:

```python
class _TransFake:
    def push(self, eventos): return [e["uuid"] for e in eventos]
    def pull_catalogo(self, local_id): return {"productos": [], "promociones": []}

def test_sincronizar_aplica_snapshot(...):
    # replica espía que registra la llamada; assert que aplicar_catalogo fue invocado
    ...
```

- [ ] **Step 2: Ejecutar — falla.**

- [ ] **Step 3: Implementar** — extender `cliente.py`:

```python
class TransporteSync(Protocol):
    def push(self, eventos: list[dict]) -> list[str]: ...
    def pull_catalogo(self, local_id: str) -> dict: ...


class ClienteSync:
    def __init__(self, outbox, transporte, replica=None, local_id: str | None = None) -> None:
        self._outbox = outbox
        self._transporte = transporte
        self._replica = replica
        self._local_id = local_id

    def sincronizar(self, limite: int = 100) -> int:
        pendientes = self._outbox.pendientes(limite)
        aceptados = []
        if pendientes:
            aceptados = self._transporte.push([asdict(e) for e in pendientes])
            if aceptados:
                self._outbox.marcar_enviados(aceptados)
        if self._replica is not None and self._local_id:
            snap = self._transporte.pull_catalogo(self._local_id)
            self._replica.aplicar_catalogo(snap)
        return len(aceptados)
```

Y en `TransporteHTTP`:

```python
    def pull_catalogo(self, local_id: str) -> dict:
        import urllib.request, json
        req = urllib.request.Request(
            self._base + f"/sync/catalogo?local_id={local_id}",
            headers={"Authorization": self._auth})
        with urllib.request.urlopen(req, timeout=10.0) as r:
            return json.loads(r.read())
```

(Guarda `self._base = url.rstrip("/")` en `__init__` para reusar en push y pull.)

- [ ] **Step 4: Ejecutar — pasa.** Run: `python -m pytest tests/sync_pdv/ -q` → PASS.

- [ ] **Step 5: Commit**

```
feat(pos): ClienteSync baja snapshot de catalogo a la replica ademas del push
```

---

### Task NUBE2A.10: El POS vende leyendo precios de la réplica + cablear pull

**Files:**
- Modify: `w:\POS\src\caja\contexto.py`
- Test: `w:\POS\tests\caja\test_contexto_replica.py` (o test de integración de venta con réplica)

**Interfaces:**
- Consumes: `RepositorioReplicaSQLite`, `ClienteSync(replica=..., local_id=...)`.
- Produces: cuando hay `LOCAL_ID`, `ContextoApp` instancia la réplica; el `HiloSincronizacion` baja el catálogo; la lista de productos y el precio de venta salen de `catalogo_replica` cuando existe (fallback a `productos` local si la réplica está vacía → offline-first en primer arranque). El adaptador de venta lee `replica.precio_de(producto_id)`.

- [ ] **Step 1: Test** — con réplica sembrada, la pantalla/servicio de venta usa el precio de la réplica y no el de `productos`. (Test de integración a nivel de `ContextoApp` o del servicio que resuelve el precio de línea.)

- [ ] **Step 2: Ejecutar — falla.**

- [ ] **Step 3: Implementar** — en `contexto.py`, dentro del bloque `if local_id and almacen_id:` construir `replica = RepositorioReplicaSQLite(conn)` y pasarla a `ClienteSync(..., replica=replica, local_id=local_id)` (y al hilo, con su `conn_hilo`). Ajustar la resolución de precio de venta para consultar la réplica primero. Mantener el fallback al catálogo local cuando la réplica esté vacía (primer arranque sin sync).

  > Nota de alcance: esta es la parte más invasiva del POS. Cíñete a leer el precio desde la réplica en el punto donde hoy se toma `producto.precio`; no reescribas toda la pantalla de venta. Si el punto de lectura está muy acoplado, introduce un pequeño resolutor `precio_venta(producto_id)` que consulte réplica→fallback.

- [ ] **Step 4: Ejecutar — pasa** + suite POS verde (`python -m pytest -q`).

- [ ] **Step 5: Commit**

```
feat(pos): venta lee precio de la replica RO; hilo de sync baja catalogo
```

---

### Task NUBE2A.11: El POS (admin) edita/importa catálogo → encola en el outbox

**Files:**
- Modify: `w:\POS\src\sync_pdv\outbox.py`
- Modify: `w:\POS\src\caja\pantalla_inventario.py` (o donde viva la edición de productos del admin)
- Test: `w:\POS\tests\sync_pdv\test_serializar_catalogo.py`

**Interfaces:**
- Produces: `serializar_overlay(local_id, producto_id, precio, costo, activo, actualizado_en) -> EventoSync` (tipo `catalogo_overlay`), `serializar_producto_maestro(...) -> EventoSync` (tipo `catalogo_producto`), `serializar_promo(...) -> EventoSync` (tipo `catalogo_promo`). El admin, al importar/editar en el POS, llama al servicio de gestión que encola el evento; el push existente lo sube (materializado en NUBE2A.6).

- [ ] **Step 1: Test que falla** — `serializar_overlay(...)` produce un `EventoSync` con `tipo=="catalogo_overlay"` y payload con `precio`/`costo` como str y `actualizado_en`:

```python
def test_serializar_overlay():
    ev = serializar_overlay("local-01", 1, Decimal("21000"), Decimal("12000"), True,
                            "2026-07-07T11:00:00")
    assert ev.tipo == "catalogo_overlay"
    assert ev.payload["precio"] == "21000" and ev.payload["actualizado_en"]
```

- [ ] **Step 2: Ejecutar — falla.**

- [ ] **Step 3: Implementar** los serializadores en `outbox.py` (patrón de `serializar_venta`): construir el dict, `uuid=str(uuid4())`, `creado_en=now(UTC).isoformat()`, `actualizado_en` = el de la edición (mismo instante). Cablear en la UI del admin la llamada al encolar tras editar. La UI de gestión desde el POS puede reusar la pantalla de productos existente añadiendo el encolado; **si el alcance de la UI POS crece, córtalo a "editar precio local + importar (activar overlay)"** — que es lo que el e2e exige — y deja el CRUD completo del maestro para la web.

- [ ] **Step 4: Ejecutar — pasa** + suite POS verde.

- [ ] **Step 5: Commit**

```
feat(pos): serializadores de eventos de catalogo (overlay/maestro/promo) al outbox
```

---

### Task NUBE2A.12: UI web de catálogo (React, admin)

**Files:**
- Create: `w:\pos-plataforma-web\frontend\src\catalogo\Catalogo.tsx`, `frontend\src\catalogo\EditorOverlay.tsx`
- Modify: `w:\pos-plataforma-web\frontend\src\App.tsx` (pestañas Ventas / Catálogo / Inventario)
- Modify: `w:\pos-plataforma-web\frontend\src\api.ts` (añadir `apiPost`)

**Interfaces:**
- Consumes: `apiGet`/`apiPost` (JWT Supabase), endpoints `/catalogo/*`.
- Produces: pantalla admin: lista del maestro; alta/edición de producto; por producto, editor de overlay con selector **"aplicar a: todos / locales específicos"** que llama `POST /catalogo/overlay`; alta/edición de promo. **Sin test runner → verificación manual.**

- [ ] **Step 1: Añadir `apiPost` a `api.ts`**

```ts
export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token ?? "";
  const r = await fetch(`${import.meta.env.VITE_API_URL}${path}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`${r.status} ${path}`);
  return r.json() as Promise<T>;
}
```

- [ ] **Step 2: Escribir `Catalogo.tsx` y `EditorOverlay.tsx`** — lista de productos (`GET /catalogo/productos`), formulario de alta/edición (`POST /catalogo/productos`), y el editor de overlay con el selector "aplicar a". Sigue el estilo/tokens ya usados en `Dashboard.tsx` (mismos componentes/CSS). Carga la skill `frontend-design` solo si rediseñas la estética; para paridad con el dashboard actual, reusa sus patrones.

- [ ] **Step 3: Enlazar en `App.tsx`** — barra de pestañas simple (estado local `vista: "ventas"|"catalogo"|"inventario"`), render condicional. La pestaña Catálogo/Inventario solo aparece para emails admin (opcional en demo; el backend ya rechaza con 403).

- [ ] **Step 4: Build + verificación manual**

Run: `cd w:\pos-plataforma-web\frontend && npm run build && npx oxlint`
Expected: build OK, lint limpio. Verificación manual en el navegador se hace en NUBE2A.13.

- [ ] **Step 5: Commit**

```
feat(frontend): UI web de catalogo (maestro + overlay "aplicar a" + promos)
```

---

### Task NUBE2A.13: Verificación e2e de la Ola A (real, no solo build)

**Files:** ninguno (verificación); al final, nota en el propio plan / commit de cierre de ola si aplica.

- [ ] **Step 1:** Levanta backend (con `SUPABASE_DB_URL` al Session Pooler, `ADMIN_EMAILS` con tu email) y frontend (`npm run dev`). Aplica migraciones (arranque del backend o script).
- [ ] **Step 2:** En la web (logueado como admin): crea/edita un producto del maestro, impórtalo a `local-01` con un precio, guarda. Verifica `productos_local` en Supabase (MCP `execute_sql`).
- [ ] **Step 3:** Arranca el POS real (`w:\POS\iniciar_pos.ps1`, con `LOCAL_ID`/`ALMACEN_ID`/`SYNC_URL`/`LOCAL_TOKEN`). Espera un ciclo de sync (`SYNC_INTERVALO_SEGUNDOS`). Confirma que el producto/precio aparece en la venta del POS (leído de la réplica).
- [ ] **Step 4:** En el POS (admin), cambia el precio local o importa otro producto. Espera el push. Confirma en la web que el cambio se refleja (`GET /catalogo/overlay`).
- [ ] **Step 5:** Caso LWW: edita el mismo overlay en web y POS con marcas de tiempo distintas; confirma que gana el `actualizado_en` mayor. Documenta el resultado (qué se probó y cómo) en el reporte final.

> **Checkpoint de revisión (subagent-driven / executing-plans):** no arranques la Ola B hasta que el usuario confirme la Ola A verificada en navegador.

---

# OLA B — Inventario multi-ubicación

> **Verificable e2e al cerrar la ola:** traslado cross-local (local A → local B) → el destino confirma; el stock por ubicación cuadra en ambos y en la web.

### Task NUBE2B.1: Migración nube `006_ubicaciones_movimientos.sql`

**Files:**
- Create: `w:\pos-plataforma-web\backend\migraciones\006_ubicaciones_movimientos.sql`
- Test: `w:\pos-plataforma-web\backend\tests\test_migraciones.py` (extender)

**Interfaces:**
- Produces: `almacenes` renombrada a `ubicaciones` con `tipo ('bodega'|'local')`, `activo`, `local_id` NULLABLE; `movimientos_inventario` extendida con `tipo` (entrada/salida/ajuste/traslado/conversion), `origen_id`, `destino_id`, `estado ('confirmado'|'pendiente')`, `grupo_uuid`, `lote_id`, `ref`, `actualizado_en`.

- [ ] **Step 1: Escribir la migración**

```sql
-- 006_ubicaciones_movimientos.sql
-- NUBE2 Ola B: generaliza almacenes->ubicaciones (bodegas compartidas) y
-- movimientos_inventario multi-ubicacion append-only.

ALTER TABLE almacenes RENAME TO ubicaciones;
ALTER TABLE ubicaciones ADD COLUMN tipo TEXT NOT NULL DEFAULT 'local';  -- 'bodega'|'local'
ALTER TABLE ubicaciones ALTER COLUMN local_id DROP NOT NULL;            -- NULL = bodega compartida
-- (las filas de Fase 1 quedan tipo='local', local_id intacto)

-- Reconstruye movimientos_inventario multi-ubicacion (003 tenia entrada/salida simple).
ALTER TABLE inventario_movimientos ADD COLUMN origen_id      BIGINT REFERENCES ubicaciones(id);
ALTER TABLE inventario_movimientos ADD COLUMN destino_id     BIGINT REFERENCES ubicaciones(id);
ALTER TABLE inventario_movimientos ADD COLUMN estado         TEXT NOT NULL DEFAULT 'confirmado';
ALTER TABLE inventario_movimientos ADD COLUMN grupo_uuid     UUID;
ALTER TABLE inventario_movimientos ADD COLUMN lote_id        BIGINT;
ALTER TABLE inventario_movimientos ADD COLUMN ref            TEXT;
ALTER TABLE inventario_movimientos ADD COLUMN actualizado_en TIMESTAMPTZ NOT NULL DEFAULT now();
-- 'almacen_id' de 003 se conserva como la ubicacion "dueña" del registro append-only;
-- para entrada => destino_id=almacen_id; salida => origen_id=almacen_id.

CREATE INDEX ix_mov_ubic_cursor ON inventario_movimientos (destino_id, actualizado_en);
CREATE INDEX ix_mov_ubic_origen ON inventario_movimientos (origen_id, actualizado_en);
```

> Nota: `movimientos_inventario` de Fase 1 tiene 0 filas (spec de contexto), así que no hay backfill de datos que hacer.

- [ ] **Step 2: Test** — extiende `test_migraciones.py`: tras aplicar, `ubicaciones` existe, `almacenes` no, y las columnas nuevas de `inventario_movimientos` están. Gated por `TEST_DB_URL`.

- [ ] **Step 3: Ejecutar — pasa** contra branch de prueba.

- [ ] **Step 4: Commit**

```
feat(backend): migracion 006 ubicaciones + movimientos_inventario multi-ubicacion
```

---

### Task NUBE2B.2: `dashboard.py` y fixtures de test migran a `ubicaciones`

**Files:**
- Modify: `w:\pos-plataforma-web\backend\app\dashboard.py`
- Modify: `w:\pos-plataforma-web\backend\tests\test_dashboard.py`, `backend\tests\test_sync_push.py`
- Test: los propios (deben quedar verdes).

**Interfaces:**
- Produces: `dashboard.resumen` consulta `FROM ubicaciones WHERE activo AND tipo='local'` (los reportes de venta son por punto de venta, no por bodega).

- [ ] **Step 1: Actualizar el test primero** — en `test_dashboard.py::_ConnFake`, cambia `if "FROM almacenes"` por `if "FROM ubicaciones"`; en los fixtures de integración (`sembrada`, y `conn` de `test_sync_push.py`) cambia `INSERT INTO almacenes (...)` por `INSERT INTO ubicaciones (id,nombre,local_id,tipo) VALUES (...,'local')`.

- [ ] **Step 2: Ejecutar — falla** (dashboard aún dice `FROM almacenes`).

- [ ] **Step 3: Implementar** — en `dashboard.py`:

```python
        ubicaciones = conn.execute(
            "SELECT id, nombre FROM ubicaciones WHERE activo AND tipo='local' ORDER BY id"
        ).fetchall()
```

(y renombra la variable local `almacenes`→`ubicaciones`; el resto del código y el nombre de columna `almacen_id` en `ventas` no cambian).

- [ ] **Step 4: Ejecutar — pasan** los 3 tests de dashboard unitarios + push. Run: `.venv\Scripts\python -m pytest tests/test_dashboard.py tests/test_sync_push.py -q` → PASS.

- [ ] **Step 5: Commit**

```
refactor(backend): dashboard y fixtures usan ubicaciones (tipo='local')
```

---

### Task NUBE2B.3: Reglas de inventario multi-ubicación en `core` (stock, operaciones, confirmación)

**Files:**
- Create: `w:\POS\src\core\servicio_inventario_ubicaciones.py`
- Modify: `w:\POS\src\core\puertos.py`
- Test: `w:\POS\tests\core\test_inventario_ubicaciones.py`

**Interfaces:**
- Produces (Python puro sobre un puerto):
  - Puerto `RepositorioMovimientosUbicacion` con `registrar(mov: dict) -> None`, `confirmar(uuid: str) -> None`, `stock(ubicacion_id: int, producto_id: int) -> Decimal`, `movimientos_grupo(grupo_uuid) -> list[dict]`.
  - `stock_por_suma(movimientos: list[dict], ubicacion_id: int, producto_id: int) -> Decimal` — función pura: Σ entradas confirmadas a la ubicación − Σ salidas confirmadas desde la ubicación (entrada=`destino_id`, salida=`origen_id`).
  - `plan_traslado(producto_id, cantidad, origen_id, destino_id, fecha) -> list[dict]` — 1 salida confirmada en origen + 1 entrada **pendiente** en destino, mismo `grupo_uuid`.
  - `plan_conversion(origen_id, salidas, entradas, fecha) -> list[dict]` — 1 salida del origen + N entradas en la **misma** ubicación, solo cantidades (merma permitida), mismo `grupo_uuid`. Reusa los ratios de cantidad; **sin costeo**.

- [ ] **Step 1: Escribir los tests que fallan** (pure, sin BD):

```python
from decimal import Decimal
from datetime import datetime
from core.servicio_inventario_ubicaciones import (
    stock_por_suma, plan_traslado, plan_conversion)

F = datetime(2026, 7, 7, 12, 0, 0)

def test_stock_suma_confirmados():
    movs = [
        {"tipo": "entrada", "producto_id": 1, "cantidad": Decimal("200"),
         "destino_id": 5, "origen_id": None, "estado": "confirmado"},
        {"tipo": "salida", "producto_id": 1, "cantidad": Decimal("30"),
         "origen_id": 5, "destino_id": None, "estado": "confirmado"},
        {"tipo": "entrada", "producto_id": 1, "cantidad": Decimal("10"),
         "destino_id": 5, "origen_id": None, "estado": "pendiente"},  # no cuenta
    ]
    assert stock_por_suma(movs, 5, 1) == Decimal("170")

def test_plan_traslado_pendiente_en_destino():
    movs = plan_traslado(1, Decimal("50"), origen_id=5, destino_id=8, fecha=F)
    salida = next(m for m in movs if m["tipo"] == "salida")
    entrada = next(m for m in movs if m["tipo"] == "entrada")
    assert salida["origen_id"] == 5 and salida["estado"] == "confirmado"
    assert entrada["destino_id"] == 8 and entrada["estado"] == "pendiente"
    assert salida["grupo_uuid"] == entrada["grupo_uuid"]

def test_plan_conversion_solo_cantidades():
    movs = plan_conversion(
        origen_id=5,
        salidas=[(1, Decimal("200"))],
        entradas=[(2, Decimal("120")), (3, Decimal("60"))],  # merma 20, permitida
        fecha=F)
    assert sum(1 for m in movs if m["tipo"] == "salida") == 1
    assert sum(1 for m in movs if m["tipo"] == "entrada") == 2
    assert all(m["origen_id"] == 5 or m["destino_id"] == 5 for m in movs)
```

- [ ] **Step 2: Ejecutar — falla.**

- [ ] **Step 3: Implementar** `servicio_inventario_ubicaciones.py`:

```python
"""Reglas puras de inventario multi-ubicación: stock por suma de confirmados y
composición de operaciones (traslado, conversión). Python puro, sin BD ni costeo."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

CERO = Decimal("0")


def stock_por_suma(movs, ubicacion_id: int, producto_id: int) -> Decimal:
    total = CERO
    for m in movs:
        if m["producto_id"] != producto_id or m["estado"] != "confirmado":
            continue
        if m.get("destino_id") == ubicacion_id:
            total += m["cantidad"]
        if m.get("origen_id") == ubicacion_id:
            total -= m["cantidad"]
    return total


def _mov(tipo, producto_id, cantidad, *, origen_id, destino_id, estado, grupo, fecha):
    return {"uuid": str(uuid4()), "tipo": tipo, "producto_id": producto_id,
            "cantidad": cantidad, "origen_id": origen_id, "destino_id": destino_id,
            "estado": estado, "grupo_uuid": grupo, "fecha": fecha}


def plan_traslado(producto_id, cantidad, *, origen_id, destino_id, fecha) -> list[dict]:
    grupo = str(uuid4())
    return [
        _mov("salida", producto_id, cantidad, origen_id=origen_id, destino_id=None,
             estado="confirmado", grupo=grupo, fecha=fecha),
        _mov("entrada", producto_id, cantidad, origen_id=None, destino_id=destino_id,
             estado="pendiente", grupo=grupo, fecha=fecha),
    ]


def plan_conversion(*, origen_id, salidas, entradas, fecha) -> list[dict]:
    grupo = str(uuid4())
    movs = []
    for pid, cant in salidas:
        movs.append(_mov("salida", pid, cant, origen_id=origen_id, destino_id=None,
                         estado="confirmado", grupo=grupo, fecha=fecha))
    for pid, cant in entradas:
        movs.append(_mov("entrada", pid, cant, origen_id=None, destino_id=origen_id,
                         estado="confirmado", grupo=grupo, fecha=fecha))
    return movs
```

En `puertos.py` añade el `Protocol` `RepositorioMovimientosUbicacion` (firmas de arriba).

- [ ] **Step 4: Ejecutar — pasa.** Run: `python -m pytest tests/core/test_inventario_ubicaciones.py -q` → PASS.

- [ ] **Step 5: Commit**

```
feat(core): reglas puras de inventario multi-ubicacion (stock, traslado, conversion)
```

---

### Task NUBE2B.4: Endpoints de gestión web de inventario (`/inventario/*`, admin)

**Files:**
- Create: `w:\pos-plataforma-web\backend\app\inventario.py`
- Modify: `w:\pos-plataforma-web\backend\app\main.py`
- Test: `w:\pos-plataforma-web\backend\tests\test_inventario.py`

**Interfaces:**
- Consumes: `admin_web`, `conectar`, `core.servicio_inventario_ubicaciones` (planes de traslado/conversión + stock).
- Produces (`dependencies=[Depends(admin_web)]`):
  - `POST /inventario/entrada` `{producto_id, cantidad, destino_id, ref?}` → 1 mov entrada confirmado.
  - `POST /inventario/salida` y `/inventario/ajuste` `{producto_id, cantidad, origen_id, ref?}`.
  - `POST /inventario/traslado` `{producto_id, cantidad, origen_id, destino_id}` → `plan_traslado` (salida confirmada + entrada pendiente).
  - `POST /inventario/confirmar` `{grupo_uuid}` → flip `pendiente→confirmado` de la entrada del grupo (`actualizado_en=now()`).
  - `POST /inventario/conversion` `{origen_id, salidas:[[pid,cant]], entradas:[[pid,cant]]}`.
  - `GET /inventario/stock?ubicacion_id=U` → stock por producto en U.
  - `GET /inventario/pendientes?ubicacion_id=U` → entradas pendientes cuyo `destino_id=U` (bandeja).

- [ ] **Step 1: Escribir tests** (fake + integración gated). Casos mínimos: entrada suma stock; traslado deja entrada pendiente en destino; confirmar cambia estado y stock del destino; pendientes lista el traslado entrante.

```python
def test_traslado_y_confirmacion(conn):   # integración gated
    # entrada 200 a ubic 5; traslado 50 de 5->8; stock(8)=0 (pendiente); confirmar; stock(8)=50
    ...
```

- [ ] **Step 2: Ejecutar — falla.**

- [ ] **Step 3: Implementar** `inventario.py`. Los movimientos se insertan en `inventario_movimientos` (con `almacen_id` = la ubicación dueña: destino en entrada, origen en salida; `origen_id`/`destino_id` según el plan de core; `local_id` = el del local de la ubicación, o el del origen en traslado). El stock se calcula con `stock_por_suma` sobre los movimientos de la ubicación, o con una consulta SQL agregada equivalente. Confirmar:

```python
@router.post("/inventario/confirmar")
def confirmar(body: dict) -> dict:
    with conectar() as conn:
        conn.execute(
            "UPDATE inventario_movimientos SET estado='confirmado', actualizado_en=now() "
            "WHERE grupo_uuid=%s AND tipo='entrada' AND estado='pendiente'",
            (body["grupo_uuid"],))
        conn.commit()
    return {"ok": True}
```

Registra el router en `main.py`.

- [ ] **Step 4: Ejecutar — pasan.**

- [ ] **Step 5: Commit**

```
feat(backend): gestion web de inventario (entrada/salida/ajuste/traslado/confirmar/conversion/stock)
```

---

### Task NUBE2B.5: Endpoint pull `GET /sync/inventario` (delta por cursor por ubicación)

**Files:**
- Modify: `w:\pos-plataforma-web\backend\app\inventario.py`
- Test: `w:\pos-plataforma-web\backend\tests\test_inventario.py` (extender)

**Interfaces:**
- Consumes: `local_autenticado`.
- Produces: `GET /sync/inventario?ubicacion_id=U&desde=<cursor>` → movimientos nuevos que **tocan** U (origen o destino) con `actualizado_en > desde`, ordenados por `actualizado_en`; incluye los flips de confirmación (porque el flip actualiza `actualizado_en`). Respuesta `{"movimientos":[...], "cursor": <max actualizado_en>}`.

- [ ] **Step 1: Test que falla** — sembrar movimientos con `actualizado_en` crecientes; pedir con `desde` intermedio → solo devuelve los posteriores; el flip de confirmación reaparece con su nuevo `actualizado_en`.

- [ ] **Step 2: Ejecutar — falla.**

- [ ] **Step 3: Implementar**:

```python
@router.get("/sync/inventario")
def sync_inventario(ubicacion_id: int, desde: str | None = None,
                    _: str = Depends(local_autenticado)) -> dict:
    tope = desde or "1970-01-01T00:00:00+00:00"
    with conectar() as conn:
        filas = conn.execute(
            "SELECT uuid, tipo, producto_id, cantidad, origen_id, destino_id, estado, "
            "grupo_uuid, lote_id, ref, fecha, actualizado_en FROM inventario_movimientos "
            "WHERE (origen_id=%s OR destino_id=%s) AND actualizado_en > %s "
            "ORDER BY actualizado_en", (ubicacion_id, ubicacion_id, tope)).fetchall()
    movs = [{"uuid": str(r[0]), "tipo": r[1], "producto_id": r[2], "cantidad": str(r[3]),
             "origen_id": r[4], "destino_id": r[5], "estado": r[6],
             "grupo_uuid": None if r[7] is None else str(r[7]), "lote_id": r[8],
             "ref": r[9], "fecha": r[10].isoformat(),
             "actualizado_en": r[11].isoformat()} for r in filas]
    cursor = movs[-1]["actualizado_en"] if movs else desde
    return {"movimientos": movs, "cursor": cursor}
```

- [ ] **Step 4: Ejecutar — pasa.**

- [ ] **Step 5: Commit**

```
feat(backend): endpoint pull /sync/inventario (delta por cursor por ubicacion)
```

---

### Task NUBE2B.6: `/sync/push` materializa `movimiento_inventario` del POS (append + flip)

**Files:**
- Modify: `w:\pos-plataforma-web\backend\app\sync.py`
- Test: `w:\pos-plataforma-web\backend\tests\test_sync_push.py` (extender)

**Interfaces:**
- Produces: `push` maneja `tipo == "movimiento_inventario"` con payload `{uuid, tipo, producto_id, cantidad, origen_id, destino_id, estado, grupo_uuid, lote_id, ref, fecha, almacen_id, local_id, actualizado_en}`. Upsert por `uuid`: crea la fila **o** aplica el flip `pendiente→confirmado`; nunca reescribe cantidad/origen/destino.

- [ ] **Step 1: Test que falla** — empujar un movimiento nuevo lo inserta; re-empujar el mismo uuid con `estado='confirmado'` solo cambia el estado (no duplica, no toca cantidad).

- [ ] **Step 2: Ejecutar — falla.**

- [ ] **Step 3: Implementar** — en `sync.py`, rama nueva:

```python
            elif tipo == "movimiento_inventario":
                _materializar_movimiento(conn, ev["payload"])
```

```python
def _materializar_movimiento(conn, p: dict) -> None:
    conn.execute(
        "INSERT INTO inventario_movimientos (uuid, local_id, almacen_id, producto_id, tipo, "
        "cantidad, origen_id, destino_id, estado, grupo_uuid, lote_id, ref, fecha, actualizado_en) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
        "ON CONFLICT (uuid) DO UPDATE SET estado=EXCLUDED.estado, actualizado_en=EXCLUDED.actualizado_en "
        "WHERE inventario_movimientos.estado='pendiente' AND EXCLUDED.estado='confirmado'",
        (p["uuid"], p["local_id"], p["almacen_id"], p["producto_id"], p["tipo"],
         Decimal(p["cantidad"]), p.get("origen_id"), p.get("destino_id"),
         p.get("estado", "confirmado"), p.get("grupo_uuid"), p.get("lote_id"),
         p.get("ref"), p["fecha"], p["actualizado_en"]))
```

- [ ] **Step 4: Ejecutar — pasa.**

- [ ] **Step 5: Commit**

```
feat(backend): /sync/push materializa movimiento_inventario (append + flip confirmacion)
```

---

### Task NUBE2B.7: Migración POS `013_inventario_ubicaciones.sql` + adaptador

**Files:**
- Create: `w:\POS\scripts\migraciones\013_inventario_ubicaciones.sql`
- Create: `w:\POS\src\inventario\repositorio_ubicaciones_sqlite.py`
- Test: `w:\POS\tests\inventario\test_repositorio_ubicaciones.py`

**Interfaces:**
- Produces: en el POS, `ubicaciones` (espejo mínimo: id, nombre, tipo, local_id) + `movimientos_ubicacion` (uuid, tipo, producto_id, cantidad, origen_id, destino_id, estado, grupo_uuid, lote_id, ref, fecha, actualizado_en) + cursor por ubicación en `sync_cursor` (clave `inventario:<ubicacion_id>`). `RepositorioMovimientosUbicacionSQLite(conn)` implementa el puerto `RepositorioMovimientosUbicacion` de NUBE2B.3 (stock por suma, registrar, confirmar, aplicar delta).

- [ ] **Step 1: Escribir la migración** (tipos DECLARADOS para portabilidad; `movimientos_ubicacion` append-only salvo el flip):

```sql
-- 013_inventario_ubicaciones.sql — NUBE2 Ola B (POS).
CREATE TABLE IF NOT EXISTS ubicaciones (
    id       INTEGER PRIMARY KEY,
    nombre   TEXT NOT NULL,
    tipo     TEXT NOT NULL DEFAULT 'local',   -- 'bodega'|'local'
    local_id TEXT,
    activo   INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS movimientos_ubicacion (
    uuid           TEXT PRIMARY KEY,
    tipo           TEXT NOT NULL,             -- entrada|salida|ajuste|traslado|conversion
    producto_id    INTEGER NOT NULL,
    cantidad       DECIMAL NOT NULL,
    origen_id      INTEGER,
    destino_id     INTEGER,
    estado         TEXT NOT NULL DEFAULT 'confirmado',  -- confirmado|pendiente
    grupo_uuid     TEXT,
    lote_id        INTEGER,
    ref            TEXT,
    fecha          TEXT NOT NULL,
    actualizado_en TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_mov_ubic_dest ON movimientos_ubicacion (destino_id);
CREATE INDEX IF NOT EXISTS ix_mov_ubic_orig ON movimientos_ubicacion (origen_id);
```

- [ ] **Step 2: Escribir el test que falla** — registrar entrada/salida y comprobar `stock`; aplicar un delta con un flip de confirmación y comprobar que el stock del destino sube.

- [ ] **Step 3: Ejecutar — falla.**

- [ ] **Step 4: Implementar** `repositorio_ubicaciones_sqlite.py` — `registrar(mov)` inserta `INSERT OR IGNORE` por uuid; `confirmar(uuid)` hace el flip; `stock(ubic, prod)` = SQL agregado (Σ entradas confirmadas a destino − Σ salidas confirmadas desde origen); `aplicar_delta(movs)` upsert por uuid (insert nuevo o flip). Reusa `core.servicio_inventario_ubicaciones.stock_por_suma` en tests para cruzar.

- [ ] **Step 5: Ejecutar — pasa** + suite POS verde. **Commit**

```
feat(pos): migracion 013 + RepositorioMovimientosUbicacionSQLite (stock, registrar, confirmar, delta)
```

---

### Task NUBE2B.8: Pull de inventario (delta) en `ClienteSync` + aplicar

**Files:**
- Modify: `w:\POS\src\sync_pdv\cliente.py`
- Modify: `w:\POS\src\sync_pdv\replica.py` (o el repo de ubicaciones) para guardar/leer el cursor por ubicación
- Test: `w:\POS\tests\sync_pdv\test_cliente_pull_inventario.py`

**Interfaces:**
- Produces: `TransporteSync.pull_inventario(ubicacion_id, desde) -> dict`; `ClienteSync.sincronizar()` — tras el push y el pull de catálogo, por cada ubicación local conocida baja el delta desde su cursor (`sync_cursor['inventario:<id>']`), lo aplica (append + flip) y avanza el cursor con el `cursor` de la respuesta.

- [ ] **Step 1: Test que falla** — transporte fake devuelve 2 movimientos; `sincronizar` los aplica y avanza el cursor; segunda llamada con `desde` = cursor no reaplica.

- [ ] **Step 2: Ejecutar — falla.**

- [ ] **Step 3: Implementar** — añade `pull_inventario` al `Protocol` y a `TransporteHTTP` (`GET /sync/inventario?ubicacion_id&desde`); en `ClienteSync` inyecta el repo de movimientos + la lista de ubicaciones locales; itera cursor→aplicar→guardar cursor.

- [ ] **Step 4: Ejecutar — pasa.**

- [ ] **Step 5: Commit**

```
feat(pos): ClienteSync baja delta de inventario por ubicacion y aplica append+flip
```

---

### Task NUBE2B.9: El POS (admin) registra movimientos → outbox

**Files:**
- Modify: `w:\POS\src\sync_pdv\outbox.py`
- Modify: `w:\POS\src\caja\pantalla_inventario.py`
- Test: `w:\POS\tests\sync_pdv\test_serializar_movimiento.py`

**Interfaces:**
- Produces: `serializar_movimiento(mov: dict, almacen_id, local_id) -> EventoSync` (tipo `movimiento_inventario`); la UI del admin en el POS registra entrada/salida/ajuste/traslado/confirmación/conversión (usando `core.servicio_inventario_ubicaciones` para armar los movimientos) y encola cada uno. El push existente los sube (materializados en NUBE2B.6).

- [ ] **Step 1: Test que falla** — `serializar_movimiento({...})` produce `tipo=="movimiento_inventario"`, cantidad como str, incluye `origen_id`/`destino_id`/`estado`/`grupo_uuid`/`actualizado_en`.

- [ ] **Step 2: Ejecutar — falla.**

- [ ] **Step 3: Implementar** el serializador (patrón `serializar_venta`) + cablear en `pantalla_inventario.py`: al confirmar una operación, arma los movimientos con core, los registra localmente (repo de ubicaciones) y los encola. Confirmación de traslado entrante desde la bandeja del POS = flip local + evento con `estado='confirmado'`. Nuevo permiso `ACCION_GESTIONAR_INVENTARIO`/`ACCION_CONFIRMAR_TRASLADO` en `core/permisos.py` (añádelos a `PERMISOS_ADMIN`).

- [ ] **Step 4: Ejecutar — pasa** + suite POS verde.

- [ ] **Step 5: Commit**

```
feat(pos): admin registra movimientos de inventario (permiso admin) y los encola al outbox
```

---

### Task NUBE2B.10: UI web de inventario (React, admin)

**Files:**
- Create: `w:\pos-plataforma-web\frontend\src\inventario\Inventario.tsx`, `frontend\src\inventario\BandejaPendientes.tsx`
- Modify: `frontend\src\App.tsx` (pestaña Inventario)
- Test: manual (sin runner).

**Interfaces:**
- Consumes: `apiGet`/`apiPost`, endpoints `/inventario/*`.
- Produces: formularios de entrada/salida/ajuste; crear traslado (origen/destino, incl. cross-local); **bandeja de traslados pendientes** por ubicación con botón "Confirmar" (`POST /inventario/confirmar`); vista de **stock por ubicación** (`GET /inventario/stock`); conversión (1 origen → N destinos, solo cantidades).

- [ ] **Step 1:** Escribir `Inventario.tsx` (selector de ubicación + operaciones) y `BandejaPendientes.tsx` (lista + confirmar). Reusa estilo del dashboard.
- [ ] **Step 2:** Enlazar la pestaña Inventario en `App.tsx`.
- [ ] **Step 3:** Build + lint: `npm run build && npx oxlint` → OK.
- [ ] **Step 4: Commit**

```
feat(frontend): UI web de inventario (operaciones, bandeja de pendientes, stock por ubicacion)
```

---

### Task NUBE2B.11: Verificación e2e de la Ola B + cierre NUBE2

**Files:**
- Modify: `w:\POS\docs\README-pos.md` (fila NUBE2 → ✅ implementado).

- [ ] **Step 1:** Backend + frontend + dos POS (o simular local A y local B con dos `LOCAL_ID`). Sembrar ubicaciones (local A, local B, una bodega compartida).
- [ ] **Step 2:** Registrar una **entrada** en la bodega (web); confirmar stock por ubicación en la web y en Supabase (MCP).
- [ ] **Step 3:** Crear un **traslado cross-local** (local A → local B). Verificar: sale de A (confirmado), entra a B **pendiente**. El POS de B baja el delta y muestra el traslado en su **bandeja de pendientes**.
- [ ] **Step 4:** Confirmar el traslado (en la web o en el POS de B). Verificar el flip `pendiente→confirmado`, que se propaga por el cursor, y que el **stock por ubicación** de B sube en ambos lados.
- [ ] **Step 5:** Probar una **conversión** (1 salida → N entradas, con merma) y un **ajuste**. Confirmar stock.
- [ ] **Step 6:** Correr ambas suites: `cd w:\POS && python -m pytest -q` (≥420) y `cd w:\pos-plataforma-web\backend && .venv\Scripts\python -m pytest -q`. Actualizar la fila NUBE2 en `README-pos.md` a ✅. **Commit** `docs: cierra NUBE2 (catalogo + inventario multi-ubicacion) en README`.

> **No** hagas merge ni push. Reporta al usuario qué se implementó y cómo se verificó cada ola.

---

## Self-Review (hecho por el autor del plan)

**Cobertura del spec:**
- §3.1 catálogo maestro+overlay+promos → NUBE2A.1 (schema), A.5 (gestión), A.6 (push). Impuesto global (decisión 1) y costo en ambas (decisión 2) reflejados en A.1/A.5.
- §3.2 ubicaciones + movimientos append-only + flip → NUBE2B.1 (schema), B.3 (core), B.4/B.6 (backend). Flip mismo-fila (decisión 3) en B.4/B.6/B.7.
- §4 sync híbrido: catálogo snapshot (A.3, A.8, A.9) + inventario delta por cursor (B.5, B.8); push ampliado (A.6, B.6); idempotencia/LWW (A.2, A.6).
- §5 operaciones (entrada/salida/ajuste/traslado+confirmación/conversión) → B.3 (core), B.4 (backend), B.9 (POS). Permiso `ACCION_GESTIONAR_INVENTARIO`/`ACCION_CONFIRMAR_TRASLADO` → B.9.
- §6 roles/UI: `admin_web` (A.4); UI web catálogo (A.12) e inventario (B.10); edición desde POS (A.11, B.9).
- §7 dos olas verificables → estructura A/B con verificación e2e (A.13, B.11).
- §8 reconciliación (bidireccional, ubicaciones compartidas, conversión sin costeo) → aplicada en A.11/B.9, B.1, B.3.
- §9 pruebas: core (A.2, B.3), backend patrón test_dashboard (A.3/A.5/A.6/B.4/B.5/B.6), frontend manual, e2e real (A.13, B.11).
- §10 impacto POS: réplica RO (A.7/A.8), venta desde réplica (A.10), pull en HiloSincronizacion (A.9, B.8), edición→outbox (A.11, B.9).
- §11 riesgos: migración almacenes→ubicaciones (B.1/B.2), cursor por ubicación (B.7/B.8), RLS diferido (fuera de alcance, documentado).

**Placeholders:** sin "TBD/etc". Los tests de UI (A.12, B.10) son manuales por ausencia de runner — declarado explícitamente, no se reclama cobertura inexistente.

**Consistencia de tipos:** `gana_escritura(entrante, existente)` (A.2) usada conceptualmente en A.6/B.6; `stock_por_suma`/`plan_traslado`/`plan_conversion` (B.3) reusadas en B.4/B.7; `aplicar_catalogo`/`precio_de` (A.8) usadas en A.9/A.10; `pull_catalogo`/`pull_inventario` (A.9/B.8) consistentes en `TransporteSync` y `TransporteHTTP`; `movimiento_inventario` payload idéntico entre B.6 (materializar) y B.9 (serializar).

## Notas de riesgo para el ejecutor

- **NUBE2A.10 es la tarea más invasiva del POS** (leer precio de la réplica en la venta). Acótala a un resolutor `precio_venta(producto_id)` réplica→fallback; no reescribas la pantalla de venta. Si crece, córtala y pregunta.
- **UI del admin en el POS (A.11, B.9):** si el CRUD crece, limita el POS a "importar/editar precio local" (catálogo) y "registrar/confirmar movimiento" (inventario) — lo que exige el e2e — y deja el CRUD completo del maestro para la web.
- **Nunca** apuntes `TEST_DB_URL` a la BD real (la fixture hace `DROP SCHEMA public CASCADE`). Usa un branch de prueba de Supabase (MCP `create_branch`).
