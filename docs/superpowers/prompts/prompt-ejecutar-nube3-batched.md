# Prompt handoff — ejecutar NUBE3 (aislamiento multi-tenant) en modo batched

Vas a **EJECUTAR** el plan NUBE3 (cerrar la escritura cross-tenant en `/sync/push`) en
**modo batched de bajo overhead** (misma decisión que NUBE2: subagente-por-task con review
por task gasta demasiados tokens para un plan pequeño). Repo backend: `w:\pos-plataforma-web`
(hermano de `w:\POS`). El POS **no se toca** en esta fase.

## Fuente de verdad

- Plan: `w:\POS\docs\superpowers\plans\2026-07-07-plataforma-web-aislamiento-multitenant.md`
  (5 tasks `NUBE3.1`–`NUBE3.5`, con TODO el código y los tests ya escritos paso a paso).
- Spec: `w:\POS\docs\superpowers\specs\2026-07-07-plataforma-web-aislamiento-multitenant-design.md`
- Ledger de estado: `w:\POS\.superpowers\sdd\progress.md`. Actualízalo con **una línea por lote**.

## Contexto (para no repreguntar)

- El spec ya fue revisado y aprobado con el usuario. Dos decisiones cerradas: **maestro
  `catalogo_producto` compartido** (con costura de un solo retorno para restringir a web-admin
  después) y **respuesta aditiva `rechazados: [{uuid, motivo}]`**. No las reabras.
- El hueco a cerrar: `/sync/push` confiaba en `payload.local_id`/`origen_id`/`destino_id` en vez
  del local autenticado. Las **lecturas** (`/sync/catalogo`, `/sync/inventario`) ya están cerradas.
- Hallazgo clave del plan: **todo movimiento legítimo del POS lleva `grupo_uuid`** (traslado,
  conversión, flip de confirmación); los directos (entrada/salida/ajuste sueltos, sin grupo) son
  de web-admin y se rechazan. La entrada **pendiente** de un traslado lleva `origen_id=None` y se
  acepta como "oferta" (sin efecto en stock hasta que el destino confirme). Está documentado en el
  plan (Task NUBE3.2, nota de diseño) — respétalo, no lo "arregles".
- **Ramas:** `w:\POS` = `feature/plataforma-web-fase-0-1`; `w:\pos-plataforma-web` = `master`.
  **NO merge ni push sin preguntar.** Aplicar la migración 007 a la BD real es paso de deploy y
  **requiere confirmación explícita del usuario** (checkpoint final).
- **TEST_DB_URL:** BD **`pos_test`** en el mismo Postgres (misma `SUPABASE_DB_URL` de
  `backend/.env` cambiando `/postgres` → `/pos_test`). La fixture hace `DROP SCHEMA public
  CASCADE`: seguro **solo** contra `/pos_test`, **NUNCA** contra `/postgres` (BD demo real).

## Baseline antes de tocar código

```
cd w:\pos-plataforma-web\backend && .venv\Scripts\python -m pytest -q
```
Esperado hoy: 18 passed, 4 skipped sin TEST_DB_URL (22 con TEST_DB_URL al pooler).

## Modo de ejecución batched (OBLIGATORIO — reemplaza subagent-driven-development)

- Trabaja **INLINE** (tú mismo, sin subagentes).
- TDD por task (test → falla → implementa → pasa) con tests **focalizados** (`-k`); la **suite
  completa + self-review + reporte breve al usuario** se hace UNA vez **al final de cada lote**.
- Un commit pequeño por task, en español (`feat(nube3)`/`test(nube3)`/`docs(nube3)`). Los hooks
  bloquean heredocs en bash → usa `git commit -m "una línea"`.
- Actualiza `progress.md` con una línea por lote (tasks, commits, resultado de suite).

## Lotes

1. **LOTE 1 — NUBE3.1 → NUBE3.2 → NUBE3.3** (backend, mismo archivo `app/sync.py` + tests
   unitarios): migración 007 `rechazo_motivo` → regla pura `evento_permitido`/`_permitido_movimiento`
   → cablear `push()` + respuesta `rechazados` + arreglar `_ConnFake`/`_Cursor`/`_lote_mov`.
   **Al cierre:** suite backend **sin** TEST_DB_URL verde (los gated se saltan) + reporte.
2. **LOTE 2 — NUBE3.4 + NUBE3.5 (Steps 1–2)**: 6 tests de integración del spec §6 (amplía las
   fixtures `conn`/`tokens` con `local-02` + bodega compartida id 9) → actualizar fila NUBE3 y
   conteo de suites en `README-pos.md` (repo `w:\POS`). **Al cierre:** suite backend **con**
   `TEST_DB_URL='...pos_test'` verde (unit + 6 integración + los `conn` preexistentes) + reporte.
3. **CHECKPOINT — NUBE3.5 (Steps 3–4)**: desplegar migración 007 a la **BD real** de Supabase y
   verificación en vivo con el POS real. **PARA y pregunta al usuario** antes de tocar la BD real;
   no hagas merge/push.

## Comandos

- Backend unit: `cd w:\pos-plataforma-web\backend && .venv\Scripts\python -m pytest -q`
- Backend integración: prefijar `TEST_DB_URL='<misma SUPABASE_DB_URL con /pos_test>'`
- (POS no se toca; no hace falta correr su suite salvo que, sin querer, cambies algo en `w:\POS`.)

## Reglas vigentes (del plan, no cambian)

- Aislamiento hexagonal: SQL solo en adaptadores; `evento_permitido` vive en `app/sync.py`, no en
  `core/`. `Decimal` siempre (JSON como `str`). LWW por `actualizado_en` (no se toca la
  materialización existente). Ponytail: mínimo código, reusa el flujo de `push()` y los patrones de
  test de `test_sync_push.py`.
- Enforcement "rechaza-solo-el-evento": ACK siempre, no abortes el lote, marca `rechazo_motivo`.
- No reabras las lecturas ya cerradas ni el alcance de NUBE2. No inventes infra de test nueva.

## Skills a cargar

`superpowers:using-superpowers` al arrancar; `planes-pos` (IDs `NUBE3.*`);
`superpowers:test-driven-development`; `db-design-pos` al tocar la migración 007. **NO** cargues
`subagent-driven-development` — reemplazado por este modo batched.
