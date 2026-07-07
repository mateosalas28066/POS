# Diseño — Aislamiento multi-tenant a nivel app (Fase 1 de roles/RLS)

> Fecha: 2026-07-07
> Repos: `w:\pos-plataforma-web` (backend FastAPI + Postgres Supabase). Sin cambios en el POS.
> Epic sugerido para el plan: **NUBE3** (tasks `NUBE3.1`, `NUBE3.2`, …) — prefijo único, no colisiona
> con NUBE0/1, NUBE2A, NUBE2B (ver `planes-pos`).
> Antecede a: Fase 2 (roles web) y Fase 3 (RLS Postgres), cada una con su propio spec+plan.

## 1. Contexto y problema

La plataforma web multi-local tiene hoy dos vías de autenticación (`backend/app/auth.py`):

- **Token de servicio por local** (POS → backend): `Authorization: Bearer <local_id>:<token>`,
  comparación HMAC contra `settings.local_tokens`. Identifica inequívocamente al local que empuja.
- **JWT de Supabase** (web): `usuario_web` (cualquier autenticado) y `admin_web` (email ∈
  `ADMIN_EMAILS`). El admin web es el **dueño del negocio** y gestiona **todos** los locales desde
  la consola — su alcance cross-local es intencional.

El backend conecta a Postgres con una **única conexión de servicio**; **no hay RLS**. Por lo tanto,
todo el aislamiento entre locales depende, hoy, de la capa de aplicación.

La revisión final de rama de NUBE2 encontró:

- **(cerrado) Lectura cross-tenant en `/sync/inventario`:** no scopeaba por local; un token de
  local podía leer el delta de inventario de otra ubicación. Corregido (valida que la ubicación
  pertenezca al local o sea bodega compartida, si no 403).
- **(abierto — este spec) Escritura cross-tenant en `/sync/push`:** la materialización confía en el
  `payload` del evento (`payload.local_id`, `origen_id`/`destino_id`) en vez de en el local
  autenticado. Un token de local puede empujar un `catalogo_overlay`/`catalogo_promo`/`venta`/
  `movimiento_inventario` que escribe datos de **otro** local.

`/sync/catalogo` ya valida `local_id == token` (403 si no coincide). Así que **las lecturas ya están
cerradas**; falta cerrar la **escritura**.

## 2. Objetivo y no-goals

**Objetivo:** cerrar el hueco de escritura cross-tenant en las rutas con token de POS, con una
regla de propiedad por evento, sin tocar el modelo de conexión ni introducir roles nuevos. Ponytail:
mínimo código, reusa el flujo de `/sync/push` y el patrón de tests existente.

**No-goals (specs futuros):**
- **Fase 2 — roles web:** usuarios web con local(es) asignado(s) y roles (`admin`/`operador`/
  `lector`); scoping de `/dashboard/*` e `/inventario/*` por locales asignados.
- **Fase 3 — RLS Postgres:** conexión por request con identidad (claims del JWT / `SET` de tenant),
  políticas RLS por tenant como defensa en profundidad.

## 3. Postura de aislamiento (estado objetivo)

| Ruta | Auth | Regla de aislamiento | Estado |
|---|---|---|---|
| `GET /sync/catalogo` | token POS | `local_id == token` | ✅ ya |
| `GET /sync/inventario` | token POS | ubicación ∈ {local del token, bodega compartida (`local_id IS NULL`)} | ✅ ya |
| `POST /sync/push` | token POS | **regla de propiedad por evento** (§4) | 🔨 este spec |
| `/dashboard/*`, `/catalogo/*`, `/inventario/*` | `admin_web` | cross-local (dueño) — sin cambios | ✅ intencional |

## 4. Regla de propiedad por evento (`/sync/push`, empujado por el local P)

El backend ya conoce `P = local_autenticado`. Para cada evento del lote:

- **`venta`** → aceptar si `payload.local_id == P` **y** la ubicación de `payload.almacen_id`
  pertenece a P. Si no, rechazar.
- **`catalogo_overlay`** / **`catalogo_promo`** → aceptar si `payload.local_id == P`. Si no, rechazar.
- **`catalogo_producto`** (maestro global) → **aceptar** (el maestro es compartido; se conserva la
  materialización LWW existente). *Decisión:* mantener el maestro compartido preserva la edición
  bidireccional del catálogo ya entregada en NUBE2 Ola A (el admin del POS edita un producto →
  outbox → materializa el maestro con LWW). Restringirlo a web-admin regresaría ese flujo.
- **`movimiento_inventario`** — un token de POS solo produce, por diseño (alcance acotado de
  NUBE2B.9), dos formas:
  - **Grupo de traslado** (salida `origen`=P confirmada + entrada `destino`=otra ubicación,
    pendiente): aceptar si el `origen` de la salida pertenece a P. Crear una entrada **pendiente**
    en la ubicación destino es una "oferta" que el destino todavía debe confirmar — por eso es
    legítimo que el origen la cree.
  - **Flip de confirmación** (entrada `destino`=P que pasa `pendiente→confirmado`): aceptar si el
    `destino` de la entrada pertenece a P.
  - Cualquier otro movimiento desde un token de POS (p. ej. una salida/ajuste sobre ubicación
    ajena, o una entrada confirmada directa) → **rechazar**. (Entrada/salida/ajuste/conversión
    directas son operaciones de web-admin, no del POS.)

**Propiedad de ubicación:** `pertenece(ubicacion_id, P)` ⇔ el `local_id` de la fila `ubicaciones`
es `P` **o** es `NULL` (bodega compartida). Se resuelve con un lookup a `ubicaciones`, cacheado por
request (un solo `SELECT id, local_id FROM ubicaciones` al inicio del push, o memoización por id).

## 5. Mecanismo de enforcement — "rechaza solo el evento"

Decisión (usuario): un evento fuera de alcance **no** debe abortar el lote completo (evita el
"poison event" que trancaría el sync del local para siempre), y debe quedar registrado.

Flujo en `push()` (`backend/app/sync.py`), por evento del lote:

1. Insertar en el ledger `eventos_sync` (idempotente por `uuid`, `ON CONFLICT DO NOTHING`) — igual
   que hoy. El evento se **ACKea** siempre (para que el POS no lo reintente en bucle).
2. Si el `uuid` ya existía (`rowcount == 0`) → ya procesado, continuar (idempotencia actual).
3. Evaluar `evento_permitido(conn, P, ev) -> (ok, motivo)`:
   - Si **`ok`** → materializar como hoy (venta/overlay/promo/producto/movimiento).
   - Si **`not ok`** → **no materializar**; marcar `eventos_sync.rechazo_motivo = motivo` para esa
     fila; registrar un `log`. El evento queda aceptado en el ACK pero no aplicado.
4. `commit` al final del lote (los eventos válidos se materializan; los rechazados solo quedan en el
   ledger con su motivo).

**Migración nube 007:** `ALTER TABLE eventos_sync ADD COLUMN rechazo_motivo TEXT;` (NULL = aceptado y
materializado, o pendiente). Auditable con `SELECT uuid, local_id, tipo, rechazo_motivo FROM
eventos_sync WHERE rechazo_motivo IS NOT NULL`.

**Contrato de respuesta:** se conserva `{"aceptados": [...]}` (todos los uuids del lote, incluidos
los rechazados-por-alcance, siguen ACKeados). Se **añade** `"rechazados": [{"uuid", "motivo"}]` para
visibilidad; es aditivo y no rompe a los clientes actuales (el POS ignora campos desconocidos).

**Ubicación del código:** `evento_permitido` vive en la capa de adaptador (`app/sync.py`), no en
`core/` — necesita el lookup de ubicación→local (BD). La lógica de forma del movimiento (distinguir
grupo-traslado vs flip vs otro) es pura y podría apoyarse en un helper, pero se mantiene junto al
resto de la materialización por cohesión.

## 6. Pruebas (backend pytest, patrón `test_sync_push.py`)

Integración real gated por `TEST_DB_URL` (fixture `conn` con dos locales + una bodega compartida):

1. **Traslado cross-local legítimo pasa:** local A empuja el grupo (salida origen=A + entrada
   destino=B pendiente) → ambos se materializan; la entrada queda pendiente en B.
2. **Flip de confirmación solo por el destino:** el flip `pendiente→confirmado` de una entrada de B
   empujado por A (no-destino) → rechazado + ledger marcado; empujado por B → aceptado.
3. **Overlay/promo/venta con `local_id` ajeno → rechazado:** local A empuja overlay con
   `payload.local_id=B` → no materializa, `rechazo_motivo` seteado, y el **resto del lote sí se
   materializa** (comprobar un evento bueno junto a uno malo).
4. **Movimiento no-permitido:** local A empuja una salida directa sobre ubicación de B → rechazado.
5. **Regresión — lote sano intacto:** un lote 100% válido se materializa igual que hoy (ACK +
   `rechazados == []`).
6. **Maestro compartido:** `catalogo_producto` empujado por cualquier local se materializa (LWW),
   confirmando que no se regresó la edición bidireccional de Ola A.

Los tests unitarios con `_ConnFake` existentes se mantienen; los nuevos casos de propiedad requieren
Postgres real (necesitan el lookup de `ubicaciones`), así que van en la sección gated.

## 7. Riesgos y decisiones cerradas

- **Web-admin conserva cross-local** (dueño del negocio) — no se restringe en esta fase.
- **Maestro compartido** (§4) — decisión explícita para no regresar Ola A.
- **Enforcement por-evento** (§5) — evita poison-event; requiere la columna `rechazo_motivo`.
- **Sin cambio de conexión** — RLS real queda para Fase 3; esta fase es defensa a nivel app, que es
  hoy la única capa de aislamiento efectiva (backend usa conexión de servicio).
- **Alcance del POS** — la regla de movimientos asume el alcance acotado de NUBE2B.9 (POS solo
  traslados + confirmaciones). Si en el futuro el POS empuja entradas/salidas directas, la regla
  deberá extenderse (documentado aquí para el que la toque).

## 8. Criterios de aceptación

- `/sync/push` rechaza (sin materializar, con `rechazo_motivo`) todo evento fuera del alcance del
  local autenticado, sin abortar los eventos válidos del mismo lote.
- El traslado cross-local legítimo y su confirmación por el destino siguen funcionando end-to-end.
- Migración 007 aplicada a la BD real (patrón de despliegue NUBE, ver `README-pos.md`).
- Suite backend verde con `TEST_DB_URL`; sin cambios en la suite del POS.
- Fila NUBE en `README-pos.md` actualizada con la fase de aislamiento.
