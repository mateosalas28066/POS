# Aislamiento multi-tenant en `/sync/push` (NUBE3) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **ESTADO: COMPLETO (2026-07-08).** Las 5 tasks (NUBE3.1–NUBE3.5) están implementadas, probadas
> (backend **77 passed** con `TEST_DB_URL`; sin ella 43 passed, 34 skipped) y **desplegadas**:
> migración 007 (`eventos_sync.rechazo_motivo`) aplicada a la **BD real** y **verificada en vivo**
> contra Postgres real vía `/sync/push` (venta legítima materializa con `rechazados==[]`; evento con
> local/almacén ajeno marca `rechazo_motivo` y **no** materializa, sin romper el lote). Fila NUBE3 ✅
> en `docs/README-pos.md`. Implementación en `w:\pos-plataforma-web` (master, commits `307ba6a` +
> `d81ec64` + `3cb59a2` + `94eded7`). El POS (`w:\POS`) no se tocó en esta fase.

**Goal:** Cerrar el hueco de escritura cross-tenant en `POST /sync/push` con una regla de propiedad por evento, rechazando solo el evento fuera de alcance (sin abortar el lote) y dejándolo auditable.

**Architecture:** Todo el cambio vive en el adaptador de la nube `w:\pos-plataforma-web\backend` (repo hermano de `w:\POS`). Se agrega una función pura `evento_permitido(mapa, local, ev) -> (ok, motivo)` sobre un mapa `{ubicacion_id: local_id}` cargado una sola vez por push, se cablea en el loop de `push()` entre el ACK idempotente y la materialización, y se persiste el motivo de rechazo en una columna nueva `eventos_sync.rechazo_motivo` (migración 007). El contrato de respuesta añade `rechazados` (aditivo). No se toca el POS (`w:\POS`).

**Tech Stack:** Python 3.11, FastAPI, psycopg (Postgres/Supabase), pytest. Auth de POS: `Authorization: Bearer <local_id>:<token>` → `local_autenticado` devuelve el `local_id` autenticado (`P`).

**Spec de referencia:** [docs/superpowers/specs/2026-07-07-plataforma-web-aislamiento-multitenant-design.md](../specs/2026-07-07-plataforma-web-aislamiento-multitenant-design.md)

## Global Constraints

- **Aislamiento hexagonal:** SQL solo en adaptadores. `evento_permitido` vive en `app/sync.py` (adaptador nube), nunca en `core/`. Requiere el lookup `ubicaciones → local_id`, por eso es del adaptador.
- **Decimal siempre; JSON como str.** LWW por `actualizado_en` (no se cambia la materialización existente).
- **Enforcement "rechaza-solo-el-evento":** un evento fuera de alcance NO aborta el lote; se ACKea igual (para que el POS no lo reintente en bucle), no se materializa, y se marca `eventos_sync.rechazo_motivo`.
- **Propiedad de ubicación:** `pertenece(ubicacion_id, P)` ⇔ la fila `ubicaciones` tiene `local_id == P` **o** `local_id IS NULL` (bodega compartida).
- **Contrato aditivo:** la respuesta conserva `{"aceptados": [...]}` (todos los uuids, incluidos los rechazados-por-alcance) y **añade** `{"rechazados": [{"uuid", "motivo"}]}`. El POS ignora campos desconocidos.
- **Maestro compartido:** `catalogo_producto` se acepta desde cualquier local (LWW). Esa rama es la costura única para una futura restricción a web-admin (cambiar un solo retorno).
- **Ponytail / TDD / commits frecuentes.** **NO merge ni push a ningún repo sin preguntar.** Aplicar la migración 007 a la BD real es un paso de despliegue que **requiere confirmación explícita del usuario**.

**Baseline antes de tocar código** (correr y confirmar verde):
```bash
cd "w:/pos-plataforma-web/backend" && .venv/Scripts/python -m pytest -q
```
Esperado hoy: **18 passed, 4 skipped** sin `TEST_DB_URL` (con `TEST_DB_URL` al pooler: 22 passed).

---

### Task NUBE3.1: Migración 007 `eventos_sync.rechazo_motivo`

**Files:**
- Create: `w:\pos-plataforma-web\backend\migraciones\007_rechazo_motivo.sql`
- Test: `w:\pos-plataforma-web\backend\tests\test_migraciones.py` (Modify: añadir `test_migracion_007_rechazo_motivo`)

**Interfaces:**
- Produces: columna `eventos_sync.rechazo_motivo TEXT` (NULL = aceptado/materializado o pendiente; no-NULL = rechazado por alcance, no aplicado). El runner `aplicar_migraciones` la recoge automáticamente por orden de nombre de archivo (`*.sql` ordenados).

- [x] **Step 1: Write the failing test**

En `tests/test_migraciones.py`, añadir al final:

```python
def test_migracion_007_rechazo_motivo(conn_migrada):
    cols = {r[0] for r in conn_migrada.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name='eventos_sync'")}
    assert "rechazo_motivo" in cols
```

- [x] **Step 2: Run test to verify it fails**

Run: `cd "w:/pos-plataforma-web/backend" && TEST_DB_URL=<pooler> .venv/Scripts/python -m pytest tests/test_migraciones.py::test_migracion_007_rechazo_motivo -v`
Expected: FAIL — `assert 'rechazo_motivo' in {...}` (columna aún no existe). *(Sin `TEST_DB_URL` el test se SKIPea; entonces valida el archivo SQL por inspección y sigue.)*

- [x] **Step 3: Create the migration**

`migraciones/007_rechazo_motivo.sql`:

```sql
-- 007_rechazo_motivo.sql
-- NUBE3 (aislamiento multi-tenant a nivel app): motivo de rechazo por-evento en /sync/push.
-- NULL = evento aceptado y materializado (o pendiente); no-NULL = rechazado por alcance, no aplicado.
-- Auditable: SELECT uuid, local_id, tipo, rechazo_motivo FROM eventos_sync WHERE rechazo_motivo IS NOT NULL;
ALTER TABLE eventos_sync ADD COLUMN rechazo_motivo TEXT;
```

- [x] **Step 4: Run test to verify it passes**

Run: `cd "w:/pos-plataforma-web/backend" && TEST_DB_URL=<pooler> .venv/Scripts/python -m pytest tests/test_migraciones.py -v`
Expected: PASS (incluye `test_migraciones_idempotentes`, que re-aplica sin fallar).

- [x] **Step 5: Commit**

```bash
cd "w:/pos-plataforma-web/backend"
git add migraciones/007_rechazo_motivo.sql tests/test_migraciones.py
git commit -m "feat(nube3): migracion 007 eventos_sync.rechazo_motivo"
```

---

### Task NUBE3.2: Regla pura de propiedad por evento (`evento_permitido`)

**Files:**
- Modify: `w:\pos-plataforma-web\backend\app\sync.py` (añadir helpers puros; sin tocar `push()` todavía)
- Test: `w:\pos-plataforma-web\backend\tests\test_sync_push.py` (Modify: sección de unitarios puros)

**Interfaces:**
- Consumes: nada de tasks anteriores (funciones puras sobre un `dict`).
- Produces, en `app/sync.py`:
  - `_mapa_ubicaciones(conn) -> dict[int, str | None]` — `{id: local_id}` con un solo `SELECT id, local_id FROM ubicaciones`.
  - `_pertenece(mapa: dict, ubicacion_id, local: str) -> bool`.
  - `evento_permitido(mapa: dict, local: str, ev: dict) -> tuple[bool, str | None]`.
  - `_permitido_movimiento(mapa: dict, local: str, p: dict) -> tuple[bool, str | None]`.

- [x] **Step 1: Write the failing tests**

En `tests/test_sync_push.py`, añadir tras los imports una sección nueva de unitarios puros (no requieren Postgres):

```python
# --- unitarios puros de la regla de propiedad (sin BD) -------------------------

MAPA = {1: "local-01", 2: "local-02", 9: None}   # 9 = bodega compartida (local_id NULL)


def _ev(tipo, payload):
    return {"uuid": "x", "tipo": tipo, "payload": payload}


def test_permitido_maestro_siempre():
    ok, motivo = sync_mod.evento_permitido(MAPA, "local-01", _ev("catalogo_producto", {"id": 5}))
    assert ok and motivo is None


def test_permitido_overlay_propio_vs_ajeno():
    ok, _ = sync_mod.evento_permitido(MAPA, "local-01",
                                      _ev("catalogo_overlay", {"local_id": "local-01"}))
    assert ok
    ok, motivo = sync_mod.evento_permitido(MAPA, "local-01",
                                           _ev("catalogo_promo", {"local_id": "local-02"}))
    assert not ok and "ajeno" in motivo


def test_permitido_venta_almacen_ajeno_rechaza():
    ok, motivo = sync_mod.evento_permitido(MAPA, "local-01",
        _ev("venta", {"local_id": "local-01", "almacen_id": 2}))
    assert not ok and motivo


def test_permitido_venta_bodega_compartida_ok():
    ok, _ = sync_mod.evento_permitido(MAPA, "local-01",
        _ev("venta", {"local_id": "local-01", "almacen_id": 9}))
    assert ok


def test_permitido_mov_salida_origen_propio():
    ok, _ = sync_mod.evento_permitido(MAPA, "local-01", _ev("movimiento_inventario",
        {"tipo": "salida", "origen_id": 1, "grupo_uuid": "g", "estado": "confirmado"}))
    assert ok


def test_permitido_mov_flip_solo_destino():
    base = {"tipo": "entrada", "destino_id": 2, "grupo_uuid": "g", "estado": "confirmado"}
    ok, motivo = sync_mod.evento_permitido(MAPA, "local-01", _ev("movimiento_inventario", base))
    assert not ok and motivo                       # local-01 no es dueño del destino 2
    ok, _ = sync_mod.evento_permitido(MAPA, "local-02", _ev("movimiento_inventario", base))
    assert ok                                       # local-02 sí


def test_permitido_mov_entrada_pendiente_es_oferta():
    ok, _ = sync_mod.evento_permitido(MAPA, "local-01", _ev("movimiento_inventario",
        {"tipo": "entrada", "destino_id": 2, "grupo_uuid": "g", "estado": "pendiente"}))
    assert ok                                       # oferta a otro local, sin efecto en stock


def test_permitido_mov_directo_sin_grupo_rechaza():
    ok, motivo = sync_mod.evento_permitido(MAPA, "local-01", _ev("movimiento_inventario",
        {"tipo": "entrada", "destino_id": 1, "grupo_uuid": None, "estado": "confirmado"}))
    assert not ok and "directo" in motivo


def test_permitido_tipo_desconocido_rechaza():
    ok, motivo = sync_mod.evento_permitido(MAPA, "local-01", _ev("otro", {}))
    assert not ok and motivo
```

- [x] **Step 2: Run tests to verify they fail**

Run: `cd "w:/pos-plataforma-web/backend" && .venv/Scripts/python -m pytest tests/test_sync_push.py -k permitido -v`
Expected: FAIL — `AttributeError: module 'app.sync' has no attribute 'evento_permitido'`.

- [x] **Step 3: Add the pure helpers to `app/sync.py`**

En `app/sync.py`, insertar tras la línea `router = APIRouter()` (antes de `def push`):

```python
# --- regla de propiedad por evento (NUBE3 §4): aislamiento de escritura cross-tenant ----

def _mapa_ubicaciones(conn) -> dict[int, str | None]:
    """{ubicacion_id: local_id} — local_id NULL = bodega compartida. Un solo SELECT por push."""
    return {r[0]: r[1] for r in conn.execute("SELECT id, local_id FROM ubicaciones")}


def _pertenece(mapa: dict[int, str | None], ubicacion_id, local: str) -> bool:
    """La ubicación es del local autenticado o es bodega compartida (local_id NULL)."""
    if ubicacion_id not in mapa:
        return False
    dueno = mapa[ubicacion_id]
    return dueno is None or dueno == local


def evento_permitido(mapa: dict, local: str, ev: dict) -> tuple[bool, str | None]:
    """¿Puede el local autenticado materializar este evento? (True, None) o (False, motivo).
    El rechazo no aborta el lote; se marca en el ledger y se sigue (NUBE3 §5)."""
    tipo = ev["tipo"]
    p = ev["payload"]
    if tipo == "catalogo_producto":
        return True, None          # maestro compartido (LWW). COSTURA: para restringir a
        #                            web-admin en el futuro, cambiar este único retorno.
    if tipo in ("catalogo_overlay", "catalogo_promo"):
        if p.get("local_id") == local:
            return True, None
        return False, f"{tipo}: local_id ajeno"
    if tipo == "venta":
        if p.get("local_id") == local and _pertenece(mapa, p.get("almacen_id"), local):
            return True, None
        return False, "venta: local o almacen ajeno"
    if tipo == "movimiento_inventario":
        return _permitido_movimiento(mapa, local, p)
    return False, f"tipo no soportado: {tipo}"


def _permitido_movimiento(mapa: dict, local: str, p: dict) -> tuple[bool, str | None]:
    """El POS solo produce movimientos con grupo (traslado/conversion) y el flip de
    confirmacion (mismo mov re-enviado como confirmado). Todo movimiento directo
    (sin grupo_uuid: entrada/salida/ajuste sueltos = ops de web-admin) se rechaza."""
    if p.get("grupo_uuid") is None:
        return False, "movimiento directo no permitido desde POS"
    tipo = p.get("tipo")
    if tipo == "salida":                                   # sale de una ubicacion del local
        if _pertenece(mapa, p.get("origen_id"), local):
            return True, None
        return False, "movimiento: salida desde ubicacion ajena"
    if tipo == "entrada":
        if p.get("estado", "confirmado") == "pendiente":
            return True, None                              # oferta de traslado: sin efecto en stock
        if _pertenece(mapa, p.get("destino_id"), local):
            return True, None                              # flip de confirmacion / entrada de conversion
        return False, "movimiento: entrada confirmada sobre destino ajeno"
    return False, f"movimiento: tipo no soportado ({tipo})"
```

> **Nota de diseño (documentar para el revisor):** la entrada **pendiente** de un traslado lleva `origen_id=None` y su `almacen_id`/`destino` es de OTRO local (ver `core.servicio_inventario_ubicaciones.plan_traslado` en `w:\POS`), así que no puede autorizarse por propiedad de ubicación. Se acepta como "oferta" inocua (el stock solo cuenta confirmados; no cambia nada hasta que el **destino** confirme, y ese flip sí exige que el destino sea del local). El residual es que un local podría inyectar una oferta pendiente falsa en la bandeja de otro (molestia, no corrupción de stock) — coincide con la decisión del spec §4; un cross-check del origen del grupo queda como endurecimiento futuro.

- [x] **Step 4: Run tests to verify they pass**

Run: `cd "w:/pos-plataforma-web/backend" && .venv/Scripts/python -m pytest tests/test_sync_push.py -k permitido -v`
Expected: PASS (9 tests).

- [x] **Step 5: Commit**

```bash
cd "w:/pos-plataforma-web/backend"
git add app/sync.py tests/test_sync_push.py
git commit -m "feat(nube3): regla pura evento_permitido de propiedad por evento"
```

---

### Task NUBE3.3: Cablear enforcement en `push()` + respuesta `rechazados`

**Files:**
- Modify: `w:\pos-plataforma-web\backend\app\sync.py:15-41` (función `push`)
- Test: `w:\pos-plataforma-web\backend\tests\test_sync_push.py` (Modify: `_ConnFake`/`_Cursor`, `_lote_mov`, nuevo test de lote mixto)

**Interfaces:**
- Consumes: `_mapa_ubicaciones`, `evento_permitido` (Task NUBE3.2); columna `rechazo_motivo` (Task NUBE3.1).
- Produces: respuesta `{"aceptados": [uuid, ...], "rechazados": [{"uuid": str, "motivo": str}, ...]}`.

- [x] **Step 1: Extender el fake y las tests unitarias existentes (rojo)**

En `tests/test_sync_push.py`, reemplazar la clase `_Cursor` por una iterable y `_ConnFake` para que sirva el `SELECT ... FROM ubicaciones`:

```python
class _Cursor:
    def __init__(self, rowcount=1, filas=()):
        self.rowcount = rowcount
        self._filas = list(filas)

    def __iter__(self):
        return iter(self._filas)

    def fetchone(self):
        return self._filas[0] if self._filas else None


class _ConnFake:
    """Simula la conexión para idempotencia del ledger + mapa de ubicaciones."""

    def __init__(self, ubicaciones=((1, "local-01"),)):
        self.sentencias = []
        self.uuids = set()
        self.ubicaciones = list(ubicaciones)

    def execute(self, sql, params=None):
        self.sentencias.append(sql)
        if "FROM ubicaciones" in sql:
            return _Cursor(filas=self.ubicaciones)
        if "INSERT INTO eventos_sync" in sql:
            uuid = params[0]
            nuevo = uuid not in self.uuids
            self.uuids.add(uuid)
            return _Cursor(1 if nuevo else 0)
        return _Cursor(1)

    def commit(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False
```

Y actualizar `_lote_mov` para que represente una forma legítima del POS (todo movimiento del POS lleva `grupo_uuid`); cambiar la línea `"grupo_uuid": None,` por:

```python
                    "grupo_uuid": "77777777-7777-7777-7777-777777777777",
```

Añadir un test de lote mixto (bueno + malo) al bloque de unitarios con `conn_fake`:

```python
def test_push_rechaza_overlay_ajeno_y_conserva_bueno(conn_fake):
    malo = {"uuid": "cc000000-0000-0000-0000-000000000001", "local_id": "local-01",
            "tipo": "catalogo_overlay", "creado_en": "2026-07-07T10:00:00",
            "payload": {"local_id": "local-02", "producto_id": 1, "precio": "1",
                        "costo": "1", "activo": True, "actualizado_en": "2026-07-07T10:00:00"}}
    lote = {"eventos": [malo, _lote_overlay()["eventos"][0]]}   # malo (ajeno) + bueno (local-01)
    r = TestClient(app).post("/sync/push", json=lote,
                             headers={"Authorization": "Bearer local-01:tok1"})
    body = r.json()
    assert len(body["aceptados"]) == 2                          # ambos ACKeados
    assert [x["uuid"] for x in body["rechazados"]] == [malo["uuid"]]
    ins = [s for s in conn_fake.sentencias if "INSERT INTO productos_local" in s]
    assert len(ins) == 1                                        # solo el bueno materializo
```

- [x] **Step 2: Run to verify red**

Run: `cd "w:/pos-plataforma-web/backend" && .venv/Scripts/python -m pytest tests/test_sync_push.py -v`
Expected: el test nuevo FALLA con `KeyError: 'rechazados'` (o similar); `push()` aún no evalúa la regla ni devuelve `rechazados`.

- [x] **Step 3: Cablear `push()`**

Reemplazar el cuerpo de `push` (`app/sync.py:15-41`) por:

```python
@router.post("/sync/push")
def push(cuerpo: dict, local_id: str = Depends(local_autenticado)) -> dict:
    eventos = cuerpo.get("eventos", [])
    aceptados: list[str] = []
    rechazados: list[dict] = []
    with conectar() as conn:
        mapa = _mapa_ubicaciones(conn)
        for ev in eventos:
            # ledger idempotente: si el uuid ya existia, no reprocesar
            cur = conn.execute(
                "INSERT INTO eventos_sync (uuid, local_id, tipo, payload) "
                "VALUES (%s, %s, %s, %s) ON CONFLICT (uuid) DO NOTHING",
                (ev["uuid"], local_id, ev["tipo"], json.dumps(ev["payload"])))
            aceptados.append(ev["uuid"])          # se ACK aunque ya existiera o se rechace
            if cur.rowcount == 0:
                continue                           # ya materializado antes
            ok, motivo = evento_permitido(mapa, local_id, ev)
            if not ok:
                conn.execute("UPDATE eventos_sync SET rechazo_motivo=%s WHERE uuid=%s",
                             (motivo, ev["uuid"]))
                rechazados.append({"uuid": ev["uuid"], "motivo": motivo})
                continue                           # no materializar; queda auditable en el ledger
            tipo = ev["tipo"]
            if tipo == "venta":
                _materializar_venta(conn, ev["uuid"], ev["payload"])
            elif tipo == "catalogo_producto":
                _upsert_producto_maestro(conn, ev["payload"])
            elif tipo == "catalogo_overlay":
                _upsert_overlay(conn, ev["payload"])
            elif tipo == "catalogo_promo":
                _upsert_promo(conn, ev["payload"])
            elif tipo == "movimiento_inventario":
                _materializar_movimiento(conn, ev["payload"])
        conn.commit()
    return {"aceptados": aceptados, "rechazados": rechazados}
```

- [x] **Step 4: Run to verify green**

Run: `cd "w:/pos-plataforma-web/backend" && .venv/Scripts/python -m pytest tests/test_sync_push.py -v`
Expected: PASS todo el archivo sin `TEST_DB_URL` (unitarios: idempotencia, overlay, movimiento con grupo, lote mixto, y los `-k permitido`). Los gated de integración quedan SKIPeados.

- [x] **Step 5: Commit**

```bash
cd "w:/pos-plataforma-web/backend"
git add app/sync.py tests/test_sync_push.py
git commit -m "feat(nube3): /sync/push aplica propiedad por evento y responde rechazados"
```

---

### Task NUBE3.4: Tests de integración (Postgres real, gated por `TEST_DB_URL`)

**Files:**
- Test: `w:\pos-plataforma-web\backend\tests\test_sync_push.py` (Modify: fixture `conn` + fixture `tokens` + 6 escenarios del spec §6)

**Interfaces:**
- Consumes: `push()` con enforcement (NUBE3.3); migración 007 aplicada por `aplicar_migraciones` en la fixture.

- [x] **Step 1: Ampliar las fixtures compartidas (segundo local + bodega compartida + token)**

Actualizar la fixture `tokens` (autouse) para incluir `local-02`:

```python
@pytest.fixture(autouse=True)
def tokens(monkeypatch):
    monkeypatch.setattr(auth_mod, "settings",
                        Settings(local_tokens={"local-01": "tok1", "local-02": "tok2"}))
```

Y ampliar el sembrado de la fixture `conn` (integración) para dos locales + una bodega compartida (añadir tras el INSERT de `local-01`/ubicación 1 existente):

```python
    c.execute("INSERT INTO locales (local_id, nombre, token_hash) VALUES ('local-02','L2','y')")
    c.execute("INSERT INTO ubicaciones (id, nombre, local_id, tipo) VALUES (2,'Bodega L2','local-02','local')")
    c.execute("INSERT INTO ubicaciones (id, nombre, local_id, tipo) VALUES (9,'Compartida',NULL,'bodega')")
    c.commit()
```

- [x] **Step 2: Escribir los 6 escenarios (rojo si el enforcement estuviera mal; deben pasar con NUBE3.3)**

Añadir al bloque de integración (tras los tests `conn` existentes) un helper y los seis casos del spec §6:

```python
GRUPO = "99999999-9999-9999-9999-999999999999"
SAL = "a1000000-0000-0000-0000-000000000000"   # mov uuid de la salida
ENT = "a2000000-0000-0000-0000-000000000000"   # mov uuid de la entrada


def _mov_evento(evt_uuid, mov_uuid, tipo, *, origen, destino, estado, grupo,
                actualizado_en="2026-07-07T10:00:00+00:00"):
    # el local_id del payload/evento es cosmetico: push() decide propiedad por ubicacion y
    # usa el local AUTENTICADO (header) para el ledger, no este campo.
    return {"uuid": evt_uuid, "local_id": "local-01", "tipo": "movimiento_inventario",
            "creado_en": actualizado_en,
            "payload": {"uuid": mov_uuid, "tipo": tipo, "producto_id": 1, "cantidad": "5",
                        "origen_id": origen, "destino_id": destino, "estado": estado,
                        "grupo_uuid": grupo, "lote_id": None, "ref": None,
                        "fecha": actualizado_en,
                        "almacen_id": destino if tipo == "entrada" else origen,
                        "local_id": "local-01", "actualizado_en": actualizado_en}}


def test_push_traslado_cross_local_legitimo(conn):
    conn.execute("INSERT INTO productos (id, nombre, costo) VALUES (1,'Lomo','1')")
    conn.commit()
    lote = {"eventos": [
        _mov_evento("b1000000-0000-0000-0000-000000000001", SAL, "salida",
                    origen=1, destino=None, estado="confirmado", grupo=GRUPO),
        _mov_evento("b1000000-0000-0000-0000-000000000002", ENT, "entrada",
                    origen=None, destino=2, estado="pendiente", grupo=GRUPO),
    ]}
    r = TestClient(app).post("/sync/push", json=lote,
                             headers={"Authorization": "Bearer local-01:tok1"})
    assert r.json()["rechazados"] == []
    estados = {row[0]: row[1] for row in conn.execute(
        "SELECT uuid::text, estado FROM inventario_movimientos WHERE grupo_uuid=%s", (GRUPO,))}
    assert estados[SAL] == "confirmado" and estados[ENT] == "pendiente"


def test_push_flip_solo_por_destino(conn):
    conn.execute("INSERT INTO productos (id, nombre, costo) VALUES (1,'Lomo','1')")
    conn.commit()
    hdr1 = {"Authorization": "Bearer local-01:tok1"}
    hdr2 = {"Authorization": "Bearer local-02:tok2"}
    # el origen (local-01) crea la entrada pendiente en el destino 2
    TestClient(app).post("/sync/push", json={"eventos": [
        _mov_evento("c1000000-0000-0000-0000-000000000001", ENT, "entrada",
                    origen=None, destino=2, estado="pendiente", grupo=GRUPO)]}, headers=hdr1)
    # flip empujado por local-01 (NO es el destino) -> rechazado, no se aplica
    flip_no = _mov_evento("c1000000-0000-0000-0000-000000000002", ENT, "entrada",
                          origen=None, destino=2, estado="confirmado", grupo=GRUPO,
                          actualizado_en="2026-07-07T11:00:00+00:00")
    r1 = TestClient(app).post("/sync/push", json={"eventos": [flip_no]}, headers=hdr1)
    assert len(r1.json()["rechazados"]) == 1
    assert conn.execute("SELECT estado FROM inventario_movimientos WHERE uuid=%s",
                        (ENT,)).fetchone()[0] == "pendiente"
    assert conn.execute("SELECT rechazo_motivo FROM eventos_sync WHERE uuid=%s",
                        ("c1000000-0000-0000-0000-000000000002",)).fetchone()[0] is not None
    # flip empujado por local-02 (SI es el destino) -> aceptado, confirma
    flip_ok = _mov_evento("c1000000-0000-0000-0000-000000000003", ENT, "entrada",
                          origen=None, destino=2, estado="confirmado", grupo=GRUPO,
                          actualizado_en="2026-07-07T12:00:00+00:00")
    r2 = TestClient(app).post("/sync/push", json={"eventos": [flip_ok]}, headers=hdr2)
    assert r2.json()["rechazados"] == []
    assert conn.execute("SELECT estado FROM inventario_movimientos WHERE uuid=%s",
                        (ENT,)).fetchone()[0] == "confirmado"


def test_push_overlay_ajeno_rechaza_pero_lote_sigue(conn):
    conn.execute("INSERT INTO productos (id, nombre, costo) VALUES (1,'Lomo','1')")
    conn.commit()
    malo = {"uuid": "d1000000-0000-0000-0000-000000000001", "local_id": "local-01",
            "tipo": "catalogo_overlay", "creado_en": "2026-07-07T10:00:00",
            "payload": {"local_id": "local-02", "producto_id": 1, "precio": "5",
                        "costo": "1", "activo": True, "actualizado_en": "2026-07-07T10:00:00"}}
    bueno = {"uuid": "d1000000-0000-0000-0000-000000000002", "local_id": "local-01",
             "tipo": "catalogo_overlay", "creado_en": "2026-07-07T10:00:00",
             "payload": {"local_id": "local-01", "producto_id": 1, "precio": "20000",
                         "costo": "1", "activo": True, "actualizado_en": "2026-07-07T10:00:00"}}
    r = TestClient(app).post("/sync/push", json={"eventos": [malo, bueno]},
                             headers={"Authorization": "Bearer local-01:tok1"})
    assert [x["uuid"] for x in r.json()["rechazados"]] == [malo["uuid"]]
    assert conn.execute("SELECT count(*) FROM productos_local WHERE local_id='local-02'"
                        ).fetchone()[0] == 0                     # ajeno NO materializo
    assert str(conn.execute("SELECT precio FROM productos_local WHERE local_id='local-01' "
                           "AND producto_id=1").fetchone()[0]) == "20000"   # bueno si
    assert conn.execute("SELECT rechazo_motivo FROM eventos_sync WHERE uuid=%s",
                        (malo["uuid"],)).fetchone()[0] is not None


def test_push_salida_sobre_ubicacion_ajena_rechaza(conn):
    conn.execute("INSERT INTO productos (id, nombre, costo) VALUES (1,'Lomo','1')")
    conn.commit()
    ev = _mov_evento("e1000000-0000-0000-0000-000000000001",
                     "e9000000-0000-0000-0000-000000000000", "salida",
                     origen=2, destino=None, estado="confirmado", grupo=GRUPO)  # origen 2 = local-02
    r = TestClient(app).post("/sync/push", json={"eventos": [ev]},
                             headers={"Authorization": "Bearer local-01:tok1"})  # empuja local-01
    assert len(r.json()["rechazados"]) == 1
    assert conn.execute("SELECT count(*) FROM inventario_movimientos WHERE uuid=%s",
                        ("e9000000-0000-0000-0000-000000000000",)).fetchone()[0] == 0


def test_push_lote_sano_intacto_y_rechazados_vacio(conn):
    r = _push(TestClient(app))                                   # venta local-01, almacen 1
    assert r.json()["aceptados"] == [UUID1]
    assert r.json()["rechazados"] == []
    assert conn.execute("SELECT count(*) FROM ventas").fetchone()[0] == 1


def test_push_maestro_compartido_desde_otro_local(conn):
    lote = {"eventos": [{
        "uuid": "f1000000-0000-0000-0000-000000000001", "local_id": "local-02",
        "tipo": "catalogo_producto", "creado_en": "2026-07-07T10:00:00",
        "payload": {"id": 7, "codigo_barras": None, "nombre": "Pernil", "unidad": "kg",
                    "vendido_por_peso": True, "categoria_id": None, "impuesto_id": None,
                    "costo": "8000", "actualizado_en": "2026-07-07T10:00:00"}}]}
    r = TestClient(app).post("/sync/push", json=lote,
                             headers={"Authorization": "Bearer local-02:tok2"})
    assert r.json()["rechazados"] == []
    assert conn.execute("SELECT nombre FROM productos WHERE id=7").fetchone()[0] == "Pernil"
```

- [x] **Step 3: Run the gated suite green**

Run: `cd "w:/pos-plataforma-web/backend" && TEST_DB_URL=<pooler-de-supabase> .venv/Scripts/python -m pytest tests/test_sync_push.py -v`
Expected: PASS todos (unitarios + los 6 de integración). Confirmar además que los tests `conn` preexistentes (venta idempotente, overlay LWW, promo, movimiento+flip) siguen verdes con el sembrado ampliado.

- [x] **Step 4: Run the full backend suite**

Run: `cd "w:/pos-plataforma-web/backend" && TEST_DB_URL=<pooler> .venv/Scripts/python -m pytest -q`
Expected: verde (22+ passed con `TEST_DB_URL`; sin él, los gated se SKIPean).

- [x] **Step 5: Commit**

```bash
cd "w:/pos-plataforma-web/backend"
git add tests/test_sync_push.py
git commit -m "test(nube3): integracion real de propiedad por evento en /sync/push"
```

---

### Task NUBE3.5: Desplegar migración 007 a la BD real + actualizar `README-pos.md`

**Files:**
- Modify: `w:\POS\docs\README-pos.md` (añadir fila NUBE3; actualizar nota de suites)
- Deploy: aplicar migración 007 a la BD real de Supabase (**requiere confirmación explícita del usuario**)

**Interfaces:**
- Consumes: migración 007 (NUBE3.1). No produce código nuevo.

- [x] **Step 1: Actualizar la fila de estado en `README-pos.md`**

Insertar tras la fila `NUBE2·OlaB` (`docs/README-pos.md:58`):

```markdown
| NUBE3 | Aislamiento multi-tenant a nivel app (Fase 1 de roles/RLS): `/sync/push` aplica **regla de propiedad por evento** (`evento_permitido` en `backend/app/sync.py`) — venta/overlay/promo por `local_id==token`, maestro `catalogo_producto` compartido con LWW (costura para restringir a web-admin luego), `movimiento_inventario` solo grupo-traslado (origen del token) o flip de confirmación (destino del token); resto rechazado. Enforcement "rechaza-solo-el-evento" (no aborta el lote; ACK igual, marca `eventos_sync.rechazo_motivo`, migración 007) + respuesta aditiva `rechazados: [{uuid, motivo}]`. Lecturas ya cerradas antes (`/sync/catalogo`, `/sync/inventario`). Fases futuras (specs propios): roles web y RLS Postgres ([spec](superpowers/specs/2026-07-07-plataforma-web-aislamiento-multitenant-design.md) · [plan](superpowers/plans/2026-07-07-plataforma-web-aislamiento-multitenant.md)) | ✅ implementado |
```

Actualizar la línea de suites (`docs/README-pos.md:62`) con el nuevo conteo de backend tras correr `pytest -q` con `TEST_DB_URL` (rellenar el número real observado en NUBE3.4 Step 4).

- [x] **Step 2: Commit de la documentación**

```bash
cd "w:/POS"
git add docs/README-pos.md
git commit -m "docs(nube3): cierra aislamiento multi-tenant en README (fila + suites)"
```

- [x] **Step 3: Desplegar la migración a la BD real (SOLO con visto bueno del usuario)**

> ⚠️ Acción hacia producción. **Preguntar al usuario antes de ejecutar.** Patrón de deploy documentado en `README-pos.md`:

```bash
cd "w:/pos-plataforma-web/backend"
.venv/Scripts/python -c "import psycopg,os; from app.migraciones_runner import aplicar_migraciones; aplicar_migraciones(psycopg.connect(os.environ['SUPABASE_DB_URL']))"
```

Alternativa vía MCP Supabase (`apply_migration` con el SQL de 007). Verificar después:
```sql
SELECT column_name FROM information_schema.columns
WHERE table_name='eventos_sync' AND column_name='rechazo_motivo';
```
Expected: una fila (`rechazo_motivo`).

- [x] **Step 4: Verificación en vivo (opcional pero recomendada)**

Con backend corriendo contra la BD real y el POS real (`w:\POS\iniciar_pos.ps1`): registrar una venta legítima → confirmar `rechazados == []` y que materializa; y (si es fácil de forzar) empujar un evento con `local_id` ajeno → confirmar `rechazo_motivo` seteado en `eventos_sync` y que no materializa. Reportar lo verificado.

---

## Self-Review

**1. Cobertura del spec:**
- §3 tabla de postura → NUBE3.2/3.3 implementan la fila `/sync/push` (las otras filas ya estaban ✅). ✔
- §4 regla por evento (venta, overlay/promo, maestro compartido con costura, movimiento grupo/flip/rechazo) → `evento_permitido` + `_permitido_movimiento` (NUBE3.2), tests puros + integración. ✔
- §5 enforcement rechaza-solo-el-evento (ACK siempre, no aborta lote, marca `rechazo_motivo`, respuesta aditiva `rechazados`) → NUBE3.3. ✔
- §5 migración 007 → NUBE3.1. ✔
- §6 seis escenarios de prueba → NUBE3.4 (traslado legítimo, flip solo-destino, overlay ajeno + resto sigue, movimiento no permitido, lote sano, maestro compartido). ✔
- §8 criterios de aceptación (rechaza sin abortar, traslado+confirmación E2E, migración a BD real, suite verde con `TEST_DB_URL`, fila README) → NUBE3.3/3.4/3.5. ✔

**2. Placeholders:** `<pooler>` / `<pooler-de-supabase>` y el conteo de suites son valores del entorno del usuario (no versionados), señalados explícitamente; no son TODOs de implementación. Todo paso con código muestra el código completo.

**3. Consistencia de tipos:** `evento_permitido(mapa, local, ev) -> (bool, str|None)` y `_permitido_movimiento(mapa, local, p)` se usan con la misma firma en push(), tests puros y comentarios. `_mapa_ubicaciones` devuelve `{int: str|None}`, consumido por `_pertenece`. La respuesta `{"aceptados", "rechazados"}` es consistente entre `push()` y todas las aserciones de test.
