# Usuarios/roles + Cliente y descuento en la venta — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Autenticar al operador (usuario+contraseña, roles admin/cajero), trazar `usuario_id` en venta/cierre/devolución, y permitir vender a un cliente con descuento porcentual (recalculando IVA incluido).

**Architecture:** Hexagonal. Reglas nuevas (hash, permisos, descuento, autenticación) viven en `core/` (Python puro). La persistencia pasa por puertos `RepositorioX` con adaptadores SQLite en `src/ventas/`. La UI Qt (`caja/`) inyecta servicios y gatea controles con `puede()`. Se sigue TDD: test primero, dominio → persistencia → UI.

**Tech Stack:** Python 3.11+, PySide6 (Qt6), SQLite (`sqlite3`), pytest. Hash con `hashlib`/`hmac`/`secrets` (stdlib).

**Spec:** [../specs/2026-06-30-usuarios-cliente-descuento-design.md](../specs/2026-06-30-usuarios-cliente-descuento-design.md)

## Global Constraints

- `src/core/` NO importa Qt ni sqlite3 — solo entidades, reglas y puertos.
- SQL solo dentro de adaptadores de repositorio (`src/ventas/`, `src/inventario/`).
- Sin dependencias nuevas (Ponytail): solo stdlib + PySide6 + pytest ya presentes.
- Nombres de dominio en español (`Usuario`, `ServicioUsuarios`, `puede`).
- Dinero/cantidades como `Decimal` vía texto (nunca float). Redondeo a peso entero con `ROUND_HALF_UP`.
- Tests: `test_*.py`, estructura espejo bajo `tests/`. `pythonpath = src`. UI Qt con patrón offscreen + `importorskip("PySide6")` (no `pytest-qt`).
- Migraciones SQLite: `scripts/migraciones/NNN_*.sql`, aplicadas en orden por `aplicar_migraciones`.
- Roles: `("admin", "cajero")`. Acciones solo-admin: `gestionar_usuarios`, `editar_productos`, `aplicar_descuento_manual`.
- Commits terminan con `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

---

### Task 1: `core/seguridad.py` — hash y verificación de contraseñas

**Files:**
- Create: `src/core/seguridad.py`
- Test: `tests/core/test_seguridad.py`

**Interfaces:**
- Produces: `hash_password(password: str) -> str` (formato `pbkdf2_sha256$<iter>$<sal_hex>$<hash_hex>`); `verificar(password: str, codificado: str) -> bool` (comparación en tiempo constante).

- [ ] **Step 1: Write the failing test**

Create `tests/core/test_seguridad.py`:

```python
from core.seguridad import hash_password, verificar


def test_verifica_password_correcta():
    h = hash_password("secreta123")
    assert verificar("secreta123", h) is True


def test_rechaza_password_incorrecta():
    h = hash_password("secreta123")
    assert verificar("otra", h) is False


def test_hashes_distintos_por_sal():
    assert hash_password("misma") != hash_password("misma")


def test_verificar_rechaza_formato_invalido():
    assert verificar("x", "no-es-un-hash") is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/core/test_seguridad.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.seguridad'`

- [ ] **Step 3: Write the implementation**

Create `src/core/seguridad.py`:

```python
"""Hash y verificación de contraseñas. Python puro (stdlib)."""
from __future__ import annotations

import hashlib
import hmac
import secrets

_ALGO = "pbkdf2_sha256"
_ITERACIONES = 200_000


def hash_password(password: str) -> str:
    sal = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(sal), _ITERACIONES)
    return f"{_ALGO}${_ITERACIONES}${sal}${dk.hex()}"


def verificar(password: str, codificado: str) -> bool:
    try:
        algo, iteraciones, sal, hash_hex = codificado.split("$")
        if algo != _ALGO:
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(sal), int(iteraciones))
    except (ValueError, AttributeError):
        return False
    return hmac.compare_digest(dk.hex(), hash_hex)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/core/test_seguridad.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/core/seguridad.py tests/core/test_seguridad.py
git commit -m "feat(core): seguridad.hash_password/verificar (pbkdf2_hmac stdlib)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: `core/permisos.py` — `puede(rol, accion)`

**Files:**
- Create: `src/core/permisos.py`
- Test: `tests/core/test_permisos.py`

**Interfaces:**
- Produces: constantes `ACCION_GESTIONAR_USUARIOS`, `ACCION_EDITAR_PRODUCTOS`, `ACCION_DESCUENTO_MANUAL`; `PERMISOS_ADMIN: frozenset[str]`; `puede(rol: str, accion: str) -> bool`.

- [ ] **Step 1: Write the failing test**

Create `tests/core/test_permisos.py`:

```python
import pytest

from core.permisos import (
    ACCION_DESCUENTO_MANUAL, ACCION_EDITAR_PRODUCTOS, ACCION_GESTIONAR_USUARIOS, puede,
)

ACCIONES_ADMIN = [ACCION_GESTIONAR_USUARIOS, ACCION_EDITAR_PRODUCTOS, ACCION_DESCUENTO_MANUAL]


@pytest.mark.parametrize("accion", ACCIONES_ADMIN)
def test_admin_puede_acciones_restringidas(accion):
    assert puede("admin", accion) is True


@pytest.mark.parametrize("accion", ACCIONES_ADMIN)
def test_cajero_no_puede_acciones_restringidas(accion):
    assert puede("cajero", accion) is False


@pytest.mark.parametrize("accion", ["vender", "anular", "devolver", "cerrar_caja"])
def test_cajero_puede_acciones_no_restringidas(accion):
    assert puede("cajero", accion) is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/core/test_permisos.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.permisos'`

- [ ] **Step 3: Write the implementation**

Create `src/core/permisos.py`:

```python
"""Permisos por rol. Python puro. admin puede todo; cajero todo salvo lo restringido."""
from __future__ import annotations

ACCION_GESTIONAR_USUARIOS = "gestionar_usuarios"
ACCION_EDITAR_PRODUCTOS = "editar_productos"
ACCION_DESCUENTO_MANUAL = "aplicar_descuento_manual"

PERMISOS_ADMIN = frozenset({
    ACCION_GESTIONAR_USUARIOS, ACCION_EDITAR_PRODUCTOS, ACCION_DESCUENTO_MANUAL})


def puede(rol: str, accion: str) -> bool:
    return rol == "admin" or accion not in PERMISOS_ADMIN
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/core/test_permisos.py -v`
Expected: PASS (10 passed)

- [ ] **Step 5: Commit**

```bash
git add src/core/permisos.py tests/core/test_permisos.py
git commit -m "feat(core): permisos.puede(rol, accion) con acciones solo-admin

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Entidad `Usuario`

**Files:**
- Modify: `src/core/entidades.py`
- Test: `tests/core/test_usuario.py`

**Interfaces:**
- Produces: `ROLES = ("admin", "cajero")`; `@dataclass(frozen=True) Usuario(nombre: str, rol: str = "cajero", id: int | None = None)`; valida nombre no vacío y `rol ∈ ROLES`.

- [ ] **Step 1: Write the failing test**

Create `tests/core/test_usuario.py`:

```python
import pytest

from core.entidades import Usuario


def test_usuario_valido():
    u = Usuario(nombre="ana", rol="admin")
    assert u.nombre == "ana"
    assert u.rol == "admin"


def test_rol_por_defecto_cajero():
    assert Usuario(nombre="ana").rol == "cajero"


def test_rechaza_rol_invalido():
    with pytest.raises(ValueError):
        Usuario(nombre="ana", rol="gerente")


def test_rechaza_nombre_vacio():
    with pytest.raises(ValueError):
        Usuario(nombre="   ")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/core/test_usuario.py -v`
Expected: FAIL with `ImportError: cannot import name 'Usuario'`

- [ ] **Step 3: Add the entity**

In `src/core/entidades.py`, add after the `MedioPago` dataclass (around line 73):

```python
ROLES = ("admin", "cajero")


@dataclass(frozen=True)
class Usuario:
    nombre: str
    rol: str = "cajero"
    id: int | None = None

    def __post_init__(self) -> None:
        if not self.nombre.strip():
            raise ValueError("el nombre de usuario es obligatorio")
        if self.rol not in ROLES:
            raise ValueError(f"rol inválido: {self.rol!r}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/core/test_usuario.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/core/entidades.py tests/core/test_usuario.py
git commit -m "feat(core): entidad Usuario (nombre, rol, id) con validación de rol

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Puerto `RepositorioUsuarios` + `ServicioUsuarios`

**Files:**
- Modify: `src/core/puertos.py`
- Create: `src/core/servicio_usuarios.py`
- Test: `tests/core/test_servicio_usuarios.py`

**Interfaces:**
- Consumes: `Usuario` (core.entidades); `hash_password`/`verificar` (core.seguridad).
- Produces:
  - Puerto `RepositorioUsuarios` con `guardar(usuario, hash_password) -> Usuario`, `por_id(id) -> Usuario | None`, `por_nombre(nombre) -> Usuario | None`, `credencial(nombre) -> tuple[Usuario, str] | None`, `listar() -> list[Usuario]`.
  - `class UsuarioDuplicado(ValueError)`.
  - `ServicioUsuarios(repo)` con `crear(nombre, password, rol="cajero") -> Usuario`, `autenticar(nombre, password) -> Usuario | None`, `listar() -> list[Usuario]`.

- [ ] **Step 1: Write the failing test**

Create `tests/core/test_servicio_usuarios.py`:

```python
from dataclasses import replace

import pytest

from core.entidades import Usuario
from core.servicio_usuarios import ServicioUsuarios, UsuarioDuplicado


class FakeRepoUsuarios:
    def __init__(self):
        self._items: dict[int, Usuario] = {}
        self._hashes: dict[int, str] = {}
        self._next = 1

    def guardar(self, usuario, hash_password):
        u = replace(usuario, id=self._next)
        self._items[self._next] = u
        self._hashes[self._next] = hash_password
        self._next += 1
        return u

    def por_id(self, id):
        return self._items.get(id)

    def por_nombre(self, nombre):
        return next((u for u in self._items.values() if u.nombre == nombre), None)

    def credencial(self, nombre):
        u = self.por_nombre(nombre)
        return (u, self._hashes[u.id]) if u else None

    def listar(self):
        return list(self._items.values())


def test_crear_persiste_usuario():
    s = ServicioUsuarios(FakeRepoUsuarios())
    u = s.crear("ana", "clave1234", rol="admin")
    assert u.id is not None
    assert u.rol == "admin"


def test_crear_rechaza_nombre_duplicado():
    s = ServicioUsuarios(FakeRepoUsuarios())
    s.crear("ana", "clave1234")
    with pytest.raises(UsuarioDuplicado):
        s.crear("ana", "otra")


def test_crear_exige_password():
    s = ServicioUsuarios(FakeRepoUsuarios())
    with pytest.raises(ValueError):
        s.crear("ana", "")


def test_autenticar_ok():
    s = ServicioUsuarios(FakeRepoUsuarios())
    s.crear("ana", "clave1234")
    assert s.autenticar("ana", "clave1234").nombre == "ana"


def test_autenticar_password_mala_devuelve_none():
    s = ServicioUsuarios(FakeRepoUsuarios())
    s.crear("ana", "clave1234")
    assert s.autenticar("ana", "incorrecta") is None


def test_autenticar_usuario_inexistente_devuelve_none():
    s = ServicioUsuarios(FakeRepoUsuarios())
    assert s.autenticar("fantasma", "x") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/core/test_servicio_usuarios.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.servicio_usuarios'`

- [ ] **Step 3: Add the port**

In `src/core/puertos.py`, add `Usuario` to the `from core.entidades import (...)` block, then add this Protocol (e.g. after `RepositorioMediosPago`):

```python
class RepositorioUsuarios(Protocol):
    def guardar(self, usuario: Usuario, hash_password: str) -> Usuario: ...
    def por_id(self, id: int) -> Usuario | None: ...
    def por_nombre(self, nombre: str) -> Usuario | None: ...
    def credencial(self, nombre: str) -> tuple[Usuario, str] | None: ...
    def listar(self) -> list[Usuario]: ...
```

- [ ] **Step 4: Write the service**

Create `src/core/servicio_usuarios.py`:

```python
"""Servicio de usuarios: crear y autenticar. Python puro vía puerto + seguridad."""
from __future__ import annotations

from core.entidades import Usuario
from core.puertos import RepositorioUsuarios
from core.seguridad import hash_password, verificar


class UsuarioDuplicado(ValueError):
    pass


class ServicioUsuarios:
    def __init__(self, repo: RepositorioUsuarios) -> None:
        self._repo = repo

    def crear(self, nombre: str, password: str, rol: str = "cajero") -> Usuario:
        if not nombre.strip():
            raise ValueError("el nombre es obligatorio")
        if not password:
            raise ValueError("la contraseña es obligatoria")
        if self._repo.por_nombre(nombre) is not None:
            raise UsuarioDuplicado(f"ya existe usuario {nombre!r}")
        return self._repo.guardar(Usuario(nombre=nombre, rol=rol), hash_password(password))

    def autenticar(self, nombre: str, password: str) -> Usuario | None:
        cred = self._repo.credencial(nombre)
        if cred is None:
            return None
        usuario, hash_ = cred
        return usuario if verificar(password, hash_) else None

    def listar(self) -> list[Usuario]:
        return self._repo.listar()
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/core/test_servicio_usuarios.py -v`
Expected: PASS (6 passed)

- [ ] **Step 6: Commit**

```bash
git add src/core/puertos.py src/core/servicio_usuarios.py tests/core/test_servicio_usuarios.py
git commit -m "feat(core): RepositorioUsuarios (puerto) + ServicioUsuarios (crear/autenticar)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Migración `005` + runner de migraciones idempotente

`ALTER TABLE ADD COLUMN` no es idempotente y `aplicar_migraciones` re-ejecuta todos los `.sql` en cada arranque sobre la DB persistente. Este task hace el runner idempotente (registra las migraciones aplicadas) y agrega la migración `005`.

**Files:**
- Modify: `src/inventario/db.py` (`aplicar_migraciones`)
- Create: `scripts/migraciones/005_usuarios_descuento.sql`
- Test: `tests/inventario/test_migraciones_005.py`

**Interfaces:**
- Consumes: `conectar`, `aplicar_migraciones` (inventario.db).
- Produces: tabla `schema_migraciones(archivo PK, aplicada_en)`; `aplicar_migraciones` corre cada archivo una sola vez; columnas `clientes.descuento_pct` y `ventas.descuento_pct` (DECIMAL default `'0'`); índice único `idx_usuarios_nombre`.

- [ ] **Step 1: Write the failing test**

Create `tests/inventario/test_migraciones_005.py`:

```python
import sqlite3

import pytest

from inventario.db import aplicar_migraciones, conectar


def _columnas(conn, tabla):
    return {r["name"] for r in conn.execute(f"PRAGMA table_info({tabla})")}


def test_agrega_descuento_pct_a_clientes_y_ventas():
    conn = conectar()
    aplicar_migraciones(conn)
    assert "descuento_pct" in _columnas(conn, "clientes")
    assert "descuento_pct" in _columnas(conn, "ventas")


def test_aplicar_migraciones_es_idempotente():
    conn = conectar()
    aplicar_migraciones(conn)
    aplicar_migraciones(conn)  # no debe lanzar "duplicate column name"
    assert "descuento_pct" in _columnas(conn, "clientes")


def test_nombre_de_usuario_es_unico():
    conn = conectar()
    aplicar_migraciones(conn)
    conn.execute("INSERT INTO usuarios (nombre, rol, hash_password) VALUES ('ana','cajero','h')")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO usuarios (nombre, rol, hash_password) VALUES ('ana','admin','h2')")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/inventario/test_migraciones_005.py -v`
Expected: FAIL — no existe la columna `descuento_pct` (y sin el runner idempotente, la doble aplicación lanzaría más adelante).

- [ ] **Step 3: Add the migration**

Create `scripts/migraciones/005_usuarios_descuento.sql`:

```sql
-- 005: unicidad de login (usuarios.nombre) + descuento porcentual (cliente y venta).
-- El runner (inventario.db.aplicar_migraciones) aplica cada archivo una sola vez.

CREATE UNIQUE INDEX IF NOT EXISTS idx_usuarios_nombre ON usuarios(nombre);

-- Descuento porcentual del cliente (fracción 0..1; 0 = sin descuento).
ALTER TABLE clientes ADD COLUMN descuento_pct DECIMAL NOT NULL DEFAULT '0';

-- Descuento porcentual aplicado a la venta (cliente o manual). Para recibo/reportes.
ALTER TABLE ventas ADD COLUMN descuento_pct DECIMAL NOT NULL DEFAULT '0';
```

- [ ] **Step 4: Make the runner idempotent**

Replace `aplicar_migraciones` in `src/inventario/db.py` (and add the datetime import at the top):

```python
from datetime import datetime, timezone
```

```python
def aplicar_migraciones(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migraciones ("
        "archivo TEXT PRIMARY KEY, aplicada_en TEXT NOT NULL)")
    aplicadas = {r[0] for r in conn.execute("SELECT archivo FROM schema_migraciones")}
    for archivo in sorted(DIR_MIGRACIONES.glob("*.sql")):
        if archivo.name in aplicadas:
            continue
        conn.executescript(archivo.read_text(encoding="utf-8"))
        conn.execute(
            "INSERT INTO schema_migraciones (archivo, aplicada_en) VALUES (?, ?)",
            (archivo.name, datetime.now(timezone.utc).isoformat()))
    conn.commit()
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/inventario/test_migraciones_005.py -v`
Expected: PASS (3 passed)

- [ ] **Step 6: Run the full suite (guard against regressions in migration ordering)**

Run: `python -m pytest -q`
Expected: PASS (no regressions; migraciones 001–004 se siguen aplicando).

- [ ] **Step 7: Commit**

```bash
git add src/inventario/db.py scripts/migraciones/005_usuarios_descuento.sql tests/inventario/test_migraciones_005.py
git commit -m "feat(db): migración 005 (descuento_pct + índice único usuarios); runner idempotente

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: `RepositorioUsuariosSQLite` + seed admin por defecto

**Files:**
- Modify: `src/ventas/repositorio_sqlite.py`
- Modify: `src/caja/bootstrap.py`
- Test: `tests/ventas/test_repositorio_usuarios.py`
- Test: `tests/caja/test_bootstrap.py` (añadir)

**Interfaces:**
- Consumes: `Usuario` (core.entidades), `hash_password` (core.seguridad), fixture `conn` (tests/ventas/conftest.py), migración `005`.
- Produces:
  - `RepositorioUsuariosSQLite(conn)` que implementa el puerto `RepositorioUsuarios`.
  - `ADMIN_POR_DEFECTO = ("admin", "admin1234")` y `sembrar_admin(conn)` (idempotente) en `caja.bootstrap`; `preparar_db` lo invoca.

- [ ] **Step 1: Write the failing test (adapter)**

Create `tests/ventas/test_repositorio_usuarios.py`:

```python
import pytest

from core.entidades import Usuario
from ventas.repositorio_sqlite import RepositorioUsuariosSQLite


def test_guardar_y_leer_por_nombre(conn):
    repo = RepositorioUsuariosSQLite(conn)
    u = repo.guardar(Usuario(nombre="ana", rol="admin"), "hash-x")
    assert u.id is not None
    leido = repo.por_nombre("ana")
    assert leido.rol == "admin"
    assert leido.id == u.id


def test_credencial_devuelve_usuario_y_hash(conn):
    repo = RepositorioUsuariosSQLite(conn)
    repo.guardar(Usuario(nombre="ana"), "hash-x")
    usuario, hash_ = repo.credencial("ana")
    assert usuario.nombre == "ana"
    assert hash_ == "hash-x"


def test_credencial_inexistente_none(conn):
    repo = RepositorioUsuariosSQLite(conn)
    assert repo.credencial("fantasma") is None


def test_listar(conn):
    repo = RepositorioUsuariosSQLite(conn)
    repo.guardar(Usuario(nombre="ana"), "h")
    repo.guardar(Usuario(nombre="beto"), "h")
    assert [u.nombre for u in repo.listar()] == ["ana", "beto"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/ventas/test_repositorio_usuarios.py -v`
Expected: FAIL with `ImportError: cannot import name 'RepositorioUsuariosSQLite'`

- [ ] **Step 3: Write the adapter**

In `src/ventas/repositorio_sqlite.py`, add `Usuario` to the `from core.entidades import (...)` block, then add near the other repos:

```python
def _fila_a_usuario(f: sqlite3.Row) -> Usuario:
    return Usuario(nombre=f["nombre"], rol=f["rol"], id=f["id"])


class RepositorioUsuariosSQLite:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def guardar(self, usuario: Usuario, hash_password: str) -> Usuario:
        cur = self._conn.execute(
            "INSERT INTO usuarios (nombre, rol, hash_password) VALUES (?, ?, ?)",
            (usuario.nombre, usuario.rol, hash_password))
        self._conn.commit()
        return replace(usuario, id=cur.lastrowid)

    def por_id(self, id: int) -> Usuario | None:
        f = self._conn.execute("SELECT * FROM usuarios WHERE id = ?", (id,)).fetchone()
        return _fila_a_usuario(f) if f else None

    def por_nombre(self, nombre: str) -> Usuario | None:
        f = self._conn.execute("SELECT * FROM usuarios WHERE nombre = ?", (nombre,)).fetchone()
        return _fila_a_usuario(f) if f else None

    def credencial(self, nombre: str) -> tuple[Usuario, str] | None:
        f = self._conn.execute("SELECT * FROM usuarios WHERE nombre = ?", (nombre,)).fetchone()
        return (_fila_a_usuario(f), f["hash_password"]) if f else None

    def listar(self) -> list[Usuario]:
        filas = self._conn.execute("SELECT * FROM usuarios ORDER BY id").fetchall()
        return [_fila_a_usuario(f) for f in filas]
```

- [ ] **Step 4: Run adapter tests**

Run: `python -m pytest tests/ventas/test_repositorio_usuarios.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Write the failing test (seed admin)**

Append to `tests/caja/test_bootstrap.py`:

```python
from caja.bootstrap import ADMIN_POR_DEFECTO, sembrar_admin
from core.servicio_usuarios import ServicioUsuarios
from ventas.repositorio_sqlite import RepositorioUsuariosSQLite
from inventario.db import aplicar_migraciones, conectar


def test_sembrar_admin_crea_admin_si_no_hay_usuarios():
    conn = conectar()
    aplicar_migraciones(conn)
    sembrar_admin(conn)
    nombre, password = ADMIN_POR_DEFECTO
    servicio = ServicioUsuarios(RepositorioUsuariosSQLite(conn))
    autenticado = servicio.autenticar(nombre, password)
    assert autenticado is not None
    assert autenticado.rol == "admin"


def test_sembrar_admin_es_idempotente():
    conn = conectar()
    aplicar_migraciones(conn)
    sembrar_admin(conn)
    sembrar_admin(conn)
    total = conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
    assert total == 1
```

- [ ] **Step 6: Run to verify it fails**

Run: `python -m pytest tests/caja/test_bootstrap.py -k admin -v`
Expected: FAIL with `ImportError: cannot import name 'sembrar_admin'`

- [ ] **Step 7: Add the seed**

In `src/caja/bootstrap.py`, add the import and the function, and call it from `preparar_db`:

```python
from core.seguridad import hash_password

ADMIN_POR_DEFECTO = ("admin", "admin1234")


def sembrar_admin(conn: sqlite3.Connection) -> None:
    """Crea un admin por defecto si no hay usuarios. Idempotente."""
    if conn.execute("SELECT 1 FROM usuarios LIMIT 1").fetchone():
        return
    nombre, password = ADMIN_POR_DEFECTO
    conn.execute(
        "INSERT INTO usuarios (nombre, rol, hash_password) VALUES (?, 'admin', ?)",
        (nombre, hash_password(password)))
    conn.commit()
```

Update `preparar_db` to call it:

```python
def preparar_db(ruta: str = "pos.db") -> sqlite3.Connection:
    conn = conectar(ruta)
    aplicar_migraciones(conn)
    sembrar_demo(conn)
    sembrar_admin(conn)
    return conn
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `python -m pytest tests/caja/test_bootstrap.py tests/ventas/test_repositorio_usuarios.py -v`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add src/ventas/repositorio_sqlite.py src/caja/bootstrap.py tests/ventas/test_repositorio_usuarios.py tests/caja/test_bootstrap.py
git commit -m "feat(ventas): RepositorioUsuariosSQLite + seed admin por defecto en bootstrap

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Descuento en entidades + `aplicar_descuento`

**Files:**
- Modify: `src/core/entidades.py` (`Cliente`, `Venta`)
- Modify: `src/core/calculos.py`
- Test: `tests/core/test_calculos.py` (añadir)
- Test: `tests/core/test_entidades_descuento.py` (crear)

**Interfaces:**
- Produces:
  - `Cliente.descuento_pct: Decimal = CERO` y `Venta.descuento_pct: Decimal = CERO`, ambos validados a `0 ≤ pct < 1`.
  - `calculos.aplicar_descuento(subtotal_bruto: Decimal, pct: Decimal) -> Decimal` (neto redondeado a peso, `ROUND_HALF_UP`).

- [ ] **Step 1: Write the failing test (cálculo)**

Append to `tests/core/test_calculos.py`:

```python
from core.calculos import aplicar_descuento


def test_aplicar_descuento_porcentual():
    assert aplicar_descuento(Decimal("1000"), Decimal("0.1")) == Decimal("900")


def test_aplicar_descuento_cero_no_cambia():
    assert aplicar_descuento(Decimal("2500"), Decimal("0")) == Decimal("2500")


def test_aplicar_descuento_redondea_half_up_a_peso():
    # 999 * (1 - 0.075) = 924.075 -> 924
    assert aplicar_descuento(Decimal("999"), Decimal("0.075")) == Decimal("924")


def test_aplicar_descuento_rechaza_pct_fuera_de_rango():
    with pytest.raises(ValueError):
        aplicar_descuento(Decimal("1000"), Decimal("1"))
```

(Si `pytest`/`Decimal` no están importados en ese archivo, añade `import pytest` y `from decimal import Decimal` arriba.)

- [ ] **Step 2: Write the failing test (entidades)**

Create `tests/core/test_entidades_descuento.py`:

```python
from datetime import datetime
from decimal import Decimal

import pytest

from core.entidades import Cliente, LineaVenta, Venta


def test_cliente_descuento_pct_por_defecto_cero():
    assert Cliente(identificacion="1", nombre="x").descuento_pct == Decimal("0")


def test_cliente_rechaza_descuento_fuera_de_rango():
    with pytest.raises(ValueError):
        Cliente(identificacion="1", nombre="x", descuento_pct=Decimal("1"))


def test_venta_acepta_descuento_pct():
    linea = LineaVenta(producto_id=1, descripcion="p", cantidad_o_peso=Decimal("1"),
                       precio_unit=Decimal("100"), impuesto=Decimal("0"), subtotal=Decimal("100"))
    v = Venta(fecha=datetime.now(), lineas=(linea,), total=Decimal("100"),
              total_impuestos=Decimal("0"), descuento_pct=Decimal("0.1"))
    assert v.descuento_pct == Decimal("0.1")
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/core/test_calculos.py -k descuento tests/core/test_entidades_descuento.py -v`
Expected: FAIL (`aplicar_descuento` no existe; `Cliente`/`Venta` no aceptan `descuento_pct`).

- [ ] **Step 4: Add `descuento_pct` to entities**

In `src/core/entidades.py`, modify `Cliente` to add the field and validation:

```python
@dataclass(frozen=True)
class Cliente:
    identificacion: str
    nombre: str
    contacto: str | None = None
    bloqueado_edicion: bool = False
    tipo_documento: str | None = None        # reservado DIAN
    regimen: str | None = None               # reservado DIAN
    tipo_responsabilidad: str | None = None  # reservado DIAN
    descuento_pct: Decimal = CERO            # fracción 0..1
    id: int | None = None

    def __post_init__(self) -> None:
        if not (CERO <= self.descuento_pct < Decimal("1")):
            raise ValueError("descuento_pct debe estar en [0, 1)")
```

In the `Venta` dataclass, add the field (before `id`) and extend `__post_init__`:

```python
    descuento_pct: Decimal = CERO   # descuento aplicado a la venta (cliente o manual)
    id: int | None = None

    def __post_init__(self) -> None:
        if self.estado not in ESTADOS_VENTA:
            raise ValueError(f"estado inválido: {self.estado!r}")
        if not (CERO <= self.descuento_pct < Decimal("1")):
            raise ValueError("descuento_pct debe estar en [0, 1)")
```

- [ ] **Step 5: Add `aplicar_descuento`**

In `src/core/calculos.py`, add:

```python
def aplicar_descuento(subtotal_bruto: Decimal, pct: Decimal) -> Decimal:
    """Subtotal neto tras descuento porcentual, redondeado a peso entero (ROUND_HALF_UP)."""
    if subtotal_bruto < CERO or not (CERO <= pct < Decimal("1")):
        raise ValueError("subtotal no negativo y pct en [0, 1)")
    return (subtotal_bruto * (Decimal("1") - pct)).quantize(_PESO, rounding=ROUND_HALF_UP)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m pytest tests/core/test_calculos.py tests/core/test_entidades_descuento.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/core/entidades.py src/core/calculos.py tests/core/test_calculos.py tests/core/test_entidades_descuento.py
git commit -m "feat(core): Cliente/Venta.descuento_pct + calculos.aplicar_descuento

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: Persistencia del descuento (adaptadores clientes + ventas)

**Files:**
- Modify: `src/ventas/repositorio_sqlite.py` (`RepositorioClientesSQLite`, `RepositorioVentasSQLite`)
- Test: `tests/ventas/test_repositorio_descuento.py` (crear)

**Interfaces:**
- Consumes: migración `005` (columnas `descuento_pct`), fixture `conn`.
- Produces: `guardar`/`por_id`/`por_identificacion`/`listar`/`actualizar` de clientes leen/escriben `descuento_pct`; `RepositorioVentasSQLite.guardar`/`por_id` persisten/leen `ventas.descuento_pct`.

- [ ] **Step 1: Write the failing test**

Create `tests/ventas/test_repositorio_descuento.py`:

```python
from datetime import datetime
from decimal import Decimal

from core.entidades import Cliente, LineaVenta, Venta
from ventas.repositorio_sqlite import RepositorioClientesSQLite, RepositorioVentasSQLite


def test_cliente_persiste_descuento_pct(conn):
    repo = RepositorioClientesSQLite(conn)
    c = repo.guardar(Cliente(identificacion="900", nombre="Mayorista", descuento_pct=Decimal("0.1")))
    assert repo.por_id(c.id).descuento_pct == Decimal("0.1")


def test_venta_persiste_descuento_pct(conn):
    linea = LineaVenta(producto_id=1, descripcion="Arroz", cantidad_o_peso=Decimal("1"),
                       precio_unit=Decimal("2500"), impuesto=Decimal("0"), subtotal=Decimal("2250"))
    venta = Venta(fecha=datetime.now(), lineas=(linea,), total=Decimal("2250"),
                  total_impuestos=Decimal("0"), descuento_pct=Decimal("0.1"))
    repo = RepositorioVentasSQLite(conn)
    guardada = repo.guardar(venta, [])
    assert repo.por_id(guardada.id).descuento_pct == Decimal("0.1")
```

Nota: `venta_lineas.producto_id` referencia `productos(id)`. Con `PRAGMA foreign_keys = ON`, este test requiere un producto id=1. Añade al inicio del test de venta, tras crear `linea`:

```python
    conn.execute("INSERT INTO categorias (id, nombre) VALUES (1, 'X')")
    conn.execute("INSERT INTO impuestos (id, nombre, tarifa) VALUES (1, 'IVA 0%', '0')")
    conn.execute(
        "INSERT INTO productos (id, codigo_barras, nombre, precio, costo, categoria_id, "
        "impuesto_id, vendido_por_peso, unidad) VALUES (1, '1', 'Arroz', '2500', '0', 1, 1, 0, 'und')")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/ventas/test_repositorio_descuento.py -v`
Expected: FAIL — `descuento_pct` no se persiste (KeyError / valor por defecto).

- [ ] **Step 3: Update `RepositorioClientesSQLite`**

In `src/ventas/repositorio_sqlite.py`:

Extend `_fila_a_cliente` to read the column:

```python
def _fila_a_cliente(f: sqlite3.Row) -> Cliente:
    return Cliente(
        identificacion=f["identificacion"],
        nombre=f["nombre"],
        contacto=f["contacto"],
        bloqueado_edicion=bool(f["bloqueado_edicion"]),
        tipo_documento=f["tipo_documento"],
        regimen=f["regimen"],
        tipo_responsabilidad=f["tipo_responsabilidad"],
        descuento_pct=f["descuento_pct"],
        id=f["id"],
    )
```

Update `_COLS` and `guardar` (add one column + placeholder):

```python
    _COLS = ("identificacion, nombre, contacto, bloqueado_edicion, "
             "tipo_documento, regimen, tipo_responsabilidad, descuento_pct")

    def guardar(self, cliente: Cliente) -> Cliente:
        cur = self._conn.execute(
            f"INSERT INTO clientes ({self._COLS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (cliente.identificacion, cliente.nombre, cliente.contacto,
             int(cliente.bloqueado_edicion), cliente.tipo_documento,
             cliente.regimen, cliente.tipo_responsabilidad, cliente.descuento_pct))
        self._conn.commit()
        return replace(cliente, id=cur.lastrowid)
```

Update `actualizar` to set the column:

```python
    def actualizar(self, cliente: Cliente) -> Cliente:
        cur = self._conn.execute(
            "UPDATE clientes SET identificacion = ?, nombre = ?, contacto = ?, "
            "bloqueado_edicion = ?, tipo_documento = ?, regimen = ?, "
            "tipo_responsabilidad = ?, descuento_pct = ? WHERE id = ?",
            (cliente.identificacion, cliente.nombre, cliente.contacto,
             int(cliente.bloqueado_edicion), cliente.tipo_documento,
             cliente.regimen, cliente.tipo_responsabilidad, cliente.descuento_pct, cliente.id))
        if cur.rowcount == 0:
            raise LookupError(f"cliente inexistente: id={cliente.id}")
        self._conn.commit()
        return cliente
```

- [ ] **Step 4: Update `RepositorioVentasSQLite`**

In `guardar`, add `descuento_pct` to the `ventas` INSERT:

```python
        cur = self._conn.execute(
            "INSERT INTO ventas "
            "(fecha, usuario_id, caja_sesion_id, cliente_id, total, total_impuestos, "
            "estado, descuento_pct) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (venta.fecha.isoformat(), venta.usuario_id, venta.caja_sesion_id,
             venta.cliente_id, venta.total, venta.total_impuestos, venta.estado,
             venta.descuento_pct))
```

In `por_id`, read it into the `Venta`:

```python
        return Venta(
            fecha=datetime.fromisoformat(fv["fecha"]),
            lineas=tuple(_fila_a_linea(f) for f in filas),
            total=fv["total"],
            total_impuestos=fv["total_impuestos"],
            usuario_id=fv["usuario_id"],
            caja_sesion_id=fv["caja_sesion_id"],
            cliente_id=fv["cliente_id"],
            estado=fv["estado"],
            descuento_pct=fv["descuento_pct"],
            id=fv["id"],
        )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/ventas/test_repositorio_descuento.py -v`
Expected: PASS (2 passed)

- [ ] **Step 6: Commit**

```bash
git add src/ventas/repositorio_sqlite.py tests/ventas/test_repositorio_descuento.py
git commit -m "feat(ventas): persistir descuento_pct en clientes y ventas

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9: `ServicioVenta` — descuento por línea

Se reestructura el acumulador para guardar la **entrada bruta** de cada línea, de modo que cambiar el descuento recomponga las líneas sin pérdida. La API pública (`agregar`, `agregar_escaneado`, `lineas`, `total`, `total_impuestos`, `confirmar`) no cambia de firma; con `descuento_pct = 0` el comportamiento es idéntico al actual.

**Files:**
- Modify: `src/core/servicio_venta.py` (`ServicioVenta`)
- Test: `tests/core/test_servicio_venta_descuento.py` (crear)

**Interfaces:**
- Consumes: `aplicar_descuento` (core.calculos), `impuesto_incluido`.
- Produces: `ServicioVenta.descuento_pct` (Decimal, default `CERO`); `establecer_descuento(pct: Decimal) -> None`; `confirmar(...)` incluye `descuento_pct` en la `Venta`.

- [ ] **Step 1: Write the failing test**

Create `tests/core/test_servicio_venta_descuento.py`:

```python
from datetime import datetime
from decimal import Decimal

import pytest

from core.entidades import Impuesto, Producto
from core.servicio_venta import ServicioVenta


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


def _servicio():
    arroz = Producto(codigo_barras="7700006", nombre="Arroz", precio=Decimal("2500"),
                     impuesto_id=1, id=1)
    iva = Impuesto(nombre="IVA 19%", tarifa=Decimal("0.19"), id=1)
    return ServicioVenta(FakeProductos([arroz]), FakeImpuestos([iva]))


def test_sin_descuento_subtotal_bruto():
    s = _servicio()
    linea = s.agregar("7700006", cantidad=2)
    assert linea.subtotal == Decimal("5000")


def test_descuento_aplica_por_linea():
    s = _servicio()
    s.establecer_descuento(Decimal("0.1"))
    linea = s.agregar("7700006", cantidad=2)
    assert linea.subtotal == Decimal("4500")  # round(5000 * 0.9)


def test_descuento_recalcula_iva_incluido():
    s = _servicio()
    s.establecer_descuento(Decimal("0.1"))
    linea = s.agregar("7700006", cantidad=2)
    # IVA contenido en 4500 al 19%: round(4500 * 0.19 / 1.19) = 719
    assert linea.impuesto == Decimal("719")


def test_establecer_descuento_recomputa_lineas_existentes():
    s = _servicio()
    s.agregar("7700006", cantidad=2)
    s.establecer_descuento(Decimal("0.1"))
    assert s.total == Decimal("4500")


def test_confirmar_incluye_descuento_pct():
    s = _servicio()
    s.establecer_descuento(Decimal("0.1"))
    s.agregar("7700006", cantidad=1)
    venta = s.confirmar(fecha=datetime.now())
    assert venta.descuento_pct == Decimal("0.1")


def test_establecer_descuento_rechaza_fuera_de_rango():
    s = _servicio()
    with pytest.raises(ValueError):
        s.establecer_descuento(Decimal("1"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/core/test_servicio_venta_descuento.py -v`
Expected: FAIL — `ServicioVenta` no tiene `establecer_descuento`.

- [ ] **Step 3: Refactor `ServicioVenta`**

In `src/core/servicio_venta.py`, update the import line:

```python
from dataclasses import dataclass, replace
```

Add `aplicar_descuento` to the calculos import:

```python
from core.calculos import (
    aplicar_descuento, impuesto_incluido, subtotal_por_peso, subtotal_por_unidad,
)
```

Add the internal entry dataclass just before `class ServicioVenta`:

```python
@dataclass
class _Entrada:
    producto_id: int
    descripcion: str
    cantidad_o_peso: Decimal
    precio_unit: Decimal
    subtotal_bruto: Decimal
    tarifa: Decimal
```

Replace the body of `ServicioVenta` down to `confirmar` with:

```python
class ServicioVenta:
    """Acumula líneas de una venta en curso y la confirma como `Venta`."""

    def __init__(self, productos: RepositorioProductos, impuestos: RepositorioImpuestos) -> None:
        self._productos = productos
        self._impuestos = impuestos
        self._entradas: list[_Entrada] = []
        self.descuento_pct: Decimal = CERO

    def establecer_descuento(self, pct: Decimal) -> None:
        if not (CERO <= pct < Decimal("1")):
            raise ValueError("descuento_pct debe estar en [0, 1)")
        self.descuento_pct = pct

    def agregar(self, codigo_barras: str, *, cantidad: Decimal | int = 1,
                peso_kg: Decimal | None = None,
                importe: Decimal | None = None) -> LineaVenta:
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
            bruto = (importe if importe is not None
                     else subtotal_por_peso(producto.precio, peso_kg))
        else:
            if importe is not None:
                raise ValueError(
                    f"{producto.nombre} se vende por unidad; importe no aplica")
            cantidad_o_peso = Decimal(cantidad)
            bruto = subtotal_por_unidad(producto.precio, cantidad_o_peso)
        entrada = _Entrada(
            producto_id=producto.id, descripcion=producto.nombre,
            cantidad_o_peso=cantidad_o_peso, precio_unit=producto.precio,
            subtotal_bruto=bruto, tarifa=tarifa)
        self._entradas.append(entrada)
        return self._linea(entrada)

    def _linea(self, e: _Entrada) -> LineaVenta:
        subtotal = aplicar_descuento(e.subtotal_bruto, self.descuento_pct)
        return LineaVenta(
            producto_id=e.producto_id, descripcion=e.descripcion,
            cantidad_o_peso=e.cantidad_o_peso, precio_unit=e.precio_unit,
            impuesto=impuesto_incluido(subtotal, e.tarifa), subtotal=subtotal)

    def agregar_escaneado(self, codigo: str,
                          formato: FormatoGS1 = FORMATO_PESO_DEFECTO) -> LineaVenta:
        """Agrega según un código escaneado: GS1 de peso variable o EAN/PLU normal."""
        if not es_peso_variable(codigo, formato):
            return self.agregar(codigo, cantidad=1)
        resultado = decodificar_gs1(codigo, formato)
        producto = self._productos.por_codigo(resultado.codigo_producto)
        if producto is None:
            raise ProductoNoEncontrado(
                f"producto inexistente: {resultado.codigo_producto!r} (código {codigo!r})")
        if not producto.vendido_por_peso:
            raise ValueError(
                f"{producto.nombre} no se vende por peso pero el código es de peso variable")
        peso, importe = peso_e_importe_gs1(resultado, producto, formato.valor_es_precio)
        return self.agregar(resultado.codigo_producto, peso_kg=peso, importe=importe)

    @property
    def lineas(self) -> tuple[LineaVenta, ...]:
        return tuple(self._linea(e) for e in self._entradas)

    @property
    def total(self) -> Decimal:
        return sum((l.subtotal for l in self.lineas), CERO)

    @property
    def total_impuestos(self) -> Decimal:
        return sum((l.impuesto for l in self.lineas), CERO)

    def confirmar(self, *, fecha: datetime, usuario_id: int | None = None,
                  caja_sesion_id: int | None = None, cliente_id: int | None = None) -> Venta:
        if not self._entradas:
            raise ValueError("no se puede confirmar una venta vacía")
        return Venta(
            fecha=fecha,
            lineas=self.lineas,
            total=self.total,
            total_impuestos=self.total_impuestos,
            usuario_id=usuario_id,
            caja_sesion_id=caja_sesion_id,
            cliente_id=cliente_id,
            descuento_pct=self.descuento_pct,
            estado="pagada",
        )
```

- [ ] **Step 4: Run the new tests**

Run: `python -m pytest tests/core/test_servicio_venta_descuento.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Run the existing ServicioVenta suite (no regressions)**

Run: `python -m pytest tests/core -q`
Expected: PASS — con `descuento_pct = 0` el resultado es idéntico al anterior.

- [ ] **Step 6: Commit**

```bash
git add src/core/servicio_venta.py tests/core/test_servicio_venta_descuento.py
git commit -m "feat(core): ServicioVenta aplica descuento por línea (recalcula IVA incluido)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 10: `ServicioClientes.actualizar` respeta `bloqueado_edicion`

**Files:**
- Modify: `src/core/servicio_clientes.py`
- Test: `tests/core/test_servicio_clientes.py` (añadir)

**Interfaces:**
- Produces: `class ClienteBloqueado(ValueError)`; `ServicioClientes.actualizar` lanza `ClienteBloqueado` si el cliente destino tiene `bloqueado_edicion`.

- [ ] **Step 1: Write the failing test**

Append to `tests/core/test_servicio_clientes.py`:

```python
from core.servicio_clientes import ClienteBloqueado


def test_actualizar_cliente_bloqueado_lanza():
    repo = FakeRepoClientes()
    s = ServicioClientes(repo)
    c = repo.guardar(Cliente(identificacion="900", nombre="X", bloqueado_edicion=True))
    with pytest.raises(ClienteBloqueado):
        s.actualizar(replace(c, nombre="Nuevo"))


def test_actualizar_cliente_no_bloqueado_ok():
    repo = FakeRepoClientes()
    s = ServicioClientes(repo)
    c = repo.guardar(Cliente(identificacion="900", nombre="X"))
    assert s.actualizar(replace(c, nombre="Nuevo")).nombre == "Nuevo"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/core/test_servicio_clientes.py -k bloqueado -v`
Expected: FAIL with `ImportError: cannot import name 'ClienteBloqueado'`

- [ ] **Step 3: Add the rule**

In `src/core/servicio_clientes.py`, add the exception and the guard:

```python
class ClienteBloqueado(ValueError):
    pass
```

```python
    def actualizar(self, cliente: Cliente) -> Cliente:
        if cliente.id is None:
            raise ValueError("no se puede actualizar un cliente sin id")
        actual = self._repo.por_id(cliente.id)
        if actual is not None and actual.bloqueado_edicion:
            raise ClienteBloqueado(f"cliente {cliente.id} bloqueado para edición")
        return self._repo.actualizar(cliente)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/core/test_servicio_clientes.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/core/servicio_clientes.py tests/core/test_servicio_clientes.py
git commit -m "feat(core): ServicioClientes.actualizar respeta bloqueado_edicion

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 11: `ContextoApp` — usuarios y `usuario_actual`

**Files:**
- Modify: `src/caja/contexto.py`
- Test: `tests/caja/test_contexto.py` (añadir)

**Interfaces:**
- Consumes: `RepositorioUsuariosSQLite`, `ServicioUsuarios`, `Usuario`.
- Produces: `ContextoApp.repo_usuarios`, `ContextoApp.svc_usuarios`, `ContextoApp.usuario_actual: Usuario | None = None`, y `@property usuario_actual_id -> int | None`.

- [ ] **Step 1: Write the failing test**

Append to `tests/caja/test_contexto.py`:

```python
from caja.bootstrap import ADMIN_POR_DEFECTO


def test_contexto_autentica_admin_por_defecto():
    ctx = ContextoApp.crear(":memory:")
    nombre, password = ADMIN_POR_DEFECTO
    assert ctx.svc_usuarios.autenticar(nombre, password) is not None


def test_usuario_actual_id_none_por_defecto():
    ctx = ContextoApp.crear(":memory:")
    assert ctx.usuario_actual is None
    assert ctx.usuario_actual_id is None
```

(Si `ContextoApp` no está importado en ese archivo, añade `from caja.contexto import ContextoApp`.)

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/caja/test_contexto.py -k "admin or usuario_actual" -v`
Expected: FAIL — `ContextoApp` no tiene `svc_usuarios` / `usuario_actual_id`.

- [ ] **Step 3: Wire `ContextoApp`**

In `src/caja/contexto.py`:

Add imports:

```python
from core.entidades import Usuario
from core.servicio_usuarios import ServicioUsuarios
```

and add `RepositorioUsuariosSQLite` to the `from ventas.repositorio_sqlite import (...)` block.

Add fields to the dataclass (after `svc_reportes`, before `formato_gs1`):

```python
    repo_usuarios: RepositorioUsuariosSQLite = None  # type: ignore[assignment]
    svc_usuarios: ServicioUsuarios = None            # type: ignore[assignment]
    usuario_actual: Usuario | None = None
```

In `desde_conn`, build the repo/service and pass them:

```python
        usuarios = RepositorioUsuariosSQLite(conn)
```

and add to the `cls(...)` call:

```python
            repo_usuarios=usuarios,
            svc_usuarios=ServicioUsuarios(usuarios),
```

Add the property to the class:

```python
    @property
    def usuario_actual_id(self) -> int | None:
        return self.usuario_actual.id if self.usuario_actual else None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/caja/test_contexto.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/caja/contexto.py tests/caja/test_contexto.py
git commit -m "feat(caja): ContextoApp expone svc_usuarios y usuario_actual

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 12: `DialogoLogin` + arranque con login

**Files:**
- Create: `src/caja/dialogos/dialogo_login.py`
- Modify: `src/caja/__main__.py`
- Test: `tests/caja/test_dialogo_login.py` (crear)

**Interfaces:**
- Consumes: `ServicioUsuarios`, `Usuario`.
- Produces: `DialogoLogin(servicio, parent=None)` con atributos `_nombre`, `_password`, `_estado` (QLineEdit/QLabel), método `_intentar()`, y atributo público `usuario: Usuario | None` (poblado y `accept()` al autenticar).

- [ ] **Step 1: Write the failing test**

Create `tests/caja/test_dialogo_login.py`:

```python
import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from dataclasses import replace  # noqa: E402

from PySide6.QtWidgets import QApplication  # noqa: E402

from core.entidades import Usuario  # noqa: E402
from core.servicio_usuarios import ServicioUsuarios  # noqa: E402
from caja.dialogos.dialogo_login import DialogoLogin  # noqa: E402


class _FakeRepo:
    def __init__(self):
        self._items = {}
        self._hashes = {}
        self._next = 1

    def guardar(self, usuario, hash_password):
        u = replace(usuario, id=self._next)
        self._items[self._next] = u
        self._hashes[self._next] = hash_password
        self._next += 1
        return u

    def por_id(self, id):
        return self._items.get(id)

    def por_nombre(self, nombre):
        return next((u for u in self._items.values() if u.nombre == nombre), None)

    def credencial(self, nombre):
        u = self.por_nombre(nombre)
        return (u, self._hashes[u.id]) if u else None

    def listar(self):
        return list(self._items.values())


def _servicio_con_admin():
    s = ServicioUsuarios(_FakeRepo())
    s.crear("admin", "clave1234", rol="admin")
    return s


def test_login_ok_setea_usuario():
    _app = QApplication.instance() or QApplication([])
    dlg = DialogoLogin(_servicio_con_admin())
    dlg._nombre.setText("admin")
    dlg._password.setText("clave1234")
    dlg._intentar()
    assert dlg.usuario is not None
    assert dlg.usuario.rol == "admin"


def test_login_fallido_muestra_error_y_no_setea_usuario():
    _app = QApplication.instance() or QApplication([])
    dlg = DialogoLogin(_servicio_con_admin())
    dlg._nombre.setText("admin")
    dlg._password.setText("incorrecta")
    dlg._intentar()
    assert dlg.usuario is None
    assert dlg._estado.text() != ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/caja/test_dialogo_login.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'caja.dialogos.dialogo_login'`

- [ ] **Step 3: Write the dialog**

Create `src/caja/dialogos/dialogo_login.py`:

```python
"""Diálogo de login. Autentica contra ServicioUsuarios; el login es el gate real."""
from __future__ import annotations

from PySide6.QtWidgets import QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout

from core.entidades import Usuario
from core.servicio_usuarios import ServicioUsuarios


class DialogoLogin(QDialog):
    def __init__(self, servicio: ServicioUsuarios, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Ingreso")
        self._servicio = servicio
        self.usuario: Usuario | None = None

        self._nombre = QLineEdit()
        self._nombre.setPlaceholderText("Usuario")
        self._password = QLineEdit()
        self._password.setPlaceholderText("Contraseña")
        self._password.setEchoMode(QLineEdit.Password)
        self._password.returnPressed.connect(self._intentar)
        self._estado = QLabel("")
        self._estado.setObjectName("error")
        boton = QPushButton("Ingresar")
        boton.setObjectName("primario")
        boton.clicked.connect(self._intentar)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("POS — Carnes y Frutas"))
        layout.addWidget(self._nombre)
        layout.addWidget(self._password)
        layout.addWidget(self._estado)
        layout.addWidget(boton)

    def _intentar(self) -> None:
        usuario = self._servicio.autenticar(
            self._nombre.text().strip(), self._password.text())
        if usuario is None:
            self._estado.setText("Usuario o contraseña incorrectos")
            return
        self.usuario = usuario
        self.accept()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/caja/test_dialogo_login.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Wire the login into `__main__`**

Replace `src/caja/__main__.py` `main` with:

```python
"""Entry point: python -m caja [ruta_db]."""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QDialog

from caja.contexto import ContextoApp
from caja.dialogos.dialogo_login import DialogoLogin
from caja.tema import carga_tema
from caja.ventana_principal import VentanaPrincipal


def main(ruta_db: str = "pos.db") -> int:
    app = QApplication(sys.argv)
    carga_tema(app)
    ctx = ContextoApp.crear(ruta_db)
    login = DialogoLogin(ctx.svc_usuarios)
    if login.exec() != QDialog.Accepted:
        return 0
    ctx.usuario_actual = login.usuario
    ventana = VentanaPrincipal(ctx)
    ventana.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "pos.db"))
```

- [ ] **Step 6: Commit**

```bash
git add src/caja/dialogos/dialogo_login.py src/caja/__main__.py tests/caja/test_dialogo_login.py
git commit -m "feat(caja): DialogoLogin + arranque de la app con autenticación

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 13: Cablear `usuario_id` en venta, cierre y devolución

**Files:**
- Modify: `src/caja/pantalla_venta.py` (`_registrar_pagos`)
- Modify: `src/caja/pantalla_cierre.py` (`_abrir`, `_cerrar`)
- Modify: `src/caja/pantalla_devoluciones.py` (`_procesar`)
- Test: `tests/caja/test_pantalla_venta.py` (añadir), `tests/caja/test_pantalla_cierre.py` (añadir)

**Interfaces:**
- Consumes: `ContextoApp.usuario_actual_id` (Task 11).
- Produces: las ventas/sesiones/devoluciones creadas desde la UI llevan `usuario_id = ctx.usuario_actual_id`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/caja/test_pantalla_venta.py`:

```python
from caja.bootstrap import ADMIN_POR_DEFECTO  # noqa: E402


def test_cobro_registra_usuario_actual():
    _app = QApplication.instance() or QApplication([])
    ctx = _ctx()
    nombre, password = ADMIN_POR_DEFECTO
    ctx.usuario_actual = ctx.svc_usuarios.autenticar(nombre, password)
    ctx.svc_caja.abrir(fecha=datetime.now(), monto_inicial=Decimal("0"))
    win = PantallaVenta(ctx)
    win.al_mostrar()
    win._agregar_producto(ctx.repo_productos.por_codigo("7700006"))
    sesion = ctx.repo_sesiones.abierta()
    from core.entidades import Pago
    win._registrar_pagos([Pago(medio_pago_id=1, monto=Decimal("2500"))], sesion.id)
    venta = ctx.repo_ventas.ventas_de_sesion(sesion.id)[0]
    assert venta.usuario_id == ctx.usuario_actual.id
```

Append to `tests/caja/test_pantalla_cierre.py` (adjust the ctx/import helpers to match this file's existing style):

```python
from caja.bootstrap import ADMIN_POR_DEFECTO  # noqa: E402


def test_abrir_caja_registra_usuario_actual():
    _app = QApplication.instance() or QApplication([])
    ctx = ContextoApp.crear(":memory:")
    nombre, password = ADMIN_POR_DEFECTO
    ctx.usuario_actual = ctx.svc_usuarios.autenticar(nombre, password)
    win = PantallaCierre(ctx)
    win.al_mostrar()
    win._monto_inicial.setValue(0)
    win._abrir()
    assert ctx.repo_sesiones.abierta().usuario_id == ctx.usuario_actual.id
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/caja/test_pantalla_venta.py -k usuario tests/caja/test_pantalla_cierre.py -k usuario -v`
Expected: FAIL — `usuario_id` llega como `None`.

- [ ] **Step 3: Wire `pantalla_venta._registrar_pagos`**

In `src/caja/pantalla_venta.py`, change the `confirmar` call:

```python
    def _registrar_pagos(self, pagos: list[Pago], sesion_id: int) -> None:
        venta = self._venta.confirmar(
            fecha=datetime.now(), caja_sesion_id=sesion_id,
            usuario_id=self._ctx.usuario_actual_id)
```

- [ ] **Step 4: Wire `pantalla_cierre`**

In `src/caja/pantalla_cierre.py`, `_abrir`:

```python
            self._ctx.svc_caja.abrir(
                fecha=datetime.now(),
                monto_inicial=Decimal(str(int(self._monto_inicial.value()))),
                usuario_id=self._ctx.usuario_actual_id)
```

`_cerrar` **no cambia**: `ServicioCaja.cerrar(*, sesion_id, fecha, monto_contado)` no recibe `usuario_id` y la sesión ya conserva el `usuario_id` fijado en la apertura (`replace(sesion, ...)`). No lo toques.

- [ ] **Step 5: Wire `pantalla_devoluciones._procesar`**

In `src/caja/pantalla_devoluciones.py`, add `usuario_id` to the `devolver` call:

```python
            self._ctx.svc_devolucion.devolver(
                self._venta.id, self._items_a_devolver(), pagos,
                fecha=datetime.now(),
                caja_sesion_id=sesion.id if sesion else None,
                usuario_id=self._ctx.usuario_actual_id)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m pytest tests/caja/test_pantalla_venta.py tests/caja/test_pantalla_cierre.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/caja/pantalla_venta.py src/caja/pantalla_cierre.py src/caja/pantalla_devoluciones.py tests/caja/test_pantalla_venta.py tests/caja/test_pantalla_cierre.py
git commit -m "feat(caja): cablear usuario_id en venta, cierre y devolución

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 14: Cliente + descuento en la pantalla de venta

**Files:**
- Modify: `src/caja/pantalla_venta.py`
- Test: `tests/caja/test_pantalla_venta.py` (añadir)

**Interfaces:**
- Consumes: `ContextoApp.repo_clientes`, `svc_clientes.consumidor_final()`, `establecer_descuento`, `puede`, `ACCION_DESCUENTO_MANUAL`.
- Produces: selector de cliente (`_combo_cliente`) con default consumidor final; campo de descuento manual (`_descuento_manual`, `QDoubleSpinBox`) visible solo si el rol puede; `_cliente` (Cliente actual); la venta se confirma con `cliente_id` y aplica el `descuento_pct` correspondiente.

- [ ] **Step 1: Write the failing test**

Append to `tests/caja/test_pantalla_venta.py`:

```python
from decimal import Decimal as _D  # noqa: E402

from core.entidades import Cliente, Usuario  # noqa: E402


def test_seleccionar_cliente_con_descuento_aplica_al_total():
    _app = QApplication.instance() or QApplication([])
    ctx = _ctx()
    ctx.usuario_actual = Usuario(nombre="admin", rol="admin", id=1)
    cliente = ctx.repo_clientes.guardar(
        Cliente(identificacion="900", nombre="Mayorista", descuento_pct=_D("0.1")))
    win = PantallaVenta(ctx)
    win.al_mostrar()
    idx = win._combo_cliente.findData(cliente.id)
    win._combo_cliente.setCurrentIndex(idx)  # dispara _al_cambiar_cliente
    win._agregar_producto(ctx.repo_productos.por_codigo("7700006"))  # 2500
    assert win._total_actual() == _D("2250")


def test_descuento_manual_visible_solo_para_admin():
    _app = QApplication.instance() or QApplication([])
    ctx_admin = _ctx()
    ctx_admin.usuario_actual = Usuario(nombre="a", rol="admin", id=1)
    win_admin = PantallaVenta(ctx_admin)
    assert win_admin._descuento_manual.isVisibleTo(win_admin) is True

    ctx_cajero = _ctx()
    ctx_cajero.usuario_actual = Usuario(nombre="c", rol="cajero", id=2)
    win_cajero = PantallaVenta(ctx_cajero)
    assert win_cajero._descuento_manual.isVisibleTo(win_cajero) is False


def test_default_es_consumidor_final():
    _app = QApplication.instance() or QApplication([])
    ctx = _ctx()
    ctx.usuario_actual = Usuario(nombre="admin", rol="admin", id=1)
    win = PantallaVenta(ctx)
    win.al_mostrar()
    assert win._cliente.identificacion == "222222222222"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/caja/test_pantalla_venta.py -k "cliente or descuento_manual" -v`
Expected: FAIL — `PantallaVenta` no tiene `_combo_cliente` / `_descuento_manual`.

- [ ] **Step 3: Add imports and widgets to `PantallaVenta.__init__`**

In `src/caja/pantalla_venta.py`, extend the Qt imports with `QComboBox` and `QDoubleSpinBox`:

```python
from PySide6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QGridLayout, QHBoxLayout, QInputDialog, QLabel, QLineEdit,
    QMessageBox, QPushButton, QScrollArea, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)
```

Add domain imports:

```python
from core.permisos import ACCION_DESCUENTO_MANUAL, puede
```

In `__init__`, initialise `self._cliente = None`, and build the widgets. Add the combo + discount field to the right panel (`der`) above the `Carrito` label. Insert after `self._venta = ctx.nueva_venta()`:

```python
        self._cliente = None
        rol = ctx.usuario_actual.rol if ctx.usuario_actual else "cajero"
```

And build the controls (place with the other `der` widgets, before `der.addWidget(QLabel("Carrito"))`):

```python
        self._combo_cliente = QComboBox()
        self._combo_cliente.currentIndexChanged.connect(self._al_cambiar_cliente)
        self._descuento_manual = QDoubleSpinBox()
        self._descuento_manual.setSuffix(" %")
        self._descuento_manual.setRange(0, 99)
        self._descuento_manual.setVisible(puede(rol, ACCION_DESCUENTO_MANUAL))
        self._descuento_manual.valueChanged.connect(self._al_cambiar_descuento_manual)
```

Then add them to the `der` layout (before the `Carrito` label):

```python
        der.addWidget(QLabel("Cliente"))
        der.addWidget(self._combo_cliente)
        der.addWidget(self._descuento_manual)
```

- [ ] **Step 4: Add the client/discount methods**

Add these methods to `PantallaVenta`:

```python
    def _cargar_clientes(self) -> None:
        self._combo_cliente.blockSignals(True)
        self._combo_cliente.clear()
        for c in self._ctx.repo_clientes.listar():
            self._combo_cliente.addItem(c.nombre, c.id)
        cf = self._ctx.svc_clientes.consumidor_final()
        idx = self._combo_cliente.findData(cf.id)
        if idx >= 0:
            self._combo_cliente.setCurrentIndex(idx)
        self._combo_cliente.blockSignals(False)
        self._cliente = cf
        self._venta.establecer_descuento(cf.descuento_pct)

    @Slot()
    def _al_cambiar_cliente(self) -> None:
        cid = self._combo_cliente.currentData()
        self._cliente = self._ctx.repo_clientes.por_id(cid) if cid is not None else None
        pct = self._cliente.descuento_pct if self._cliente else CERO
        self._venta.establecer_descuento(pct)
        self._descuento_manual.setValue(0)
        self._refrescar_carrito()

    @Slot()
    def _al_cambiar_descuento_manual(self) -> None:
        pct = Decimal(str(self._descuento_manual.value())) / Decimal("100")
        self._venta.establecer_descuento(pct)
        self._refrescar_carrito()
```

- [ ] **Step 5: Populate clients on show, keep discount on rebuild, pass `cliente_id`**

In `al_mostrar`, add a call to `_cargar_clientes()` (before `self._escaneo.setFocus()`):

```python
    def al_mostrar(self) -> None:
        self._construir_chips()
        self._construir_grid()
        self._cargar_clientes()
        self._refrescar_carrito()
        self._escaneo.setFocus()
```

In `_quitar_seleccionado`, after `self._venta = self._ctx.nueva_venta()`, re-apply the current discount so removing a line does not drop it:

```python
        self._venta = self._ctx.nueva_venta()
        self._venta.establecer_descuento(
            self._cliente.descuento_pct if self._cliente else CERO)
```

In `_registrar_pagos`, pass the client id, and re-apply discount to the fresh venta after the sale:

```python
    def _registrar_pagos(self, pagos: list[Pago], sesion_id: int) -> None:
        venta = self._venta.confirmar(
            fecha=datetime.now(), caja_sesion_id=sesion_id,
            cliente_id=self._cliente.id if self._cliente else None,
            usuario_id=self._ctx.usuario_actual_id)
        try:
            self._ctx.svc_registro.registrar(venta, pagos)
        except Exception as exc:  # noqa: BLE001 — error inesperado al cajero
            QMessageBox.critical(self, "Error al registrar", str(exc))
            return
        self._venta = self._ctx.nueva_venta()
        self._venta.establecer_descuento(
            self._cliente.descuento_pct if self._cliente else CERO)
        self._refrescar_carrito()
        self._escaneo.setFocus()
        self.caja_cambiada.emit()
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m pytest tests/caja/test_pantalla_venta.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/caja/pantalla_venta.py tests/caja/test_pantalla_venta.py
git commit -m "feat(caja): selección de cliente + descuento (auto y manual) en la venta

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 15: `PantallaUsuarios` (admin-only) + gating del rail

**Files:**
- Create: `src/caja/pantalla_usuarios.py`
- Modify: `src/caja/ventana_principal.py`
- Modify: `src/caja/pantalla_inventario.py` (gate de edición)
- Test: `tests/caja/test_pantalla_usuarios.py` (crear), `tests/caja/test_ventana_principal.py` (añadir)

**Interfaces:**
- Consumes: `ServicioUsuarios`, `puede`, `ACCION_GESTIONAR_USUARIOS`, `ACCION_EDITAR_PRODUCTOS`.
- Produces: `PantallaUsuarios(servicio)` con `_nombre`, `_password`, `_rol` (QComboBox), `_tabla`, `_estado`, método `_al_crear()`; el rail solo muestra "Usuarios" a admin; los botones de crear/editar producto se ocultan al cajero.

- [ ] **Step 1: Write the failing test (pantalla)**

Create `tests/caja/test_pantalla_usuarios.py`:

```python
import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from dataclasses import replace  # noqa: E402

from PySide6.QtWidgets import QApplication  # noqa: E402

from core.servicio_usuarios import ServicioUsuarios  # noqa: E402
from caja.pantalla_usuarios import PantallaUsuarios  # noqa: E402


class _FakeRepo:
    def __init__(self):
        self._items = {}
        self._hashes = {}
        self._next = 1

    def guardar(self, usuario, hash_password):
        u = replace(usuario, id=self._next)
        self._items[self._next] = u
        self._hashes[self._next] = hash_password
        self._next += 1
        return u

    def por_id(self, id):
        return self._items.get(id)

    def por_nombre(self, nombre):
        return next((u for u in self._items.values() if u.nombre == nombre), None)

    def credencial(self, nombre):
        u = self.por_nombre(nombre)
        return (u, self._hashes[u.id]) if u else None

    def listar(self):
        return list(self._items.values())


def test_crear_agrega_usuario_a_la_tabla():
    _app = QApplication.instance() or QApplication([])
    win = PantallaUsuarios(ServicioUsuarios(_FakeRepo()))
    win._nombre.setText("ana")
    win._password.setText("clave1234")
    win._al_crear()
    assert win._tabla.rowCount() == 1
    assert "ana" in win._tabla.item(0, 0).text()


def test_crear_sin_password_muestra_error():
    _app = QApplication.instance() or QApplication([])
    win = PantallaUsuarios(ServicioUsuarios(_FakeRepo()))
    win._nombre.setText("ana")
    win._al_crear()
    assert "Error" in win._estado.text()
    assert win._tabla.rowCount() == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/caja/test_pantalla_usuarios.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'caja.pantalla_usuarios'`

- [ ] **Step 3: Write the screen**

Create `src/caja/pantalla_usuarios.py`:

```python
"""Pantalla CRUD de usuarios (admin). La lógica vive en ServicioUsuarios (core)."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from core.entidades import ROLES
from core.servicio_usuarios import ServicioUsuarios


class PantallaUsuarios(QWidget):
    def __init__(self, servicio: ServicioUsuarios) -> None:
        super().__init__()
        self._servicio = servicio
        self.setWindowTitle("Usuarios")

        self._nombre = QLineEdit()
        self._nombre.setPlaceholderText("Usuario")
        self._password = QLineEdit()
        self._password.setPlaceholderText("Contraseña")
        self._password.setEchoMode(QLineEdit.Password)
        self._rol = QComboBox()
        self._rol.addItems(ROLES)
        boton = QPushButton("Crear")
        boton.clicked.connect(self._al_crear)

        self._tabla = QTableWidget(0, 2)
        self._tabla.setHorizontalHeaderLabels(["Usuario", "Rol"])
        self._estado = QLabel("")
        self._estado.setObjectName("error")

        fila = QHBoxLayout()
        fila.addWidget(self._nombre)
        fila.addWidget(self._password)
        fila.addWidget(self._rol)
        fila.addWidget(boton)

        layout = QVBoxLayout(self)
        layout.addLayout(fila)
        layout.addWidget(self._tabla)
        layout.addWidget(self._estado)

        self._refrescar()

    def _al_crear(self) -> None:
        try:
            self._servicio.crear(
                self._nombre.text().strip(), self._password.text(),
                rol=self._rol.currentText())
        except ValueError as exc:
            self._estado.setText(f"Error: {exc}")
            return
        self._estado.setText("")
        self._nombre.clear()
        self._password.clear()
        self._refrescar()

    def _refrescar(self) -> None:
        self._tabla.setRowCount(0)
        for u in self._servicio.listar():
            fila = self._tabla.rowCount()
            self._tabla.insertRow(fila)
            self._tabla.setItem(fila, 0, QTableWidgetItem(u.nombre))
            self._tabla.setItem(fila, 1, QTableWidgetItem(u.rol))
```

- [ ] **Step 4: Run pantalla tests**

Run: `python -m pytest tests/caja/test_pantalla_usuarios.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Write the failing test (rail gating)**

Append to `tests/caja/test_ventana_principal.py` (match the file's existing imports/helpers; `ContextoApp` and `VentanaPrincipal` are already imported there):

```python
from core.entidades import Usuario  # noqa: E402


def _tooltips(win):
    return {b.toolTip() for b in win._botones}


def test_rail_muestra_usuarios_solo_a_admin():
    _app = QApplication.instance() or QApplication([])
    ctx = ContextoApp.crear(":memory:")
    ctx.usuario_actual = Usuario(nombre="admin", rol="admin", id=1)
    assert "Usuarios" in _tooltips(VentanaPrincipal(ctx))


def test_rail_oculta_usuarios_a_cajero():
    _app = QApplication.instance() or QApplication([])
    ctx = ContextoApp.crear(":memory:")
    ctx.usuario_actual = Usuario(nombre="c", rol="cajero", id=2)
    assert "Usuarios" not in _tooltips(VentanaPrincipal(ctx))
```

- [ ] **Step 6: Run to verify it fails**

Run: `python -m pytest tests/caja/test_ventana_principal.py -k usuarios -v`
Expected: FAIL — "Usuarios" no está en el rail.

- [ ] **Step 7: Gate the rail in `ventana_principal.py`**

Add imports:

```python
from caja.pantalla_usuarios import PantallaUsuarios
from core.permisos import ACCION_GESTIONAR_USUARIOS, puede
```

Extend `_DEFINICION` with a 4th element `permiso` (None = siempre visible), and add the Usuarios entry:

```python
# (icono, tooltip, factory, permiso)
_DEFINICION = [
    ("venta", "Venta", PantallaVenta, None),
    ("inventario", "Inventario", PantallaInventario, None),
    ("clientes", "Clientes", PantallaClientes, None),
    ("devoluciones", "Devoluciones", PantallaDevoluciones, None),
    ("reportes", "Reportes", PantallaReportes, None),
    ("cierre", "Cierre", PantallaCierre, None),
    ("clientes", "Usuarios", PantallaUsuarios, ACCION_GESTIONAR_USUARIOS),
]
```

(El icono `usuarios` puede no existir en el tema; reutiliza `clientes` para no romper `icono()`. Si existe un icono `usuarios`, úsalo.)

In `__init__`, filter by permission. Replace the `for` loop header:

```python
        rol = ctx.usuario_actual.rol if ctx.usuario_actual else "cajero"
        visibles = [d for d in _DEFINICION if d[3] is None or puede(rol, d[3])]
        for i, (ic, tip, factory, _permiso) in enumerate(visibles):
```

- [ ] **Step 8: Update `_construir_pantalla` for `PantallaUsuarios`**

In `ventana_principal.py`, `_construir_pantalla`, handle the new factory:

```python
    def _construir_pantalla(self, factory) -> QWidget:
        if factory is PantallaClientes:
            pantalla = factory(self._ctx.svc_clientes)
        elif factory is PantallaUsuarios:
            pantalla = factory(self._ctx.svc_usuarios)
        else:
            pantalla = factory(self._ctx)
        if hasattr(pantalla, "caja_cambiada"):
            pantalla.caja_cambiada.connect(self._refrescar_estado)
        return pantalla
```

- [ ] **Step 9: Gate product editing in `pantalla_inventario.py`**

Add imports:

```python
from core.permisos import ACCION_EDITAR_PRODUCTOS, puede
```

In `__init__`, keep the "Nuevo producto" button as an attribute and hide the edit controls for non-admins. Replace the button setup:

```python
        self._boton_nuevo = QPushButton("Nuevo producto")
        self._boton_nuevo.clicked.connect(self._crear_producto)
        self._boton_editar = QPushButton("Editar")
        self._boton_editar.clicked.connect(self._editar_producto)
        self._boton_mov = QPushButton("Movimiento")
        self._boton_mov.clicked.connect(self._registrar_movimiento)

        rol = ctx.usuario_actual.rol if ctx.usuario_actual else "cajero"
        puede_editar = puede(rol, ACCION_EDITAR_PRODUCTOS)
        self._boton_nuevo.setVisible(puede_editar)
        self._boton_editar.setVisible(puede_editar)
```

Update the `barra.addWidget(...)` lines to use `self._boton_nuevo`:

```python
        barra.addWidget(self._boton_nuevo)
        barra.addWidget(self._boton_editar)
        barra.addWidget(self._boton_mov)
```

- [ ] **Step 10: Run tests to verify they pass**

Run: `python -m pytest tests/caja/test_ventana_principal.py tests/caja/test_pantalla_usuarios.py tests/caja/test_pantalla_inventario.py -v`
Expected: PASS

- [ ] **Step 11: Commit**

```bash
git add src/caja/pantalla_usuarios.py src/caja/ventana_principal.py src/caja/pantalla_inventario.py tests/caja/test_pantalla_usuarios.py tests/caja/test_ventana_principal.py
git commit -m "feat(caja): PantallaUsuarios (admin) + gating del rail y edición de inventario

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 16: Cierre — suite completa y README

**Files:**
- Modify: `docs/README-pos.md`

**Interfaces:**
- Consumes: el conteo real de la suite tras Tasks 1–15.
- Produces: fila "Usuarios+Cliente" del README apuntando a spec/plan (estado 🟡 en diseño) y conteo de suite actualizado.

- [ ] **Step 1: Run the full suite and record the count**

Run: `python -m pytest -q`
Expected: PASS. Anota el conteo exacto (p. ej. `2XX passed`) para el siguiente paso.

- [ ] **Step 2: Update the "Usuarios+Cliente" row and suite count**

In `docs/README-pos.md`, change the row:

```markdown
| Usuarios+Cliente | Usuarios/roles + selección de cliente y descuento en la venta | 🟡 en diseño (spec/plan) |
```

to:

```markdown
| Usuarios+Cliente | Usuarios/roles (login, permisos) + cliente y descuento en la venta ([spec](superpowers/specs/2026-06-30-usuarios-cliente-descuento-design.md) · [plan](superpowers/plans/2026-06-30-usuarios-cliente-descuento.md)) | 🟡 en diseño |
```

Update the suite line with the real count from Step 1, e.g.:

```markdown
Suite: **2XX passed** (`python -m pytest -q`, 2026-06-30).
```

- [ ] **Step 3: Commit**

```bash
git add docs/README-pos.md
git commit -m "docs: README apunta a spec/plan de Usuarios+Cliente y actualiza conteo de suite

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Notas de cierre

- **Enforcement de permisos:** hoy vive en la UI (login + `puede()` gatea controles y rail). Mover el enforcement a la capa de servicios es endurecimiento futuro (fuera de alcance, Ponytail).
- **Contraseña admin por defecto** (`admin`/`admin1234`): documentar que debe cambiarse; el cambio de contraseña autoservicio queda fuera de alcance.
- **Descuento manual sin auditoría separada:** se persiste `ventas.descuento_pct`; el monto descontado del recibo es derivable de `Σ round(precio_unit × cantidad_o_peso) − total`. No hay columna por línea (elección de alcance).
- **`bloqueado_edicion`:** ahora bloquea `actualizar`; no impide vender al cliente.
```
