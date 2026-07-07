# Prompt handoff — continuar NUBE2 (Fase 2 plataforma web) en modo batched

Vas a **CONTINUAR** la ejecución del plan NUBE2 (catálogo bidireccional + inventario
multi-ubicación) desde la task **NUBE2A.4**, en **modo batched de bajo overhead**
(decisión del usuario 2026-07-07: la ejecución subagente-por-task con review por task
gastaba demasiados tokens para lo avanzado).

## Fuente de verdad

- Plan: `w:\POS\docs\superpowers\plans\2026-07-07-plataforma-web-fase-2-catalogo-inventario.md`
- Spec: `w:\POS\docs\superpowers\specs\2026-07-07-plataforma-web-fase-2-catalogo-inventario-design.md`
- Ledger con el estado real: `w:\POS\.superpowers\sdd\progress.md` (sección NUBE2 al final).
  Las tasks marcadas complete ahí **NO se rehacen**.

## Estado al momento del handoff

- **Hechas y revisadas:** A.1 (migración 005 catálogo maestro, commit `3a40d62` en
  pos-plataforma-web), A.2 (`core/sync_lww.py`, `77fcfeb` en POS), A.3
  (`GET /sync/catalogo` + fix 403 si `local_id` ≠ token, `ff1ff71`+`a7007a9`).
- **Suites:** POS 424 passed; backend 28 passed (con TEST_DB_URL) / 18+skips sin ella.
- **Ramas:** `w:\POS` = `feature/plataforma-web-fase-0-1`; `w:\pos-plataforma-web` = `master`.
  **NO merge ni push sin preguntar.**
- **TEST_DB_URL:** el branching de Supabase NO está disponible; se creó la BD **`pos_test`**
  en el mismo Postgres. URL = la misma `SUPABASE_DB_URL` de `backend/.env` cambiando el
  nombre de base final `/postgres` → `/pos_test`. La fixture de integración hace
  `DROP SCHEMA public CASCADE`: **solo** es seguro contra `/pos_test`, **NUNCA** contra
  `/postgres` (la BD demo real).
- **ADMIN_EMAILS** (para A.4 en adelante): `spartan123xd@gmail.com` — va en `backend/.env`
  (no versionado) al probar en vivo; en tests se monkeypatchea `Settings(admin_emails=...)`.

## Modo de ejecución batched (OBLIGATORIO — reemplaza subagent-driven-development)

- Trabaja **INLINE** (tú mismo, sin subagentes). Excepción: puedes delegar un lote entero a
  UN subagente solo si es puramente mecánico y te ahorra contexto de verdad.
- Ejecuta por **LOTES** (abajo). Dentro del lote: TDD por task (test → falla → implementa →
  pasa) con tests **focalizados**; la **suite completa + self-review + reporte breve al
  usuario** se hace UNA vez **al final del lote**, no por task.
- Un commit pequeño por task (español, `feat(backend)/feat(pos)/feat(core)/fix/test`).
  Los hooks bloquean heredocs en bash → `git commit -m "una línea"` o `-F archivo`.
- Sin reviews de subagente por task. Opcional: una review al cierre de cada ola; la review
  final de rama al cerrar NUBE2 sí vale la pena.
- Actualiza el ledger (`progress.md`) con **una línea por lote** (tasks, commits, suite).

## Lotes (por afinidad de repo/archivos — ajusta si al investigar ves mejor corte)

1. **LOTE A4–A6** (backend nube, mismo andamiaje de tests): A.4 `admin_web` (ADMIN_EMAILS)
   → A.5 gestión `/catalogo/*` (usa `admin_web`) → A.6 `/sync/push` materializa catálogo LWW.
   Suite backend con TEST_DB_URL al cierre.
2. **LOTE A7–A9** (POS `sync_pdv`, cadena réplica): A.7 migración 012 réplica → A.8
   `RepositorioReplicaSQLite` → A.9 pull catálogo en `ClienteSync`. Suite POS al cierre.
3. **LOTE A10–A11** (POS caja/outbox, lo más delicado): A.10 venta lee precio de la réplica
   (acótalo al resolutor `precio_venta(producto_id)` réplica→fallback, NO reescribas la
   pantalla de venta) → A.11 admin POS edita/importa → outbox. Suite POS completa.
4. **LOTE A12–A13**: A.12 UI web catálogo (`npm run build && npx oxlint`, sin test runner)
   → A.13 **verificación e2e Ola A en navegador + POS real**. → **PARA en el checkpoint
   A.13**: el usuario verifica y decide si arranca la Ola B.
5. **LOTE B1–B3**: B.1 migración 006 ubicaciones → B.2 `dashboard.py`+fixtures a
   `ubicaciones` → B.3 core inventario multi-ubicación (repo POS; B.4 lo consume).
6. **LOTE B4–B6** (backend inventario): B.4 `/inventario/*` → B.5 `/sync/inventario` delta
   → B.6 push `movimiento_inventario` (verifica que `inventario_movimientos` tenga UNIQUE
   sobre `uuid` para el `ON CONFLICT`; si no, agrégalo en la migración 006).
7. **LOTE B7–B9** (POS inventario): B.7 migración 013 + `RepositorioMovimientosUbicacionSQLite`
   → B.8 pull delta en `ClienteSync` → B.9 admin registra movimientos → outbox (+ permisos
   `ACCION_GESTIONAR_INVENTARIO`/`ACCION_CONFIRMAR_TRASLADO`).
8. **LOTE B10–B11**: B.10 UI web inventario → B.11 e2e Ola B + cierre (fila NUBE2 en
   `README-pos.md` → ✅, ambas suites verdes, reporte final). Sin merge/push.

## Comandos

- POS: `cd w:\POS && python -m pytest -q` (hoy 424 passed)
- Backend: `cd w:\pos-plataforma-web\backend && .venv\Scripts\python -m pytest -q`
  (integración: prefijar `TEST_DB_URL='...pos_test'`)
- Frontend: `cd w:\pos-plataforma-web\frontend && npm run build && npx oxlint`

## Reglas vigentes (del plan, no cambian)

- Aislamiento hexagonal: `core/` sin Qt/SQLite/psycopg; SQL solo en adaptadores.
- `Decimal` siempre (en JSON como `str`). LWW por `actualizado_en` (guardia
  `WHERE existente < entrante`); inventario append-only + único flip `pendiente→confirmado`.
- Lee las secciones "Decisiones cerradas" y "Reconciliaciones con el spec" del plan antes
  de codificar. Ponytail: reusa outbox/ClienteSync/HiloSincronizacion y patrones existentes.
- No re-abras A.1–A.3. No inventes infraestructura de test de frontend.

## Skills a cargar

`superpowers:using-superpowers` al arrancar; `planes-pos` (IDs NUBE2A.*/NUBE2B.*);
`superpowers:test-driven-development`; `db-design-pos` al tocar migraciones; `pos-dominio`
si tocas reglas de negocio del POS. **NO** cargues `subagent-driven-development` — el
usuario lo reemplazó explícitamente por este modo batched.
