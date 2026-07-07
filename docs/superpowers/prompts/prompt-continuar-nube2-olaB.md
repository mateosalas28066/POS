# Prompt handoff — Ola B de NUBE2 (inventario multi-ubicación) en modo batched

Vas a **implementar la Ola B** del plan NUBE2 (inventario multi-ubicación con sync delta
append-only), en el **modo batched de bajo overhead** ya usado en la Ola A (inline, sin
subagentes; TDD por task; suite + reporte una vez por lote; un commit por task).

## Fuente de verdad (léela antes de codificar)

- Plan: `w:\POS\docs\superpowers\plans\2026-07-07-plataforma-web-fase-2-catalogo-inventario.md`
  → sección **OLA B** (tasks B.1–B.11) + la sección **"Notas de ejecución en vivo — Ola A"**
  (aprendizajes que aplican a la Ola B).
- Spec: `w:\POS\docs\superpowers\specs\2026-07-07-plataforma-web-fase-2-catalogo-inventario-design.md`
  (§ inventario/ubicaciones/movimientos).
- Ledger de progreso: `w:\POS\.superpowers\sdd\progress.md` (sección NUBE2). Lo completo NO se rehace.
- Modo batched (reglas): `w:\POS\docs\superpowers\prompts\prompt-continuar-nube2-batched.md`.

## Estado al arrancar (Ola A = COMPLETA)

- **Ola A implementada y verificada en vivo** (catálogo bidireccional + sync híbrido "aplica+avisa").
  Commits en ambos repos; sin merge/push.
- **Suites base (verde antes de empezar):**
  - POS: `cd w:\POS && python -m pytest -q` → **448 passed**.
  - Backend: `cd w:\pos-plataforma-web\backend && .venv\Scripts\python -m pytest -q` → 18+skips;
    con `TEST_DB_URL` (BD `pos_test`) → **40 passed**.
- **Ramas:** `w:\POS` = `feature/plataforma-web-fase-0-1`; `w:\pos-plataforma-web` = `master`.
  **NO merge ni push sin preguntar.**
- **TEST_DB_URL** = la `SUPABASE_DB_URL` de `backend/.env` cambiando `/postgres` → `/pos_test`.
  La fixture de integración hace `DROP SCHEMA public CASCADE`: **solo** seguro contra `/pos_test`,
  **NUNCA** contra `/postgres` (BD demo real).
- **Procesos en vivo (quizá siguen arriba de la sesión anterior; NO asumas):** backend uvicorn en
  `:8000` (nohup, log `/tmp/uvicorn_pos.log`), frontend Vite en `:5173`. Reinícialos si hace falta
  (backend: `set -a; source backend/.env; set +a; .venv/Scripts/python -m uvicorn app.main:app --port 8000`).

## Lotes (por afinidad; ajusta el corte si al investigar ves mejor)

1. **LOTE B1–B3:** B.1 migración nube **006** (rename `almacenes`→`ubicaciones` + `tipo`/`activo` +
   relax `local_id`; extiende `movimientos_inventario`) → B.2 migrar `dashboard.py` y fixtures a
   `FROM ubicaciones WHERE tipo='local'` (Fase 1 sigue verde) → B.3 core inventario multi-ubicación
   en `w:\POS\src\core\` (servicio + puerto `RepositorioMovimientosUbicacion`, Python puro). Suite
   backend con TEST_DB_URL + suite POS al cierre.
2. **LOTE B4–B6** (backend inventario): B.4 `/inventario/*` (gestión web, `admin_web`) → B.5
   `/sync/inventario` (pull delta por cursor) → B.6 `/sync/push` materializa `movimiento_inventario`
   (append + único flip `pendiente→confirmado`). **Verifica que `inventario_movimientos` tenga UNIQUE
   sobre `uuid`** para el `ON CONFLICT`; si no, agrégalo en la migración 006.
3. **LOTE B7–B9** (POS inventario): B.7 migración POS de inventario multi-ubicación +
   `RepositorioMovimientosUbicacionSQLite` → B.8 pull delta en `ClienteSync` → B.9 el admin registra
   movimientos/traslados → outbox (+ permisos `ACCION_GESTIONAR_INVENTARIO`/`ACCION_CONFIRMAR_TRASLADO`).
4. **LOTE B10–B11:** B.10 UI web inventario (pestaña nueva en `App.tsx`; `npm run build` + `npx oxlint`,
   sin test runner) → B.11 **e2e Ola B en vivo** + cierre: fila `NUBE2·OlaB` en `README-pos.md` → ✅,
   ambas suites verdes, reporte final. **PARA y pide verificación al usuario en B.11.** Sin merge/push.

## Aprendizajes de la Ola A que DEBES aplicar

1. **Desplegar migraciones a la BD REAL, no solo `pos_test`.** Tras crear la migración nube 006,
   aplícala a `/postgres` como paso de deploy (los tests NO lo hacen):
   `python -c "import psycopg,os; from app.migraciones_runner import aplicar_migraciones; aplicar_migraciones(psycopg.connect(os.environ['SUPABASE_DB_URL']))"`.
   ⚠️ **La 006 renombra `almacenes`→`ubicaciones` sobre datos de Fase 1** — es más delicada que la 005
   (aditiva). Revisa que `dashboard.py` y las columnas `almacen_id` existentes sigan resolviendo
   (el plan dice: conservar `almacen_id` apuntando a `ubicaciones.id`, sin vista de compat). Prueba el
   dashboard en vivo tras aplicarla.
2. **Alineación de ids POS↔nube** para ubicaciones/movimientos (mismo invariante que catálogo).
3. **Numeración de migraciones POS:** existen 001–012 y **014** (`novedades_catalogo`); **013 quedó libre**
   (se saltó). El plan reserva 013 para inventario POS: puedes usar **013** (queda fuera de orden respecto
   a 014 ya aplicada, pero es inofensivo: el runner aplica las no-aplicadas y 013/014 son independientes) o
   **015** para mantener orden estrictamente creciente. **Confírmalo con `ls scripts/migraciones/`** antes.
4. **Patrón de aviso híbrido**: si un traslado/movimiento llega desde la nube, considera el mismo aviso
   no bloqueante de la Ola A (`novedades_catalogo` + `VentanaPrincipal`) — **solo si el usuario lo pide**;
   no lo metas por default, cíñete al plan.
5. `ADMIN_EMAILS` en `backend/.env` incluye la cuenta real de la web (`admin@test.com`) además del email
   del dueño.

## Reglas vigentes (no cambian)

- Aislamiento hexagonal: `core/` sin Qt/SQLite/psycopg; SQL solo en adaptadores. Inventario multi-ubicación
  = reglas en `core`; adaptadores en `inventario/`, `backend/app/`.
- `Decimal` siempre (JSON como `str`). Inventario **append-only** + único flip `pendiente→confirmado`;
  idempotencia por `uuid`. Cursor de sync por ubicación.
- Ponytail: reusa `outbox`/`ClienteSync`/`HiloSincronizacion`/`sync_cursor` y el patrón `stock_de`
  (suma de movimientos) que ya existe.
- Un commit pequeño por task (español; hooks bloquean heredocs → `git commit -m "una línea"` o `-F`).
  Ledger: una línea por lote. **No merge/push sin preguntar.**

## Skills a cargar

`superpowers:using-superpowers` al arrancar; `planes-pos` (IDs `NUBE2B.*`);
`superpowers:test-driven-development`; `db-design-pos` en las migraciones (006 nube / 015 POS);
`pos-dominio` al tocar reglas de inventario del POS. **NO** cargues `subagent-driven-development`
(reemplazado por el modo batched). `frontend-design`/`dataviz` solo si la UI web de inventario
va más allá de reusar el patrón del dashboard/catálogo.
