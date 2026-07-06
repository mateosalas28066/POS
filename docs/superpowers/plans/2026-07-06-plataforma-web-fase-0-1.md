# Plataforma web multi-local — Fase 0 + Fase 1 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Levantar los cimientos de la plataforma nube (paquete `core` compartido, backend FastAPI + Supabase con `almacen_id` transversal, shell React con auth) y una primera demo: el POS empuja ventas por outbox a `/sync/push` idempotente y la web muestra un dashboard de reportes multi-bodega.

**Architecture:** El POS local (SQLite, offline-first) encola eventos append-only en una **outbox** y los sube al reconectar. El **backend FastAPI reusa el paquete `core`** (misma lógica de negocio que el POS, sin duplicar) y persiste en **Supabase Postgres** con `almacen_id` transversal. El **dashboard React** (Vercel) lee endpoints de agregación que reusan `ServicioReportes` de `core`, instanciado por almacén (el `almacen_id` vive solo en el `WHERE` de los repos Postgres; `core` no se toca). Auth: Supabase Auth (JWT) para la web; token de servicio por local para el POS.

**Tech Stack:** Python 3.11+ · FastAPI · Uvicorn · psycopg (v3) · Supabase (Postgres + Auth) · pytest · React + Vite + TypeScript · Recharts · Vercel · `core` (paquete `pos-core` extraído de `w:\POS`).

## Global Constraints

- **Ponytail (mínimo código necesario):** YAGNI, stdlib/nativo primero, sin dependencias que la stdlib cubra. No implementar Fases 2-4 (bodegas/conversión/traslado, compras/cuentas/CRM, adelgazar POS).
- **Aislamiento hexagonal (no negociable):** `core/` NO conoce Qt, SQLite ni Postgres. `almacen_id` vive en los adaptadores de repositorio (WHERE), nunca en `core`. Prohibido SQL fuera de los adaptadores de repositorio.
- **`core` sin duplicar:** una sola fuente en `w:\POS`. El backend lo consume vía `pip install` (editable local, `git+url@commit` en deploy). Nunca copiar/editar `core` en el repo web.
- **Import namespace = `core`** (no `pos_core`): la distribución se llama `pos-core` pero el paquete de import sigue siendo `core`, para no tocar los cientos de `from core.X import` del POS y mantener la suite verde. (Renombrar el namespace a `pos_core` queda diferido — YAGNI.)
- **Dinero/cantidades como texto exacto (`Decimal`), nunca float.** En Postgres: `NUMERIC`; al leer, convertir a `Decimal`. En JSON de sync: strings.
- **Idempotencia por `uuid`:** todo evento de sync lleva `uuid + local_id + timestamp`; el backend hace UPSERT por `uuid` → reenviar es inocuo.
- **Esquema Postgres nace con `almacen_id`** para no re-migrar (spec §5, riesgo §2).
- **Migraciones versionadas** en ambos lados: SQLite (`scripts/migraciones/NNN_*.sql`, runner existente) y Postgres (`backend/migraciones/NNN_*.sql`, runner nuevo).
- **Git:** rama `feature/plataforma-web-fase-0-1` en `w:\POS`; repo nuevo `w:\pos-plataforma-web` (con su propio git). Commits pequeños en español. **No merge ni push sin preguntar.**
- **IDs de task:** prefijos `NUBE0.*` (Fase 0) y `NUBE1.*` (Fase 1), únicos (no colisionan con `E1..E8`, `USUARIOS`, `CLIENTE`, `CIERRE`, `PROMO`, `CONTEO`). En TodoWrite usar el ID con prefijo completo.

---

## Prerrequisitos de ejecución (confirmar antes de empezar; no son código)

Estos existen fuera del repo; confírmalos con el usuario cuando la task los necesite (no los cablees con secretos en el repo):

- **Proyecto Supabase** creado (free tier). Necesitas: `SUPABASE_DB_URL` (cadena de conexión Postgres para migraciones/backend), `SUPABASE_URL` y `SUPABASE_ANON_KEY` (frontend), `SUPABASE_JWT_SECRET` o el JWKS del proyecto (backend, para verificar el JWT de la web).
- **Cuenta Vercel** (para desplegar el frontend). No se despliega en este plan sin preguntar.
- **Host del backend** (Render/Railway/Fly) — solo se decide/despliega al cerrar, previa pregunta.
- Variables de entorno del backend en `.env` (NO commiteado; `.env.example` sí): `SUPABASE_DB_URL`, `SUPABASE_JWT_SECRET`, `LOCAL_TOKENS` (o tabla `locales`).
- Variables del POS para sync (en config local, no en git): `SYNC_URL`, `LOCAL_ID`, `LOCAL_TOKEN`, `ALMACEN_ID`.

---

## File Structure

### En `w:\POS` (repo actual)

- `pyproject.toml` — **crear.** Empaqueta la distribución `pos-core` (import `core`), src-layout. Responsabilidad: hacer `core` instalable por el backend sin arrastrar `inventario`/`ventas`/`caja`.
- `scripts/migraciones/011_outbox.sql` — **crear.** Tabla `eventos_sync` (outbox local).
- `src/sync_pdv/outbox.py` — **crear.** `RepositorioOutboxSQLite` (encolar/pendientes/marcar_enviado) + `serializar_venta(venta, pagos, almacen_id, local_id) -> dict`.
- `src/sync_pdv/cliente.py` — **crear.** `ClienteSync` (lee pendientes, hace POST a `/sync/push`, marca enviados) + puerto `TransporteSync` (para test con fake).
- `src/core/servicio_venta.py` — **modificar.** Añadir `ServicioRegistroVentaConOutbox` (decorador que registra y luego encola). (Vive en `core` porque solo depende de un puerto `RepositorioOutbox`, sin transporte.)
- `src/core/puertos.py` — **modificar.** Añadir `Protocol` `RepositorioOutbox`.
- `src/caja/contexto.py` — **modificar.** Cablear outbox si hay config de sync (opcional; no rompe modo offline puro).
- Tests espejo en `tests/sync_pdv/`, `tests/core/`.

### En `w:\pos-plataforma-web` (repo nuevo)

```
pos-plataforma-web/
├─ backend/
│  ├─ pyproject.toml            # deps: fastapi, uvicorn, psycopg[binary], pyjwt, pos-core (editable/-git)
│  ├─ .env.example
│  ├─ app/
│  │  ├─ __init__.py
│  │  ├─ main.py                # FastAPI app, routers, /health
│  │  ├─ config.py              # Settings desde entorno (pydantic o os.environ)
│  │  ├─ db.py                  # pool psycopg + registro Decimal
│  │  ├─ migraciones_runner.py  # aplica backend/migraciones/*.sql (patrón del POS)
│  │  ├─ auth.py                # deps: usuario_web (JWT Supabase) y local_autenticado (token servicio)
│  │  ├─ repos_pg.py            # RepositorioVentasPG, PagosPG, DevolucionesPG, ProductosPG... (puertos core) + WHERE almacen_id
│  │  ├─ sync.py                # router /sync/push (idempotente por uuid)
│  │  └─ dashboard.py           # router /dashboard/* (reusa ServicioReportes por almacén)
│  ├─ migraciones/
│  │  ├─ 001_locales_almacenes.sql
│  │  ├─ 002_catalogo.sql       # productos, categorias, medios_pago, usuarios (cajeros)
│  │  ├─ 003_ventas.sql         # caja_sesiones, ventas, venta_lineas, pagos, devoluciones (+almacen_id)
│  │  └─ 004_eventos_sync.sql   # ledger idempotencia server-side
│  └─ tests/
│     ├─ conftest.py            # fixture de conexión a Postgres de test (o testcontainers/local)
│     ├─ test_health.py
│     ├─ test_migraciones.py
│     ├─ test_auth.py
│     ├─ test_sync_push.py
│     └─ test_dashboard.py
└─ frontend/
   ├─ package.json              # react, vite, typescript, @supabase/supabase-js, recharts
   ├─ .env.example
   ├─ index.html
   └─ src/
      ├─ main.tsx
      ├─ supabase.ts            # cliente Supabase (auth)
      ├─ api.ts                 # fetch a backend con Bearer token
      ├─ auth/Login.tsx
      ├─ App.tsx                # layout + guard de sesión
      └─ dashboard/
         ├─ Dashboard.tsx       # orquesta llamadas y layout de gráficas
         ├─ charts.ts           # paleta y helpers de formato
         └─ components/         # KpiCard, VentasPorAlmacen, PorCajero, PorCategoria
```

---

# FASE 0 — Cimientos (epic NUBE0)

## Task NUBE0.1: Empaquetar `core` como distribución `pos-core` (`w:\POS/pyproject.toml`)

**Objetivo:** que el backend pueda `pip install` el paquete `core` desde `w:\POS` sin arrastrar `inventario`/`ventas`/`caja`, manteniendo la suite del POS verde.

**Files:**
- Create: `w:\POS\pyproject.toml`
- Test: `w:\POS\tests\test_empaquetado_core.py`

**Interfaces:**
- Produces: distribución `pos-core`, import package `core` (incluye `core.perifericos`). Instalable con `pip install -e w:\POS`.

- [ ] **Step 1: Crear la rama de trabajo y commitear el spec si falta**

```bash
cd /w/POS
git checkout -b feature/plataforma-web-fase-0-1
git add docs/superpowers/specs/2026-07-06-plataforma-web-multi-local-design.md docs/estado-actual-y-brechas.md
git commit -m "docs: spec plataforma web multi-local + auditoria estado actual"
```

- [ ] **Step 2: Escribir el test que verifica que `core` es instalable/aislado**

`tests/test_empaquetado_core.py`:

```python
"""core debe ser importable como paquete aislado (sin depender de inventario/ventas)."""
import ast
import tomllib
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def test_pyproject_declara_pos_core():
    data = tomllib.loads((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["name"] == "pos-core"
    paquetes = data["tool"]["setuptools"]["packages"]["find"]["include"]
    assert "core*" in paquetes  # solo core (+ subpaquetes), no inventario/ventas/caja


def test_core_no_importa_capas_externas():
    """Regla hexagonal: core no importa inventario/ventas/caja/facturacion_dian."""
    prohibido = {"inventario", "ventas", "caja", "facturacion_dian", "sync_pdv"}
    for py in (RAIZ / "src" / "core").rglob("*.py"):
        arbol = ast.parse(py.read_text(encoding="utf-8"))
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.ImportFrom) and nodo.module:
                raiz = nodo.module.split(".")[0]
                assert raiz not in prohibido, f"{py.name} importa {nodo.module}"
```

- [ ] **Step 3: Correr el test para verlo fallar**

Run: `python -m pytest tests/test_empaquetado_core.py -v`
Expected: FAIL en `test_pyproject_declara_pos_core` (no existe `pyproject.toml`).

- [ ] **Step 4: Crear `pyproject.toml`**

`w:\POS\pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "pos-core"
version = "0.1.0"
description = "Dominio compartido del POS (entidades, servicios, reglas puras) — pos-siesa-remake"
requires-python = ">=3.11"
dependencies = []          # core solo usa stdlib

[tool.setuptools]
package-dir = {"" = "src"}

[tool.setuptools.packages.find]
where = ["src"]
include = ["core*"]        # empaqueta SOLO core y core.perifericos
```

- [ ] **Step 5: Instalar en modo editable y correr ambos tests + la suite completa**

Run:
```bash
cd /w/POS && pip install -e .
python -m pytest tests/test_empaquetado_core.py -v
python -m pytest -q
```
Expected: los 2 tests nuevos PASS; suite completa en verde (395+ passed) — `pip install -e .` no cambia `pythonpath=src`, así que el POS sigue igual.

- [ ] **Step 6: Verificar import limpio en un intérprete aislado**

Run: `cd /tmp && python -c "import core.calculos, core.servicio_reportes, core.perifericos.gs1; print('ok')"`
Expected: `ok` (importable fuera de `w:\POS` gracias al editable install).

- [ ] **Step 7: Commit**

```bash
cd /w/POS && git add pyproject.toml tests/test_empaquetado_core.py
git commit -m "feat(core): empaquetar core como distribucion instalable pos-core"
```

---

## Task NUBE0.2: Scaffold repo `pos-plataforma-web` + backend FastAPI mínimo (`/health`)

**Objetivo:** repo nuevo con backend que levanta, reusa `pos-core`, y responde `/health`.

**Files (en `w:\pos-plataforma-web`):**
- Create: `backend/pyproject.toml`, `backend/.env.example`, `backend/app/__init__.py`, `backend/app/config.py`, `backend/app/main.py`
- Test: `backend/tests/test_health.py`, `backend/tests/conftest.py`
- Create: `.gitignore`, `README.md`

**Interfaces:**
- Produces: `app.main:app` (FastAPI), `GET /health -> {"status": "ok", "core": "<version>"}`; `Settings` con campos de entorno.

- [ ] **Step 1: Crear repo y estructura base**

```bash
mkdir -p /w/pos-plataforma-web/backend/app /w/pos-plataforma-web/backend/tests
cd /w/pos-plataforma-web && git init
printf "__pycache__/\n*.pyc\n.env\n.venv/\nnode_modules/\ndist/\n" > .gitignore
```

- [ ] **Step 2: `backend/pyproject.toml` (deps + dependencia a pos-core editable local)**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "pos-plataforma-web-backend"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "fastapi>=0.110",
  "uvicorn[standard]>=0.27",
  "psycopg[binary]>=3.1",
  "pyjwt[crypto]>=2.8",
  "httpx>=0.27",            # tests (TestClient) y utilidades
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

# En LOCAL: pip install -e ../../POS  (pos-core editable)
# En DEPLOY: se fija en requirements con  pos-core @ git+<url_POS>@<commit>
```

`backend/.env.example`:
```
SUPABASE_DB_URL=postgresql://postgres:...@db.<proj>.supabase.co:5432/postgres
SUPABASE_JWT_SECRET=replace-me
LOCAL_TOKENS=local-01:token-secreto-01
```

- [ ] **Step 3: Escribir el test de `/health` (falla primero)**

`backend/tests/conftest.py`:
```python
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture()
def client():
    return TestClient(app)
```

`backend/tests/test_health.py`:
```python
def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["status"] == "ok"
    assert "core" in cuerpo            # confirma que pos-core está importado
```

- [ ] **Step 4: Instalar deps + pos-core editable y correr el test (debe fallar)**

```bash
cd /w/pos-plataforma-web/backend
python -m venv .venv && . .venv/Scripts/activate   # Windows Git Bash
pip install -e ".[dev]"
pip install -e ../../POS                             # pos-core
python -m pytest -q
```
Expected: FAIL (no existe `app.main`).

- [ ] **Step 5: Implementar `config.py` y `main.py`**

`backend/app/config.py`:
```python
"""Configuración desde entorno. Ponytail: os.environ, sin dependencias extra."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    db_url: str = os.environ.get("SUPABASE_DB_URL", "")
    jwt_secret: str = os.environ.get("SUPABASE_JWT_SECRET", "")
    # "local-01:tok1,local-02:tok2" -> {"local-01": "tok1", ...}
    local_tokens: dict[str, str] = None  # type: ignore[assignment]

    @staticmethod
    def cargar() -> "Settings":
        crudo = os.environ.get("LOCAL_TOKENS", "")
        tokens = dict(par.split(":", 1) for par in crudo.split(",") if ":" in par)
        return Settings(
            db_url=os.environ.get("SUPABASE_DB_URL", ""),
            jwt_secret=os.environ.get("SUPABASE_JWT_SECRET", ""),
            local_tokens=tokens,
        )


settings = Settings.cargar()
```

`backend/app/main.py`:
```python
from importlib.metadata import version

from fastapi import FastAPI

app = FastAPI(title="pos-plataforma-web")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "core": version("pos-core")}
```

- [ ] **Step 6: Correr el test (pasa) y levantar el server manualmente**

```bash
python -m pytest -q
uvicorn app.main:app --reload &   # verificar http://127.0.0.1:8000/health
```
Expected: test PASS; `curl 127.0.0.1:8000/health` → `{"status":"ok","core":"0.1.0"}`.

- [ ] **Step 7: Commit (repo web)**

```bash
cd /w/pos-plataforma-web
git add .gitignore backend/pyproject.toml backend/.env.example backend/app backend/tests
git commit -m "feat(backend): scaffold FastAPI + /health reusando pos-core"
```

---

## Task NUBE0.3: Esquema Supabase Postgres con `almacen_id` transversal + runner de migraciones

**Objetivo:** esquema Postgres versionado que nace con `almacen_id`, aplicable de forma idempotente.

**Files:**
- Create: `backend/app/db.py`, `backend/app/migraciones_runner.py`
- Create: `backend/migraciones/001_locales_almacenes.sql`, `002_catalogo.sql`, `003_ventas.sql`, `004_eventos_sync.sql`
- Test: `backend/tests/test_migraciones.py`

**Interfaces:**
- Consumes: `settings.db_url` (NUBE0.2).
- Produces: `conectar()` / `pool` (psycopg conn), `aplicar_migraciones(conn)`; tablas `locales, almacenes, categorias, productos, medios_pago, usuarios, caja_sesiones, ventas, venta_lineas, pagos, devoluciones, devolucion_lineas, eventos_sync` — todas las transaccionales con `almacen_id`.

- [ ] **Step 1: Escribir el test de migraciones (falla primero)**

`backend/tests/test_migraciones.py`:
```python
import os
import psycopg
import pytest

from app.migraciones_runner import aplicar_migraciones

DB = os.environ.get("TEST_DB_URL")  # p.ej. postgresql://postgres:postgres@localhost:5432/pos_test


@pytest.fixture()
def conn():
    if not DB:
        pytest.skip("TEST_DB_URL no configurada")
    c = psycopg.connect(DB)
    c.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
    c.commit()
    yield c
    c.close()


def _columnas(conn, tabla):
    filas = conn.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name=%s", (tabla,)
    ).fetchall()
    return {f[0] for f in filas}


def test_almacen_id_transversal(conn):
    aplicar_migraciones(conn)
    for tabla in ("ventas", "venta_lineas", "pagos", "caja_sesiones", "inventario_movimientos"):
        assert "almacen_id" in _columnas(conn, tabla), f"falta almacen_id en {tabla}"


def test_migraciones_idempotentes(conn):
    aplicar_migraciones(conn)
    aplicar_migraciones(conn)  # segunda pasada no debe fallar ni duplicar
    n = conn.execute("SELECT count(*) FROM schema_migraciones").fetchone()[0]
    assert n >= 4
```

- [ ] **Step 2: Correr el test (falla)**

Run: `TEST_DB_URL=postgresql://postgres:postgres@localhost:5432/pos_test python -m pytest tests/test_migraciones.py -v`
Expected: FAIL (no existe `app.migraciones_runner`). Si no hay Postgres local, el test hace `skip` — levantar uno con `docker run -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d postgres:16` para no saltarlo.

- [ ] **Step 3: `db.py` (conexión + Decimal)**

`backend/app/db.py`:
```python
"""Único lugar con detalles de psycopg. Dinero como NUMERIC -> Decimal."""
from __future__ import annotations

import psycopg

from app.config import settings


def conectar(db_url: str | None = None) -> psycopg.Connection:
    conn = psycopg.connect(db_url or settings.db_url)
    return conn
```
(psycopg v3 ya devuelve `Decimal` para `NUMERIC` por defecto — no hace falta registro extra.)

- [ ] **Step 4: `migraciones_runner.py` (patrón del POS, adaptado a Postgres)**

`backend/app/migraciones_runner.py`:
```python
"""Aplica backend/migraciones/*.sql en orden, registrando en schema_migraciones."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import psycopg

DIR_MIGRACIONES = Path(__file__).resolve().parents[1] / "migraciones"


def aplicar_migraciones(conn: psycopg.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migraciones ("
        "archivo TEXT PRIMARY KEY, aplicada_en TIMESTAMPTZ NOT NULL)")
    conn.commit()
    aplicadas = {r[0] for r in conn.execute("SELECT archivo FROM schema_migraciones")}
    for archivo in sorted(DIR_MIGRACIONES.glob("*.sql")):
        if archivo.name in aplicadas:
            continue
        conn.execute(archivo.read_text(encoding="utf-8"))
        conn.execute(
            "INSERT INTO schema_migraciones (archivo, aplicada_en) VALUES (%s, %s)",
            (archivo.name, datetime.now(timezone.utc)))
        conn.commit()
```

- [ ] **Step 5: Escribir las 4 migraciones SQL**

`backend/migraciones/001_locales_almacenes.sql`:
```sql
CREATE TABLE locales (
  local_id   TEXT PRIMARY KEY,
  nombre     TEXT NOT NULL,
  token_hash TEXT NOT NULL,          -- hash del token de servicio (no el token en claro)
  activo     BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE almacenes (
  id       BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  nombre   TEXT NOT NULL,
  local_id TEXT NOT NULL REFERENCES locales(local_id),
  activo   BOOLEAN NOT NULL DEFAULT TRUE
);
```

`backend/migraciones/002_catalogo.sql` (réplica del catálogo que sube el POS; maestro futuro será la nube, aquí basta para el dashboard):
```sql
CREATE TABLE categorias (
  id     BIGINT PRIMARY KEY,           -- id espejo del POS
  nombre TEXT NOT NULL
);

CREATE TABLE productos (
  id           BIGINT PRIMARY KEY,     -- id espejo del POS
  nombre       TEXT NOT NULL,
  categoria_id BIGINT REFERENCES categorias(id)
);

CREATE TABLE medios_pago (
  id     BIGINT PRIMARY KEY,
  nombre TEXT NOT NULL
);

CREATE TABLE usuarios (               -- cajeros (dimensión "por cajero")
  id       BIGINT PRIMARY KEY,
  nombre   TEXT NOT NULL,
  local_id TEXT REFERENCES locales(local_id)
);
```

`backend/migraciones/003_ventas.sql` (**almacen_id transversal**):
```sql
CREATE TABLE caja_sesiones (
  id            BIGINT NOT NULL,
  local_id      TEXT NOT NULL REFERENCES locales(local_id),
  almacen_id    BIGINT NOT NULL REFERENCES almacenes(id),
  usuario_id    BIGINT,
  abierta_en    TIMESTAMPTZ,
  cerrada_en    TIMESTAMPTZ,
  PRIMARY KEY (local_id, id)
);

CREATE TABLE inventario_movimientos (
  uuid        UUID PRIMARY KEY,
  local_id    TEXT NOT NULL REFERENCES locales(local_id),
  almacen_id  BIGINT NOT NULL REFERENCES almacenes(id),
  producto_id BIGINT NOT NULL,
  tipo        TEXT NOT NULL,           -- entrada | salida
  cantidad    NUMERIC NOT NULL,
  fecha       TIMESTAMPTZ NOT NULL
);

CREATE TABLE ventas (
  uuid            UUID PRIMARY KEY,     -- idempotencia por evento
  id              BIGINT NOT NULL,      -- id local (para trazas)
  local_id        TEXT NOT NULL REFERENCES locales(local_id),
  almacen_id      BIGINT NOT NULL REFERENCES almacenes(id),
  usuario_id      BIGINT,
  cliente_id      BIGINT,
  sesion_id       BIGINT,
  fecha           TIMESTAMPTZ NOT NULL,
  total           NUMERIC NOT NULL,
  total_impuestos NUMERIC NOT NULL,
  estado          TEXT NOT NULL DEFAULT 'confirmada'
);

CREATE TABLE venta_lineas (
  venta_uuid   UUID NOT NULL REFERENCES ventas(uuid) ON DELETE CASCADE,
  almacen_id   BIGINT NOT NULL REFERENCES almacenes(id),
  producto_id  BIGINT NOT NULL,
  cantidad     NUMERIC NOT NULL,
  subtotal     NUMERIC NOT NULL,
  impuesto     NUMERIC NOT NULL,
  PRIMARY KEY (venta_uuid, producto_id)
);

CREATE TABLE pagos (
  venta_uuid    UUID NOT NULL REFERENCES ventas(uuid) ON DELETE CASCADE,
  almacen_id    BIGINT NOT NULL REFERENCES almacenes(id),
  medio_pago_id BIGINT NOT NULL,
  monto         NUMERIC NOT NULL
);

CREATE TABLE devoluciones (
  uuid            UUID PRIMARY KEY,
  venta_uuid      UUID REFERENCES ventas(uuid),
  local_id        TEXT NOT NULL REFERENCES locales(local_id),
  almacen_id      BIGINT NOT NULL REFERENCES almacenes(id),
  usuario_id      BIGINT,
  sesion_id       BIGINT,
  fecha           TIMESTAMPTZ NOT NULL,
  total           NUMERIC NOT NULL,
  total_impuestos NUMERIC NOT NULL
);

CREATE INDEX ix_ventas_alm_fecha ON ventas (almacen_id, fecha);
CREATE INDEX ix_pagos_venta ON pagos (venta_uuid);
```

`backend/migraciones/004_eventos_sync.sql` (ledger server-side de idempotencia + payload crudo para auditoría/reprocesamiento):
```sql
CREATE TABLE eventos_sync (
  uuid        UUID PRIMARY KEY,
  local_id    TEXT NOT NULL REFERENCES locales(local_id),
  tipo        TEXT NOT NULL,            -- venta | pago | movimiento_inventario | ...
  payload     JSONB NOT NULL,
  recibido_en TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

- [ ] **Step 6: Correr el test (pasa)**

Run: `TEST_DB_URL=postgresql://postgres:postgres@localhost:5432/pos_test python -m pytest tests/test_migraciones.py -v`
Expected: `test_almacen_id_transversal` y `test_migraciones_idempotentes` PASS.

- [ ] **Step 7: Commit**

```bash
cd /w/pos-plataforma-web
git add backend/app/db.py backend/app/migraciones_runner.py backend/migraciones backend/tests/test_migraciones.py
git commit -m "feat(backend): esquema Postgres con almacen_id transversal + runner de migraciones"
```

---

## Task NUBE0.4: Identidad de local (`local_id` + token) y auth (JWT Supabase) como deps FastAPI

**Objetivo:** dos dependencias de auth reusables: `local_autenticado` (token de servicio por local, para el POS) y `usuario_web` (JWT de Supabase, para la web). Un endpoint protegido de prueba demuestra ambos caminos.

**Files:**
- Create: `backend/app/auth.py`
- Modify: `backend/app/main.py` (registrar router de prueba `/whoami`)
- Test: `backend/tests/test_auth.py`

**Interfaces:**
- Consumes: `settings.jwt_secret`, `settings.local_tokens` (NUBE0.2).
- Produces:
  - `local_autenticado(authorization: str = Header) -> str` → devuelve `local_id` o lanza `HTTPException(401)`. Valida `Authorization: Bearer <local_id>:<token>` contra `settings.local_tokens`.
  - `usuario_web(authorization: str = Header) -> dict` → verifica JWT HS256 con `settings.jwt_secret`, devuelve el claim `sub`/`email` o `HTTPException(401)`.

- [ ] **Step 1: Escribir el test de auth (falla primero)**

`backend/tests/test_auth.py`:
```python
import jwt
from fastapi.testclient import TestClient

from app.config import Settings
import app.auth as auth_mod
from app.main import app

client = TestClient(app)


def _set_settings(monkeypatch, **kw):
    s = Settings(db_url="", jwt_secret=kw.get("jwt_secret", "sec"),
                 local_tokens=kw.get("local_tokens", {"local-01": "tok1"}))
    monkeypatch.setattr(auth_mod, "settings", s)


def test_whoami_local_ok(monkeypatch):
    _set_settings(monkeypatch)
    r = client.get("/whoami", headers={"Authorization": "Bearer local-01:tok1"})
    assert r.status_code == 200 and r.json()["local_id"] == "local-01"


def test_whoami_local_token_invalido(monkeypatch):
    _set_settings(monkeypatch)
    r = client.get("/whoami", headers={"Authorization": "Bearer local-01:malo"})
    assert r.status_code == 401


def test_whoami_web_jwt_ok(monkeypatch):
    _set_settings(monkeypatch)
    token = jwt.encode({"sub": "u1", "email": "a@b.co"}, "sec", algorithm="HS256")
    r = client.get("/whoami/web", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200 and r.json()["email"] == "a@b.co"
```

- [ ] **Step 2: Correr el test (falla)**

Run: `python -m pytest tests/test_auth.py -v`
Expected: FAIL (no existe `/whoami`).

- [ ] **Step 3: Implementar `auth.py`**

`backend/app/auth.py`:
```python
"""Dos vías de auth: token de servicio por local (POS) y JWT de Supabase (web)."""
from __future__ import annotations

import hmac

import jwt
from fastapi import Header, HTTPException, status

from app.config import settings


def _bearer(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "falta bearer token")
    return authorization[len("Bearer "):]


def local_autenticado(authorization: str | None = Header(default=None)) -> str:
    """Authorization: Bearer <local_id>:<token>. Devuelve local_id o 401."""
    credencial = _bearer(authorization)
    local_id, _, token = credencial.partition(":")
    esperado = settings.local_tokens.get(local_id)
    if not esperado or not hmac.compare_digest(esperado, token):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "local o token inválido")
    return local_id


def usuario_web(authorization: str | None = Header(default=None)) -> dict:
    """Verifica el JWT de Supabase (HS256 con el JWT secret del proyecto)."""
    token = _bearer(authorization)
    try:
        claims = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"],
                            options={"verify_aud": False})
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "jwt inválido")
    return {"sub": claims.get("sub"), "email": claims.get("email")}
```

- [ ] **Step 4: Registrar endpoints de prueba en `main.py`**

Modificar `backend/app/main.py` (añadir):
```python
from fastapi import Depends

from app.auth import local_autenticado, usuario_web


@app.get("/whoami")
def whoami(local_id: str = Depends(local_autenticado)) -> dict:
    return {"local_id": local_id}


@app.get("/whoami/web")
def whoami_web(usuario: dict = Depends(usuario_web)) -> dict:
    return usuario
```

- [ ] **Step 5: Correr el test (pasa)**

Run: `python -m pytest tests/test_auth.py -v`
Expected: los 3 tests PASS.

- [ ] **Step 6: Commit**

```bash
cd /w/pos-plataforma-web
git add backend/app/auth.py backend/app/main.py backend/tests/test_auth.py
git commit -m "feat(backend): auth por token de local (POS) y JWT Supabase (web)"
```

---

## Task NUBE0.5: Shell React (Vite + TS) con login Supabase Auth

**Objetivo:** frontend que compila, con login Supabase y un layout protegido (dashboard vacío por ahora). Listo para Vercel.

**Files (en `w:\pos-plataforma-web/frontend`):**
- Create: `package.json`, `index.html`, `.env.example`, `src/main.tsx`, `src/supabase.ts`, `src/api.ts`, `src/auth/Login.tsx`, `src/App.tsx`
- Test: build (`npm run build`) como verificación.

**Interfaces:**
- Produces: `supabase` (cliente), `apiGet(path)` (fetch con Bearer del JWT de sesión), `App` (guard de sesión → Login | Dashboard placeholder).

- [ ] **Step 1: Inicializar Vite + deps**

```bash
cd /w/pos-plataforma-web/frontend
npm create vite@latest . -- --template react-ts
npm install
npm install @supabase/supabase-js recharts
```
`.env.example`:
```
VITE_SUPABASE_URL=https://<proj>.supabase.co
VITE_SUPABASE_ANON_KEY=...
VITE_API_URL=http://127.0.0.1:8000
```

- [ ] **Step 2: `src/supabase.ts` y `src/api.ts`**

`src/supabase.ts`:
```ts
import { createClient } from "@supabase/supabase-js";

export const supabase = createClient(
  import.meta.env.VITE_SUPABASE_URL,
  import.meta.env.VITE_SUPABASE_ANON_KEY,
);
```

`src/api.ts`:
```ts
import { supabase } from "./supabase";

const BASE = import.meta.env.VITE_API_URL;

export async function apiGet<T>(path: string): Promise<T> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token ?? "";
  const r = await fetch(`${BASE}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!r.ok) throw new Error(`${r.status} ${path}`);
  return r.json() as Promise<T>;
}
```

- [ ] **Step 3: `src/auth/Login.tsx`**

```tsx
import { useState } from "react";
import { supabase } from "../supabase";

export function Login() {
  const [email, setEmail] = useState("");
  const [pass, setPass] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function entrar(e: React.FormEvent) {
    e.preventDefault();
    const { error } = await supabase.auth.signInWithPassword({ email, password: pass });
    if (error) setError(error.message);
  }

  return (
    <form onSubmit={entrar} style={{ maxWidth: 320, margin: "10vh auto", display: "grid", gap: 12 }}>
      <h1>Plataforma POS</h1>
      <input placeholder="correo" value={email} onChange={(e) => setEmail(e.target.value)} />
      <input placeholder="contraseña" type="password" value={pass} onChange={(e) => setPass(e.target.value)} />
      <button type="submit">Entrar</button>
      {error && <p style={{ color: "crimson" }}>{error}</p>}
    </form>
  );
}
```

- [ ] **Step 4: `src/App.tsx` (guard de sesión) y `src/main.tsx`**

`src/App.tsx`:
```tsx
import { useEffect, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import { supabase } from "./supabase";
import { Login } from "./auth/Login";

export default function App() {
  const [session, setSession] = useState<Session | null>(null);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => setSession(data.session));
    const { data: sub } = supabase.auth.onAuthStateChange((_e, s) => setSession(s));
    return () => sub.subscription.unsubscribe();
  }, []);

  if (!session) return <Login />;
  return (
    <div style={{ padding: 24 }}>
      <header style={{ display: "flex", justifyContent: "space-between" }}>
        <h1>Dashboard</h1>
        <button onClick={() => supabase.auth.signOut()}>Salir</button>
      </header>
      <p>Sesión iniciada como {session.user.email}. (Dashboard llega en NUBE1.5.)</p>
    </div>
  );
}
```

`src/main.tsx`:
```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
```

- [ ] **Step 5: Verificar build**

Run: `cd /w/pos-plataforma-web/frontend && npm run build`
Expected: build sin errores de TS (genera `dist/`).

- [ ] **Step 6: Commit**

```bash
cd /w/pos-plataforma-web
git add frontend
git commit -m "feat(frontend): shell React + login Supabase (guard de sesion)"
```

---

# FASE 1 — Ingest del POS + dashboard multi-bodega (epic NUBE1)

## Task NUBE1.1: Outbox en el POS — tabla `eventos_sync` + `RepositorioOutboxSQLite` + serializador

**Objetivo:** persistencia local append-only de eventos pendientes de subir. Aún sin transporte.

**Files (en `w:\POS`):**
- Create: `scripts/migraciones/011_outbox.sql`
- Modify: `src/core/puertos.py` (añadir `RepositorioOutbox`)
- Create: `src/sync_pdv/outbox.py`
- Test: `tests/sync_pdv/__init__.py`, `tests/sync_pdv/test_outbox.py`

**Interfaces:**
- Produces:
  - Puerto `RepositorioOutbox` (Protocol): `encolar(evento: EventoSync) -> None`, `pendientes(limite: int = 100) -> list[EventoSync]`, `marcar_enviados(uuids: list[str]) -> None`.
  - `EventoSync` (dataclass): `uuid: str, local_id: str, tipo: str, payload: dict, creado_en: str`.
  - `RepositorioOutboxSQLite(conn)`.
  - `serializar_venta(venta: Venta, pagos: list[Pago], almacen_id: int, local_id: str) -> EventoSync` (tipo `"venta"`), con dinero como strings.

- [ ] **Step 1: Migración de outbox**

`scripts/migraciones/011_outbox.sql`:
```sql
CREATE TABLE eventos_sync (
  uuid       TEXT PRIMARY KEY,
  local_id   TEXT NOT NULL,
  tipo       TEXT NOT NULL,
  payload    TEXT NOT NULL,            -- JSON (dinero como strings)
  creado_en  TEXT NOT NULL,
  enviado_en TEXT                      -- NULL = pendiente
);
CREATE INDEX ix_eventos_sync_pendientes ON eventos_sync (enviado_en) WHERE enviado_en IS NULL;
```

- [ ] **Step 2: Escribir el test del outbox (falla primero)**

`tests/sync_pdv/test_outbox.py`:
```python
from decimal import Decimal

from inventario.db import conectar, aplicar_migraciones
from sync_pdv.outbox import EventoSync, RepositorioOutboxSQLite, serializar_venta
from core.entidades import Venta, LineaVenta, Pago


def _conn():
    c = conectar(":memory:")
    aplicar_migraciones(c)
    return c


def test_encolar_y_listar_pendientes():
    repo = RepositorioOutboxSQLite(_conn())
    ev = EventoSync(uuid="u1", local_id="local-01", tipo="venta",
                    payload={"total": "100"}, creado_en="2026-07-06T10:00:00")
    repo.encolar(ev)
    pend = repo.pendientes()
    assert [e.uuid for e in pend] == ["u1"]
    assert pend[0].payload["total"] == "100"


def test_marcar_enviados_saca_de_pendientes():
    repo = RepositorioOutboxSQLite(_conn())
    repo.encolar(EventoSync("u1", "local-01", "venta", {}, "2026-07-06T10:00:00"))
    repo.marcar_enviados(["u1"])
    assert repo.pendientes() == []


def test_serializar_venta_dinero_como_strings():
    venta = Venta(id=5, lineas=[LineaVenta(producto_id=1, cantidad_o_peso=Decimal("2"),
                  precio_unitario=Decimal("50"), impuesto_tasa=Decimal("0"))],
                  usuario_id=3, fecha="2026-07-06T10:00:00")
    ev = serializar_venta(venta, [Pago(venta_id=5, medio_pago_id=1, monto=Decimal("100"))],
                          almacen_id=7, local_id="local-01")
    assert ev.tipo == "venta"
    assert ev.payload["almacen_id"] == 7
    assert ev.payload["total"] == str(venta.total)         # string, no float
    assert ev.payload["pagos"][0]["monto"] == "100"
```

> Nota ejecutor: ajusta los kwargs de `Venta`/`LineaVenta`/`Pago` a las firmas reales en `src/core/entidades.py` (verifícalas antes; el dominio valida en `__post_init__`).

- [ ] **Step 3: Correr el test (falla)**

Run: `cd /w/POS && python -m pytest tests/sync_pdv/test_outbox.py -v`
Expected: FAIL (no existe `sync_pdv.outbox`).

- [ ] **Step 4: Añadir el puerto `RepositorioOutbox` a `core/puertos.py`**

```python
from typing import Protocol

# ... (junto a los demás Protocol)
class RepositorioOutbox(Protocol):
    def encolar(self, evento: "EventoSync") -> None: ...
    def pendientes(self, limite: int = 100) -> list["EventoSync"]: ...
    def marcar_enviados(self, uuids: list[str]) -> None: ...
```
> `EventoSync` se define en `sync_pdv/outbox.py`; para evitar dependencia inversa, en `puertos.py` usa `from __future__ import annotations` y un `TYPE_CHECKING` import, o tipa el payload como `object`. (El puerto es estructural; no requiere el import en runtime.)

- [ ] **Step 5: Implementar `sync_pdv/outbox.py`**

```python
"""Outbox local: cola SQLite de eventos append-only pendientes de subir a la nube."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from core.entidades import Pago, Venta


@dataclass(frozen=True)
class EventoSync:
    uuid: str
    local_id: str
    tipo: str
    payload: dict
    creado_en: str


class RepositorioOutboxSQLite:
    def __init__(self, conn) -> None:
        self._conn = conn

    def encolar(self, evento: EventoSync) -> None:
        self._conn.execute(
            "INSERT OR IGNORE INTO eventos_sync (uuid, local_id, tipo, payload, creado_en) "
            "VALUES (?, ?, ?, ?, ?)",
            (evento.uuid, evento.local_id, evento.tipo,
             json.dumps(evento.payload), evento.creado_en))
        self._conn.commit()

    def pendientes(self, limite: int = 100) -> list[EventoSync]:
        filas = self._conn.execute(
            "SELECT uuid, local_id, tipo, payload, creado_en FROM eventos_sync "
            "WHERE enviado_en IS NULL ORDER BY creado_en LIMIT ?", (limite,)).fetchall()
        return [EventoSync(f[0], f[1], f[2], json.loads(f[3]), f[4]) for f in filas]

    def marcar_enviados(self, uuids: list[str]) -> None:
        ahora = datetime.now(timezone.utc).isoformat()
        self._conn.executemany(
            "UPDATE eventos_sync SET enviado_en = ? WHERE uuid = ?",
            [(ahora, u) for u in uuids])
        self._conn.commit()


def serializar_venta(venta: Venta, pagos: list[Pago], almacen_id: int, local_id: str) -> EventoSync:
    payload = {
        "id": venta.id,
        "almacen_id": almacen_id,
        "local_id": local_id,
        "usuario_id": venta.usuario_id,
        "cliente_id": getattr(venta, "cliente_id", None),
        "sesion_id": getattr(venta, "caja_sesion_id", None),
        "fecha": str(venta.fecha),
        "total": str(venta.total),
        "total_impuestos": str(venta.total_impuestos),
        "lineas": [{"producto_id": ln.producto_id, "cantidad": str(ln.cantidad_o_peso),
                    "subtotal": str(ln.subtotal), "impuesto": str(ln.impuesto)}
                   for ln in venta.lineas],
        "pagos": [{"medio_pago_id": p.medio_pago_id, "monto": str(p.monto)} for p in pagos],
    }
    return EventoSync(uuid=str(uuid4()), local_id=local_id, tipo="venta",
                      payload=payload, creado_en=datetime.now(timezone.utc).isoformat())
```
> Ejecutor: confirma los nombres reales de atributos de `Venta`/`LineaVenta` (`subtotal`, `impuesto`, `cantidad_o_peso`, `fecha`, `caja_sesion_id`) en `entidades.py` y ajusta.

- [ ] **Step 6: Correr los tests (pasan) + suite completa**

Run: `cd /w/POS && python -m pytest tests/sync_pdv/test_outbox.py -v && python -m pytest -q`
Expected: tests de outbox PASS; suite completa sigue verde (la nueva migración 011 no rompe nada).

- [ ] **Step 7: Commit**

```bash
cd /w/POS && git add scripts/migraciones/011_outbox.sql src/core/puertos.py src/sync_pdv/outbox.py tests/sync_pdv
git commit -m "feat(sync): outbox local (eventos_sync) + serializador de venta"
```

---

## Task NUBE1.2: Enganche del outbox en la venta + cliente HTTP de push

**Objetivo:** que registrar una venta encole su evento (sin acoplar `core` al transporte) y que un `ClienteSync` suba los pendientes a `/sync/push` marcándolos enviados. Test con transporte fake (sin red).

**Files (en `w:\POS`):**
- Modify: `src/core/servicio_venta.py` (añadir `ServicioRegistroVentaConOutbox`)
- Create: `src/sync_pdv/cliente.py`
- Modify: `src/caja/contexto.py` (cablear outbox si hay config de sync)
- Test: `tests/core/test_registro_con_outbox.py`, `tests/sync_pdv/test_cliente.py`

**Interfaces:**
- Consumes: `RepositorioOutbox`, `serializar_venta` (NUBE1.1); `ServicioRegistroVenta.registrar` (existente).
- Produces:
  - `ServicioRegistroVentaConOutbox(interno: ServicioRegistroVenta, outbox: RepositorioOutbox, almacen_id: int, local_id: str)` con `registrar(venta, pagos) -> Venta` (registra y encola).
  - Puerto `TransporteSync` (Protocol): `push(eventos: list[dict]) -> list[str]` (devuelve uuids aceptados).
  - `ClienteSync(outbox, transporte)` con `sincronizar(limite=100) -> int` (nº de eventos subidos).
  - `TransporteHTTP(url, local_id, token)` (implementa `TransporteSync` con `httpx`).

- [ ] **Step 1: Test del decorador de registro (falla primero)**

`tests/core/test_registro_con_outbox.py`:
```python
from decimal import Decimal

from core.servicio_venta import ServicioRegistroVentaConOutbox


class _RegistroFake:
    def registrar(self, venta, pagos):
        return venta  # devuelve la misma venta como "guardada"


class _OutboxFake:
    def __init__(self):
        self.eventos = []
    def encolar(self, ev):
        self.eventos.append(ev)


def test_registrar_encola_evento_venta(venta_min, pagos_min):
    outbox = _OutboxFake()
    svc = ServicioRegistroVentaConOutbox(_RegistroFake(), outbox, almacen_id=7, local_id="local-01")
    svc.registrar(venta_min, pagos_min)
    assert len(outbox.eventos) == 1
    assert outbox.eventos[0].tipo == "venta"
    assert outbox.eventos[0].payload["almacen_id"] == 7
```
> `venta_min`/`pagos_min` = fixtures mínimas de `Venta`/`Pago` (define en `tests/core/conftest.py` o inline, con firmas reales).

- [ ] **Step 2: Correr (falla)** — Run: `python -m pytest tests/core/test_registro_con_outbox.py -v` → FAIL.

- [ ] **Step 3: Implementar `ServicioRegistroVentaConOutbox` en `core/servicio_venta.py`**

```python
class ServicioRegistroVentaConOutbox:
    """Decora ServicioRegistroVenta: registra y encola el evento para sync. core no ve el transporte."""

    def __init__(self, interno, outbox, almacen_id: int, local_id: str) -> None:
        self._interno = interno
        self._outbox = outbox
        self._almacen_id = almacen_id
        self._local_id = local_id

    def registrar(self, venta, pagos):
        guardada = self._interno.registrar(venta, pagos)
        from sync_pdv.outbox import serializar_venta   # import local: evita ciclo core->sync_pdv
        self._outbox.encolar(serializar_venta(guardada, pagos, self._almacen_id, self._local_id))
        return guardada
```
> El import diferido evita que `core` importe `sync_pdv` a nivel de módulo (respeta la dirección de dependencias). Alternativa más limpia: pasar `serializar` como callable inyectado en el constructor. Ejecutor: si el revisor prefiere pureza estricta, inyecta el serializador.

- [ ] **Step 4: Correr (pasa)** — Run: `python -m pytest tests/core/test_registro_con_outbox.py -v` → PASS.

- [ ] **Step 5: Test del `ClienteSync` con transporte fake (falla primero)**

`tests/sync_pdv/test_cliente.py`:
```python
from inventario.db import conectar, aplicar_migraciones
from sync_pdv.outbox import EventoSync, RepositorioOutboxSQLite
from sync_pdv.cliente import ClienteSync


class _TransporteFake:
    def __init__(self):
        self.recibidos = []
    def push(self, eventos):
        self.recibidos.extend(eventos)
        return [e["uuid"] for e in eventos]   # acepta todos


def _repo():
    c = conectar(":memory:"); aplicar_migraciones(c); return RepositorioOutboxSQLite(c)


def test_sincronizar_sube_y_marca_enviados():
    repo = _repo()
    repo.encolar(EventoSync("u1", "local-01", "venta", {"total": "10"}, "2026-07-06T10:00:00"))
    transporte = _TransporteFake()
    n = ClienteSync(repo, transporte).sincronizar()
    assert n == 1
    assert transporte.recibidos[0]["uuid"] == "u1"
    assert repo.pendientes() == []           # ya marcados enviados


def test_sincronizar_idempotente_sin_pendientes():
    repo = _repo()
    assert ClienteSync(repo, _TransporteFake()).sincronizar() == 0
```

- [ ] **Step 6: Correr (falla)** — Run: `python -m pytest tests/sync_pdv/test_cliente.py -v` → FAIL.

- [ ] **Step 7: Implementar `sync_pdv/cliente.py`**

```python
"""Cliente de sincronización: sube pendientes del outbox a la nube (idempotente por uuid)."""
from __future__ import annotations

from dataclasses import asdict
from typing import Protocol

from sync_pdv.outbox import EventoSync, RepositorioOutboxSQLite


class TransporteSync(Protocol):
    def push(self, eventos: list[dict]) -> list[str]: ...


class ClienteSync:
    def __init__(self, outbox: RepositorioOutboxSQLite, transporte: TransporteSync) -> None:
        self._outbox = outbox
        self._transporte = transporte

    def sincronizar(self, limite: int = 100) -> int:
        pendientes = self._outbox.pendientes(limite)
        if not pendientes:
            return 0
        aceptados = self._transporte.push([asdict(e) for e in pendientes])
        if aceptados:
            self._outbox.marcar_enviados(aceptados)
        return len(aceptados)


class TransporteHTTP:
    """POST del lote a /sync/push con Authorization: Bearer <local_id>:<token>."""

    def __init__(self, url: str, local_id: str, token: str) -> None:
        self._url = url.rstrip("/") + "/sync/push"
        self._auth = f"Bearer {local_id}:{token}"

    def push(self, eventos: list[dict]) -> list[str]:
        import httpx
        r = httpx.post(self._url, json={"eventos": eventos},
                       headers={"Authorization": self._auth}, timeout=10.0)
        r.raise_for_status()
        return r.json()["aceptados"]
```

- [ ] **Step 8: Correr (pasa)** — Run: `python -m pytest tests/sync_pdv/test_cliente.py -v` → PASS.

- [ ] **Step 9: Cablear en `contexto.py` (opcional, sin romper offline puro)**

En `ContextoApp.desde_conn`, si hay config de sync (env `LOCAL_ID`/`ALMACEN_ID`), envolver el registro:
```python
# tras construir svc_registro = ServicioRegistroVenta(...)
import os
local_id = os.environ.get("LOCAL_ID")
almacen_id = os.environ.get("ALMACEN_ID")
if local_id and almacen_id:
    from sync_pdv.outbox import RepositorioOutboxSQLite
    from core.servicio_venta import ServicioRegistroVentaConOutbox
    outbox = RepositorioOutboxSQLite(conn)
    svc_registro = ServicioRegistroVentaConOutbox(svc_registro, outbox, int(almacen_id), local_id)
```
> Mantener `svc_registro` con la misma interfaz (`registrar`) para no tocar la UI. Sin env de sync, el POS funciona idéntico a hoy.

- [ ] **Step 10: Suite completa + commit**

Run: `cd /w/POS && python -m pytest -q`
Expected: verde.
```bash
git add src/core/servicio_venta.py src/sync_pdv/cliente.py src/caja/contexto.py tests/core/test_registro_con_outbox.py tests/sync_pdv/test_cliente.py
git commit -m "feat(sync): enganche outbox en registro de venta + ClienteSync (push idempotente)"
```

---

## Task NUBE1.3: `/sync/push` idempotente por `uuid` (backend)

**Objetivo:** endpoint que recibe lotes de eventos del POS, hace UPSERT por `uuid` (reenviar no duplica) y materializa ventas/pagos con `almacen_id`. Devuelve los uuids aceptados.

**Files (en `w:\pos-plataforma-web`):**
- Create: `backend/app/sync.py`
- Modify: `backend/app/main.py` (incluir router)
- Test: `backend/tests/test_sync_push.py`

**Interfaces:**
- Consumes: `local_autenticado` (NUBE0.4), `conectar` (NUBE0.3).
- Produces: `POST /sync/push` body `{"eventos": [ {uuid, local_id, tipo, payload, creado_en}, ... ]}` → `{"aceptados": [uuid, ...]}`. Escribe en `eventos_sync` (ledger) + tablas `ventas/venta_lineas/pagos`. Idempotente: `INSERT ... ON CONFLICT (uuid) DO NOTHING`.

- [ ] **Step 1: Test de idempotencia (falla primero)**

`backend/tests/test_sync_push.py`:
```python
import os
import psycopg
import pytest
from fastapi.testclient import TestClient

from app.migraciones_runner import aplicar_migraciones
from app.main import app
import app.auth as auth_mod
from app.config import Settings

DB = os.environ.get("TEST_DB_URL")
LOTE = {"eventos": [{
    "uuid": "11111111-1111-1111-1111-111111111111",
    "local_id": "local-01", "tipo": "venta", "creado_en": "2026-07-06T10:00:00",
    "payload": {"id": 1, "almacen_id": 1, "local_id": "local-01", "usuario_id": 3,
                "cliente_id": None, "sesion_id": None, "fecha": "2026-07-06T10:00:00",
                "total": "100", "total_impuestos": "0",
                "lineas": [{"producto_id": 1, "cantidad": "2", "subtotal": "100", "impuesto": "0"}],
                "pagos": [{"medio_pago_id": 1, "monto": "100"}]},
}]}


@pytest.fixture()
def conn(monkeypatch):
    if not DB:
        pytest.skip("TEST_DB_URL no configurada")
    c = psycopg.connect(DB)
    c.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"); c.commit()
    aplicar_migraciones(c)
    # sembrar local + almacén de prueba
    c.execute("INSERT INTO locales (local_id, nombre, token_hash) VALUES ('local-01','L1','x')")
    c.execute("INSERT INTO almacenes (id, nombre, local_id) VALUES (1,'Bodega','local-01')")
    c.commit()
    monkeypatch.setattr(auth_mod, "settings",
                        Settings(db_url=DB, jwt_secret="x", local_tokens={"local-01": "tok1"}))
    monkeypatch.setenv("SUPABASE_DB_URL", DB)
    return c


def _push(client):
    return client.post("/sync/push", json=LOTE,
                       headers={"Authorization": "Bearer local-01:tok1"})


def test_push_crea_venta_y_es_idempotente(conn):
    client = TestClient(app)
    r1 = _push(client); assert r1.status_code == 200
    assert r1.json()["aceptados"] == ["11111111-1111-1111-1111-111111111111"]
    _push(client)  # reenvío del mismo lote
    n = conn.execute("SELECT count(*) FROM ventas").fetchone()[0]
    assert n == 1                              # no se duplicó
    total = conn.execute("SELECT total FROM ventas").fetchone()[0]
    assert str(total) == "100"


def test_push_sin_token_rechaza(conn):
    r = TestClient(app).post("/sync/push", json=LOTE)
    assert r.status_code == 401
```

- [ ] **Step 2: Correr (falla)** — Run: `TEST_DB_URL=... python -m pytest tests/test_sync_push.py -v` → FAIL.

- [ ] **Step 3: Implementar `sync.py`**

`backend/app/sync.py`:
```python
"""Ingest idempotente de eventos del POS. UPSERT por uuid -> reenviar es inocuo."""
from __future__ import annotations

import json
from decimal import Decimal

from fastapi import APIRouter, Depends

from app.auth import local_autenticado
from app.db import conectar

router = APIRouter()


@router.post("/sync/push")
def push(cuerpo: dict, local_id: str = Depends(local_autenticado)) -> dict:
    eventos = cuerpo.get("eventos", [])
    aceptados: list[str] = []
    with conectar() as conn:
        for ev in eventos:
            # ledger idempotente: si el uuid ya existía, no reprocesar
            cur = conn.execute(
                "INSERT INTO eventos_sync (uuid, local_id, tipo, payload) "
                "VALUES (%s, %s, %s, %s) ON CONFLICT (uuid) DO NOTHING",
                (ev["uuid"], local_id, ev["tipo"], json.dumps(ev["payload"])))
            aceptados.append(ev["uuid"])          # se ACK aunque ya existiera (idempotente)
            if cur.rowcount == 0:
                continue                           # ya materializado antes
            if ev["tipo"] == "venta":
                _materializar_venta(conn, ev["uuid"], ev["payload"])
        conn.commit()
    return {"aceptados": aceptados}


def _materializar_venta(conn, uuid: str, p: dict) -> None:
    conn.execute(
        "INSERT INTO ventas (uuid, id, local_id, almacen_id, usuario_id, cliente_id, "
        "sesion_id, fecha, total, total_impuestos) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (uuid) DO NOTHING",
        (uuid, p["id"], p["local_id"], p["almacen_id"], p.get("usuario_id"),
         p.get("cliente_id"), p.get("sesion_id"), p["fecha"],
         Decimal(p["total"]), Decimal(p["total_impuestos"])))
    for ln in p.get("lineas", []):
        conn.execute(
            "INSERT INTO venta_lineas (venta_uuid, almacen_id, producto_id, cantidad, subtotal, impuesto) "
            "VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
            (uuid, p["almacen_id"], ln["producto_id"], Decimal(ln["cantidad"]),
             Decimal(ln["subtotal"]), Decimal(ln["impuesto"])))
    for pg in p.get("pagos", []):
        conn.execute(
            "INSERT INTO pagos (venta_uuid, almacen_id, medio_pago_id, monto) VALUES (%s,%s,%s,%s)",
            (uuid, p["almacen_id"], pg["medio_pago_id"], Decimal(pg["monto"])))
```
> Idempotencia en dos niveles: el `ON CONFLICT` del ledger `eventos_sync` corta el reprocesamiento; los `ON CONFLICT DO NOTHING` de `ventas`/`venta_lineas` son cinturón-y-tirantes. Los `pagos` solo se insertan cuando el ledger aceptó el uuid por primera vez (`rowcount>0`), así no se duplican.

- [ ] **Step 4: Incluir el router en `main.py`**
```python
from app.sync import router as sync_router
app.include_router(sync_router)
```

- [ ] **Step 5: Correr (pasa)** — Run: `TEST_DB_URL=... python -m pytest tests/test_sync_push.py -v` → PASS (crea 1 venta, reenvío no duplica, 401 sin token).

- [ ] **Step 6: Commit**
```bash
cd /w/pos-plataforma-web
git add backend/app/sync.py backend/app/main.py backend/tests/test_sync_push.py
git commit -m "feat(backend): /sync/push idempotente por uuid (materializa venta+lineas+pagos)"
```

---

## Task NUBE1.4: Repos Postgres (puertos de `core`) por `almacen_id` + endpoints de dashboard

**Objetivo:** reusar `ServicioReportes` de `core` en la nube. Implementar repos Postgres que devuelven entidades de dominio filtradas por `almacen_id`, e instanciar `ServicioReportes` por almacén. Endpoints: total, por almacén, por cajero, por categoría.

**Files (en `w:\pos-plataforma-web`):**
- Create: `backend/app/repos_pg.py`, `backend/app/dashboard.py`
- Modify: `backend/app/main.py` (incluir router)
- Test: `backend/tests/test_dashboard.py`

**Interfaces:**
- Consumes: `ServicioReportes` de `core` (firma: `ServicioReportes(ventas, devoluciones, inventario, sesiones, efectivo_medio_pago_id=1, *, productos=..., ...)`); puertos `RepositorioVentas` (`ventas_en`, `pagos_en`, `ventas_de_sesion`, `totales_por_medio`), `RepositorioDevoluciones` (`devoluciones_en`, `de_sesion`), `RepositorioInventario` (`movimientos_en`), `RepositorioProductos` (`listar`), `RepositorioCajaSesiones` (`por_id`).
- Produces:
  - `RepositorioVentasPG(conn, almacen_id)`, `RepositorioDevolucionesPG(conn, almacen_id)`, `RepositorioProductosPG(conn)` (catálogo global), etc. Cada `*_en(desde, hasta)` añade `WHERE almacen_id = %s` (excepto productos, que es catálogo).
  - `GET /dashboard/resumen?desde&hasta` → `{"total": {...}, "por_almacen": [{almacen_id, nombre, ...}]}`.
  - `GET /dashboard/almacen/{almacen_id}/cajeros?desde&hasta` → `[ReporteCajero...]`.
  - `GET /dashboard/almacen/{almacen_id}/categorias?desde&hasta` → `[ReporteCategoria...]`.
  - Todos protegidos por `usuario_web` (JWT Supabase).

- [ ] **Step 1: Test del dashboard (falla primero)**

`backend/tests/test_dashboard.py`:
```python
import os, jwt, psycopg, pytest
from decimal import Decimal
from fastapi.testclient import TestClient

from app.migraciones_runner import aplicar_migraciones
from app.main import app
import app.auth as auth_mod
from app.config import Settings

DB = os.environ.get("TEST_DB_URL")


@pytest.fixture()
def sembrada(monkeypatch):
    if not DB:
        pytest.skip("TEST_DB_URL no configurada")
    c = psycopg.connect(DB)
    c.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"); c.commit()
    aplicar_migraciones(c)
    c.execute("INSERT INTO locales VALUES ('local-01','L1','x',true)")
    c.execute("INSERT INTO almacenes (id,nombre,local_id) VALUES (1,'Bodega A','local-01'),(2,'Bodega B','local-01')")
    c.execute("INSERT INTO categorias VALUES (10,'Carnes')")
    c.execute("INSERT INTO productos VALUES (1,'Lomo',10)")
    c.execute("INSERT INTO usuarios VALUES (3,'Ana','local-01')")
    # dos ventas en almacenes distintos
    for uuid, alm, total in (("a1","1","100"), ("b1","2","40")):
        u = f"{uuid}0000-0000-0000-0000-000000000000"
        c.execute("INSERT INTO ventas (uuid,id,local_id,almacen_id,usuario_id,fecha,total,total_impuestos) "
                  "VALUES (%s,1,'local-01',%s,3,'2026-07-06T10:00:00',%s,'0')", (u, alm, total))
        c.execute("INSERT INTO venta_lineas (venta_uuid,almacen_id,producto_id,cantidad,subtotal,impuesto) "
                  "VALUES (%s,%s,1,'1',%s,'0')", (u, alm, total))
        c.execute("INSERT INTO pagos (venta_uuid,almacen_id,medio_pago_id,monto) VALUES (%s,%s,1,%s)", (u, alm, total))
    c.commit()
    monkeypatch.setattr(auth_mod, "settings", Settings(db_url=DB, jwt_secret="sec", local_tokens={}))
    monkeypatch.setenv("SUPABASE_DB_URL", DB)
    return c


def _hdr():
    return {"Authorization": f"Bearer {jwt.encode({'sub':'u1','email':'a@b.co'}, 'sec', algorithm='HS256')}"}


def test_resumen_total_y_por_almacen(sembrada):
    client = TestClient(app)
    r = client.get("/dashboard/resumen?desde=2026-07-01T00:00:00&hasta=2026-07-31T00:00:00", headers=_hdr())
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["total"]["total"] == "140"                 # 100 + 40
    por_alm = {a["almacen_id"]: a["total"] for a in cuerpo["por_almacen"]}
    assert por_alm[1] == "100" and por_alm[2] == "40"


def test_resumen_sin_jwt_rechaza(sembrada):
    assert TestClient(app).get("/dashboard/resumen?desde=2026-07-01T00:00:00&hasta=2026-07-31T00:00:00").status_code == 401
```

- [ ] **Step 2: Correr (falla)** — Run: `TEST_DB_URL=... python -m pytest tests/test_dashboard.py -v` → FAIL.

- [ ] **Step 3: Implementar `repos_pg.py`**

Mapea filas Postgres → entidades de `core.entidades`, filtrando por `almacen_id`. **Referencia de firmas:** replicar la forma de `ventas/repositorio_sqlite.py` (`ventas_en`, `pagos_en`, etc.) del repo POS, adaptada a psycopg. Estructura mínima para el dashboard:

```python
"""Repos Postgres que implementan los puertos de core, acotados por almacen_id."""
from __future__ import annotations

from datetime import datetime

from core.entidades import LineaVenta, Pago, Producto, Venta


class RepositorioVentasPG:
    def __init__(self, conn, almacen_id: int) -> None:
        self._conn, self._alm = conn, almacen_id

    def ventas_en(self, desde: datetime, hasta: datetime) -> list[Venta]:
        filas = self._conn.execute(
            "SELECT uuid, id, usuario_id, fecha, total, total_impuestos FROM ventas "
            "WHERE almacen_id=%s AND fecha>=%s AND fecha<%s ORDER BY fecha",
            (self._alm, desde, hasta)).fetchall()
        ventas = []
        for f in filas:
            lineas = self._conn.execute(
                "SELECT producto_id, cantidad, subtotal, impuesto FROM venta_lineas "
                "WHERE venta_uuid=%s", (f[0],)).fetchall()
            ventas.append(_venta(f, lineas))
        return ventas

    def pagos_en(self, desde: datetime, hasta: datetime) -> list[Pago]:
        filas = self._conn.execute(
            "SELECT p.venta_uuid, p.medio_pago_id, p.monto, v.id FROM pagos p "
            "JOIN ventas v ON v.uuid=p.venta_uuid "
            "WHERE p.almacen_id=%s AND v.fecha>=%s AND v.fecha<%s",
            (self._alm, desde, hasta)).fetchall()
        return [Pago(venta_id=f[3], medio_pago_id=f[1], monto=f[2]) for f in filas]

    # ventas_de_sesion / totales_por_medio: implementar análogo si el endpoint los usa.


class RepositorioDevolucionesPG:
    def __init__(self, conn, almacen_id: int) -> None:
        self._conn, self._alm = conn, almacen_id
    def devoluciones_en(self, desde, hasta):
        return []           # sin devoluciones en la demo; tabla existe para cuando el POS las empuje
    def de_sesion(self, sesion_id):
        return []


class RepositorioProductosPG:
    def __init__(self, conn) -> None:
        self._conn = conn
    def listar(self) -> list[Producto]:
        filas = self._conn.execute("SELECT id, nombre, categoria_id FROM productos").fetchall()
        return [_producto(f) for f in filas]


def _venta(f, lineas) -> Venta:
    return Venta(
        id=f[1], usuario_id=f[2], fecha=f[3],
        lineas=[LineaVenta(producto_id=l[0], subtotal=l[2], impuesto=l[3], cantidad_o_peso=l[1])
                for l in lineas])
    # Ejecutor: ajustar kwargs a la firma real de Venta/LineaVenta; si Venta calcula total desde
    # lineas, no pasar total. Verifica en core/entidades.py.


def _producto(f) -> Producto:
    return Producto(id=f[0], nombre=f[1], categoria_id=f[2])  # ajustar kwargs reales
```
> **Punto clave para el ejecutor:** `ServicioReportes.ventas()` usa `v.total`/`v.total_impuestos` de la entidad. Confirma si `Venta` los calcula desde `lineas` o si hay que setearlos. Si los calcula, construye las `LineaVenta` con los valores correctos para que `total` cuadre; si no, extiende `_venta` para setearlos. Mantén dinero como `Decimal` (psycopg ya lo entrega así).

- [ ] **Step 4: Implementar `dashboard.py`**

```python
"""Endpoints de dashboard: reusan ServicioReportes de core, instanciado por almacen_id."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends

from core.servicio_reportes import ServicioReportes
from app.auth import usuario_web
from app.db import conectar
from app.repos_pg import RepositorioDevolucionesPG, RepositorioProductosPG, RepositorioVentasPG

router = APIRouter(prefix="/dashboard")


def _reportes(conn, almacen_id: int) -> ServicioReportes:
    return ServicioReportes(
        ventas=RepositorioVentasPG(conn, almacen_id),
        devoluciones=RepositorioDevolucionesPG(conn, almacen_id),
        inventario=None, sesiones=None,          # no usados por .ventas()/.por_categoria()
        productos=RepositorioProductosPG(conn))


def _dto_ventas(rv) -> dict:
    return {"num_ventas": rv.num_ventas, "total": str(rv.total),
            "total_impuestos": str(rv.total_impuestos), "neto": str(rv.neto)}


@router.get("/resumen")
def resumen(desde: datetime, hasta: datetime, _=Depends(usuario_web)) -> dict:
    with conectar() as conn:
        almacenes = conn.execute("SELECT id, nombre FROM almacenes WHERE activo ORDER BY id").fetchall()
        por_almacen, total_n, total_v, total_i = [], 0, 0, 0
        for aid, nombre in almacenes:
            rv = _reportes(conn, aid).ventas(desde, hasta)
            por_almacen.append({"almacen_id": aid, "nombre": nombre, **_dto_ventas(rv)})
            total_n += rv.num_ventas
        # total consolidado = suma de netos por almacén (evita re-consultar)
        from decimal import Decimal
        tot = sum((Decimal(a["total"]) for a in por_almacen), Decimal("0"))
        imp = sum((Decimal(a["total_impuestos"]) for a in por_almacen), Decimal("0"))
        return {"total": {"num_ventas": total_n, "total": str(tot), "total_impuestos": str(imp),
                          "neto": str(tot)}, "por_almacen": por_almacen}


@router.get("/almacen/{almacen_id}/cajeros")
def por_cajero(almacen_id: int, desde: datetime, hasta: datetime, _=Depends(usuario_web)) -> list[dict]:
    with conectar() as conn:
        rs = _reportes(conn, almacen_id).por_cajero(desde, hasta)
        return [{"usuario_id": r.usuario_id, "num_ventas": r.num_ventas,
                 "total": str(r.total), "neto": str(r.neto)} for r in rs]


@router.get("/almacen/{almacen_id}/categorias")
def por_categoria(almacen_id: int, desde: datetime, hasta: datetime, _=Depends(usuario_web)) -> list[dict]:
    with conectar() as conn:
        rs = _reportes(conn, almacen_id).por_categoria(desde, hasta)
        return [{"categoria_id": r.categoria_id, "total": str(r.total), "neto": str(r.neto)} for r in rs]
```
> `por_cajero` consume `pagos_en` además de `ventas_en`; ambos ya implementados en `RepositorioVentasPG`. Si `ServicioReportes.por_cajero` necesita métodos no implementados, añádelos al repo siguiendo el mismo patrón (WHERE almacen_id).

- [ ] **Step 5: Incluir router + correr (pasa)**

`main.py`: `from app.dashboard import router as dash_router; app.include_router(dash_router)`
Run: `TEST_DB_URL=... python -m pytest tests/test_dashboard.py -v`
Expected: PASS (total=140, por almacén 100/40, 401 sin JWT).

- [ ] **Step 6: Commit**
```bash
cd /w/pos-plataforma-web
git add backend/app/repos_pg.py backend/app/dashboard.py backend/app/main.py backend/tests/test_dashboard.py
git commit -m "feat(backend): repos Postgres por almacen_id + endpoints dashboard reusando ServicioReportes"
```

---

## Task NUBE1.5: Dashboard React con gráficas (total, por almacén, por cajero, por categoría)

**Objetivo:** pantalla que consume los endpoints y muestra gráficas. Es la demo para el cliente.

**Files (en `w:\pos-plataforma-web/frontend`):**
- Create: `src/dashboard/Dashboard.tsx`, `src/dashboard/charts.ts`, `src/dashboard/components/KpiCard.tsx`, `VentasPorAlmacen.tsx`, `PorCajero.tsx`, `PorCategoria.tsx`
- Modify: `src/App.tsx` (renderizar `Dashboard` cuando hay sesión)
- Test: `npm run build` + verificación visual manual.

**Interfaces:**
- Consumes: `apiGet` (NUBE0.5); endpoints `/dashboard/*` (NUBE1.4).
- Produces: `Dashboard` (React), tipos `Resumen`, `PorAlmacen`, `Cajero`, `Categoria`.

**Guía de diseño (cargar skills `dataviz` y `frontend-design` antes de implementar):** paleta consistente en claro/oscuro, formato de moneda COP, una gráfica de barras "ventas por almacén" (comparativo), KPIs (total, nº ventas), y al seleccionar un almacén, barras por cajero y por categoría. Contenedores con `overflow-x:auto` para tablas/gráficas anchas.

- [ ] **Step 1: `charts.ts` (formato + paleta placeholder de `dataviz`)**
```ts
export const COP = new Intl.NumberFormat("es-CO", { style: "currency", currency: "COP", maximumFractionDigits: 0 });
export const PALETA = ["#4f46e5", "#06b6d4", "#f59e0b", "#10b981", "#ef4444", "#8b5cf6"];
export const fmt = (s: string) => COP.format(Number(s));
```

- [ ] **Step 2: Tipos + `Dashboard.tsx` (orquesta llamadas)**
```tsx
import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { apiGet } from "../api";
import { fmt, PALETA } from "./charts";
import { KpiCard } from "./components/KpiCard";
import { PorCajero } from "./components/PorCajero";
import { PorCategoria } from "./components/PorCategoria";

type Ventas = { num_ventas: number; total: string; total_impuestos: string; neto: string };
type PorAlmacen = Ventas & { almacen_id: number; nombre: string };
type Resumen = { total: Ventas; por_almacen: PorAlmacen[] };

const RANGO = "desde=2026-07-01T00:00:00&hasta=2026-07-31T00:00:00"; // TODO selector de fechas (post-demo)

export function Dashboard() {
  const [data, setData] = useState<Resumen | null>(null);
  const [almacen, setAlmacen] = useState<number | null>(null);

  useEffect(() => { apiGet<Resumen>(`/dashboard/resumen?${RANGO}`).then(setData); }, []);
  if (!data) return <p>Cargando…</p>;

  return (
    <div style={{ display: "grid", gap: 24 }}>
      <div style={{ display: "flex", gap: 16 }}>
        <KpiCard titulo="Ventas totales" valor={fmt(data.total.total)} />
        <KpiCard titulo="Nº ventas" valor={String(data.total.num_ventas)} />
      </div>

      <section>
        <h2>Ventas por almacén</h2>
        <div style={{ overflowX: "auto" }}>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={data.por_almacen.map((a) => ({ ...a, total: Number(a.total) }))}>
              <XAxis dataKey="nombre" /><YAxis /><Tooltip formatter={(v) => fmt(String(v))} />
              <Bar dataKey="total" fill={PALETA[0]}
                   onClick={(_, i) => setAlmacen(data.por_almacen[i].almacen_id)} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <p style={{ opacity: 0.7 }}>Clic en una barra para ver cajeros y categorías del almacén.</p>
      </section>

      {almacen !== null && (
        <div style={{ display: "grid", gap: 24, gridTemplateColumns: "1fr 1fr" }}>
          <PorCajero almacenId={almacen} rango={RANGO} />
          <PorCategoria almacenId={almacen} rango={RANGO} />
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: `components/KpiCard.tsx`, `PorCajero.tsx`, `PorCategoria.tsx`**
```tsx
// KpiCard.tsx
export function KpiCard({ titulo, valor }: { titulo: string; valor: string }) {
  return (
    <div style={{ border: "1px solid #8883", borderRadius: 12, padding: 16, minWidth: 180 }}>
      <div style={{ opacity: 0.7, fontSize: 13 }}>{titulo}</div>
      <div style={{ fontSize: 28, fontWeight: 700 }}>{valor}</div>
    </div>
  );
}
```
```tsx
// PorCajero.tsx
import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { apiGet } from "../../api";
import { fmt, PALETA } from "../charts";

type Cajero = { usuario_id: number | null; num_ventas: number; total: string; neto: string };

export function PorCajero({ almacenId, rango }: { almacenId: number; rango: string }) {
  const [rows, setRows] = useState<Cajero[]>([]);
  useEffect(() => { apiGet<Cajero[]>(`/dashboard/almacen/${almacenId}/cajeros?${rango}`).then(setRows); }, [almacenId, rango]);
  return (
    <section>
      <h3>Por cajero</h3>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={rows.map((r) => ({ cajero: `#${r.usuario_id ?? "—"}`, total: Number(r.total) }))}>
          <XAxis dataKey="cajero" /><YAxis /><Tooltip formatter={(v) => fmt(String(v))} />
          <Bar dataKey="total" fill={PALETA[1]} />
        </BarChart>
      </ResponsiveContainer>
    </section>
  );
}
```
```tsx
// PorCategoria.tsx  (misma estructura; endpoint /categorias, dataKey categoria_id, PALETA[2])
import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { apiGet } from "../../api";
import { fmt, PALETA } from "../charts";

type Categoria = { categoria_id: number | null; total: string; neto: string };

export function PorCategoria({ almacenId, rango }: { almacenId: number; rango: string }) {
  const [rows, setRows] = useState<Categoria[]>([]);
  useEffect(() => { apiGet<Categoria[]>(`/dashboard/almacen/${almacenId}/categorias?${rango}`).then(setRows); }, [almacenId, rango]);
  return (
    <section>
      <h3>Por categoría</h3>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={rows.map((r) => ({ cat: `#${r.categoria_id ?? "—"}`, total: Number(r.total) }))}>
          <XAxis dataKey="cat" /><YAxis /><Tooltip formatter={(v) => fmt(String(v))} />
          <Bar dataKey="total" fill={PALETA[2]} />
        </BarChart>
      </ResponsiveContainer>
    </section>
  );
}
```

- [ ] **Step 4: Renderizar `Dashboard` en `App.tsx`**

Reemplazar el placeholder de sesión iniciada por `<Dashboard />` (importar de `./dashboard/Dashboard`).

- [ ] **Step 5: Build + verificación end-to-end manual**

```bash
cd /w/pos-plataforma-web/frontend && npm run build
```
Verificación manual (levantar backend con Postgres sembrado + POS empujando eventos): login → dashboard muestra KPIs, barras por almacén; clic en barra → cajeros y categorías. Confirmar que los números cuadran con lo que el POS envió.

- [ ] **Step 6: Commit**
```bash
cd /w/pos-plataforma-web
git add frontend/src
git commit -m "feat(frontend): dashboard multi-bodega con graficas (total/almacen/cajero/categoria)"
```

---

## Cierre del epic (ambas fases)

- [ ] Correr suite del POS completa: `cd /w/POS && python -m pytest -q` → **verde** (confirma que extraer `core` y el outbox no rompieron nada).
- [ ] Backend: `cd /w/pos-plataforma-web/backend && TEST_DB_URL=... python -m pytest -q` → verde.
- [ ] Frontend: `npm run build` → sin errores.
- [ ] Verificación integrada (con permiso): POS (con `LOCAL_ID`/`ALMACEN_ID`) registra una venta → `ClienteSync.sincronizar()` la sube → dashboard la refleja.
- [ ] Actualizar la fila correspondiente en `docs/README-pos.md` (estado: sync/outbox y dashboard nube en marcha) y `docs/estado-actual-y-brechas.md` (§8.1 pasa de ⛔ a 🟡).
- [ ] Reportar qué se implementó y cómo se verificó. **Preguntar antes de integrar (merge) o desplegar** (Vercel/host backend).

---

## Self-Review (contra el spec)

**Cobertura del spec:**
- §3 arquitectura 3 capas → NUBE0.2 (backend), NUBE0.5 (web), NUBE1.1-1.2 (POS outbox/cliente). ✅
- §4 sync offline-first, outbox `uuid+local_id+timestamp`, `/sync/push` idempotente, `/sync/pull` → push/outbox en NUBE1.1-1.3. **Pull (réplica RO del catálogo) es Fase 2** (no en este entregable; el catálogo se siembra/empuja para el dashboard). Documentado como fuera de alcance aquí.
- §5 modelo Postgres con `almacen_id` transversal, `eventos_sync`/outbox → NUBE0.3, NUBE1.1. ✅ (`almacenes`, `almacen_id` en ventas/lineas/pagos/sesiones/inventario_movimientos). `adelantos_nomina`/`empleados` son Fase 3 → fuera de alcance. ✅
- §8 dashboard total/por almacén/por cajero/por categoría reusando `ServicioReportes` → NUBE1.4-1.5. ✅
- §9 `core` compartido sin duplicar (pip install) → NUBE0.1. ✅
- §10 roadmap: este plan = Fase 0 + 1 exactamente. ✅

**Decisiones flagged para revisión (no bloquean, pero conviene confirmar en el gate):**
1. **Import namespace `core` (no `pos_core`).** Elegido por Ponytail/suite-verde; la distribución sí se llama `pos-core`. Si el revisor exige `pos_core` como namespace, es un rename mecánico masivo (todos los `from core...`) → task extra.
2. **`/sync/pull` (réplica RO catálogo) diferido a Fase 2.** Para la demo el catálogo (productos/categorías/usuarios) se puebla en Postgres (semilla o empuje), suficiente para el dashboard. Confirmar que la demo no necesita edición de catálogo desde la web (eso es Fase 2 explícitamente).
3. **`ServicioReportes` recibe `inventario=None, sesiones=None`** en los endpoints que no los usan (`ventas`, `por_cajero`, `por_categoria`). Si algún método tocara esos repos, hay que implementarlos. Verificado: los 3 endpoints del dashboard solo usan `ventas`, `devoluciones`, `productos`.

**Escaneo de placeholders:** los `# Ejecutor: ajustar…` remiten a **verificar firmas reales de entidades** (`Venta`/`LineaVenta`/`Pago`/`Producto`) antes de codificar — no son "TODO implementar", son puntos de verificación obligatoria contra `core/entidades.py`. El único `TODO` literal (selector de fechas en el dashboard) está marcado explícitamente como post-demo (YAGNI para la primera pantalla, que usa un rango fijo del mes).

**Consistencia de tipos:** `EventoSync` (uuid, local_id, tipo, payload, creado_en) idéntico en outbox (NUBE1.1), cliente (NUBE1.2), y body de `/sync/push` (NUBE1.3). `ServicioReportes` firma citada de `core/servicio_reportes.py:108`. Dinero como string en JSON / `Decimal` en Python-Postgres, consistente en 1.1/1.3/1.4.
