# Prompt handoff — Lote B10-B11 de NUBE2 (cierre de la Ola B) en modo batched

Continúa NUBE2 Ola B en modo batched inline (ver docs/superpowers/prompts/prompt-continuar-nube2-olaB.md
y docs/superpowers/prompts/prompt-continuar-nube2-batched.md).

ESTADO AL ARRANCAR:
- LOTE B1-B3 COMPLETO (migración nube 006 + core inventario multi-ubicación). 006 ya desplegada
  a la BD REAL (/postgres).
- LOTE B4-B6 COMPLETO (backend inventario, pos-plataforma-web master): B.4 endpoints
  /inventario/* (admin: entrada/salida/ajuste/traslado/confirmar/conversion/stock/pendientes) +
  B.5 GET /sync/inventario (delta por cursor por ubicación) + B.6 /sync/push materializa
  movimiento_inventario (append + único flip pendiente→confirmado por ON CONFLICT(uuid)).
- LOTE B7-B9 COMPLETO (POS feature/plataforma-web-fase-0-1): 8592d61 B.7 (migración 013
  ubicaciones+movimientos_ubicacion + RepositorioMovimientosUbicacionSQLite: registrar/
  confirmar/stock(reusa core.stock_por_suma)/movimientos_grupo + aplicar_delta/pendientes/
  cursor/guardar_cursor) + 970f051 B.8 (ClienteSync.pull_inventario por ubicación, avanza
  cursor con el de la respuesta) + ac50efb (serializar_movimiento + permisos
  ACCION_GESTIONAR_INVENTARIO/ACCION_CONFIRMAR_TRASLADO) + 25460e5 (ContextoApp expone
  repo_movimientos_ubicacion/almacen_id/encolar_movimiento) + dd755e8 (UI mínima en
  pantalla_inventario.py: botones Traslado y Pendientes, solo visibles con sync+permiso;
  DialogoTraslado cantidad+destino_id numérico; DialogoBandejaPendientes confirma con flip
  local + evento a la nube). Alcance del POS acotado a propósito: sin selector de ubicaciones,
  sin conversión en la UI del POS (per nota de riesgo del plan).
- Suites verdes: POS 475 passed (452+23 de B7-B9); backend 53 passed con TEST_DB_URL=pos_test
  (sin cambios desde B4-B6, B7-B9 no tocó el repo nube).
- Ledger con el detalle real: w:\POS\.superpowers\sdd\progress.md sección NUBE2 (gitignored).
- Ramas: w:\POS = feature/plataforma-web-fase-0-1; w:\pos-plataforma-web = master. NO merge/push sin preguntar.
- TEST_DB_URL = la SUPABASE_DB_URL de backend/.env con /postgres → /pos_test. La fixture de
  integración hace DROP SCHEMA public CASCADE: solo seguro contra /pos_test, NUNCA contra /postgres.
- ADMIN_EMAILS en backend/.env (no versionado) debe incluir la cuenta real de la web.

SIGUE CON EL LOTE B10-B11 (cierre de la Ola B) del plan
docs/superpowers/plans/2026-07-07-plataforma-web-fase-2-catalogo-inventario.md sección OLA B
(tasks NUBE2B.10 y NUBE2B.11, líneas ~1511-1547):

- **B.10** (pos-plataforma-web, frontend): `Inventario.tsx` (selector de ubicación + formularios
  entrada/salida/ajuste/traslado/conversión, reusando el estilo de `Catalogo.tsx`/`Dashboard.tsx`)
  + `BandejaPendientes.tsx` (lista de traslados pendientes por ubicación + botón Confirmar vía
  `POST /inventario/confirmar`) + vista de stock por ubicación (`GET /inventario/stock`). Enlazar
  pestaña "Inventario" en `App.tsx`. Verificación: `npm run build && npx oxlint` (sin test runner
  de frontend — no inventes infraestructura nueva). Commit:
  `feat(frontend): UI web de inventario (operaciones, bandeja de pendientes, stock por ubicacion)`.

- **B.11** (verificación e2e + cierre de NUBE2): con backend + frontend + (idealmente) dos
  instancias del POS (o simular local A / local B con dos `LOCAL_ID`/`ALMACEN_ID`), en vivo:
  1. Sembrar ubicaciones (local A, local B, una bodega compartida) si no existen ya.
  2. Registrar una **entrada** en la bodega desde la web; confirmar stock por ubicación en la
     web y en Supabase (MCP).
  3. Crear un **traslado cross-local** (local A → local B) desde la web o desde el POS de A
     (botón "Traslado" de B.9). Verificar: sale de A confirmado, entra a B **pendiente**. El
     POS de B baja el delta (ClienteSync de B.8) y lo muestra en su bandeja "Pendientes".
  4. Confirmar el traslado (web o POS de B). Verificar el flip pendiente→confirmado propagado
     por cursor y que el stock de B sube en ambos lados.
  5. Probar una **conversión** (1 salida → N entradas, con merma) y un **ajuste** desde la web.
  6. Correr ambas suites: `cd w:\POS && python -m pytest -q` (≥475) y
     `cd w:\pos-plataforma-web\backend && .venv\Scripts\python -m pytest -q` (con TEST_DB_URL).
     Actualizar la fila NUBE2 en `w:\POS\docs\README-pos.md` a ✅. Commit:
     `docs: cierra NUBE2 (catalogo + inventario multi-ubicacion) en README`.
  **No hagas merge ni push.** Reporta al usuario qué se implementó y cómo se verificó cada ola
  (A y B), y pregunta si arranca el roadmap post-NUBE2 o si cierra aquí.

REGLAS: TDD por task donde aplique (backend nube sí tiene pytest; frontend no tiene runner →
verificación manual en navegador, sé explícito sobre eso). Un commit pequeño por task (español).
Hooks bloquean heredocs → `git commit -m "una línea"` o `-F archivo`. Suite COMPLETA + self-review
+ reporte UNA sola vez al cierre del lote (no por task). Ponytail: reusa el patrón de
`Catalogo.tsx`/`EditorOverlay.tsx` (A.12) para el estilo de la UI web nueva; reusa
`/inventario/*` y `/sync/inventario` ya implementados (B.4-B.6), no inventes endpoints nuevos.
NO merge/push sin preguntar.

Carga superpowers:using-superpowers al arrancar; planes-pos (IDs NUBE2B.10/NUBE2B.11);
db-design-pos NO aplica (sin migraciones nuevas en este lote); pos-dominio NO aplica (es UI web,
no lógica del POS); frontend-design si la UI de inventario necesita decisiones visuales más allá
de reusar el patrón del dashboard/catálogo. NO cargues subagent-driven-development (reemplazado
por el modo batched).
