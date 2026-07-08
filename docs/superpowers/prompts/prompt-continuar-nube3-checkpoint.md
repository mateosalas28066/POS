# Prompt handoff — CHECKPOINT final de NUBE3 (deploy migración 007 + verificación en vivo)

Continúa el plan NUBE3 (aislamiento multi-tenant en `/sync/push`) en modo batched inline
(ver `docs/superpowers/prompts/prompt-ejecutar-nube3-batched.md`). Repo backend:
`w:\pos-plataforma-web` (hermano de `w:\POS`).

## Fuente de verdad

- Plan: `w:\POS\docs\superpowers\plans\2026-07-07-plataforma-web-aislamiento-multitenant.md`
  (Task NUBE3.5, Steps 3-4, líneas ~593-611).
- Spec: `w:\POS\docs\superpowers\specs\2026-07-07-plataforma-web-aislamiento-multitenant-design.md`
- Ledger de estado: `w:\POS\.superpowers\sdd\progress.md` sección "NUBE3" (gitignored, tiene el
  detalle completo de LOTE 1 y LOTE 2, incluido el incidente de derivación de `TEST_DB_URL`).

## Estado al arrancar (LOTE 1 y LOTE 2 completos)

- **LOTE 1** (NUBE3.1→NUBE3.2→NUBE3.3, repo `pos-plataforma-web` master): commits `307ba6a`
  (migración 007 `eventos_sync.rechazo_motivo`) + `d81ec64` (regla pura `evento_permitido`/
  `_permitido_movimiento` en `app/sync.py`) + `3cb59a2` (cablea el enforcement en `push()` +
  respuesta aditiva `rechazados: [{uuid, motivo}]`).
- **LOTE 2** (NUBE3.4 + NUBE3.5 pasos 1-2): commit `94eded7` en `pos-plataforma-web` (6 tests de
  integración del spec §6 contra Postgres real: traslado cross-local legítimo, flip
  solo-por-destino, overlay ajeno no rompe el lote, salida sobre ubicación ajena rechaza, lote
  sano intacto, maestro compartido desde otro local — todos verdes sin fixes) + commit `237b2b0`
  en `w:\POS` (fila NUBE3 en `docs/README-pos.md` + conteo de suite backend actualizado a 77).
- Suites verdes: backend con `TEST_DB_URL='...pos_test'` → **77 passed**; sin ella → **43 passed,
  34 skipped** (consistente, 43+34=77). POS no se tocó en todo el plan.
- **Ramas:** `w:\POS` = `feature/plataforma-web-fase-0-1`; `w:\pos-plataforma-web` = `master`.
  Ambos repos con working tree limpio. **NO merge ni push a ningún repo sin preguntar** (no se
  ha hecho ninguno en todo el plan).
- **TEST_DB_URL:** BD `pos_test` en el mismo Postgres (misma `SUPABASE_DB_URL` de `backend/.env`
  cambiando solo el **sufijo final** `/postgres` → `/pos_test`). ⚠️ Aprendizaje del LOTE 2: un
  `.replace('/postgres', '/pos_test')` ingenuo sobre la URL completa corrompe también el usuario
  (`postgres.<ref>` en el scheme) y dispara el circuit-breaker de auth de Supabase
  (`ECIRCUITBREAKER`). Derivar reemplazando solo el sufijo final de la ruta, nunca con un
  `str.replace` global. No dejar el archivo con la connection string sin borrar.

## Lo que falta: CHECKPOINT — NUBE3.5 Steps 3-4

> ⚠️ Esto toca la **BD real** de Supabase (producción del demo). **PARA y pregunta al usuario
> antes de ejecutar cualquier paso de esta sección.** No lo hagas de forma autónoma aunque el
> resto del plan ya esté aprobado — el plan exige confirmación explícita para este paso
> específico.

- **Step 3: Desplegar la migración 007 a la BD real** (`SUPABASE_DB_URL` → `/postgres`, NO
  `/pos_test`):
  ```bash
  cd "w:/pos-plataforma-web/backend"
  .venv/Scripts/python -c "import psycopg,os; from app.migraciones_runner import aplicar_migraciones; aplicar_migraciones(psycopg.connect(os.environ['SUPABASE_DB_URL']))"
  ```
  Alternativa vía MCP Supabase (`apply_migration` con el SQL de
  `migraciones/007_rechazo_motivo.sql`). Verificar después:
  ```sql
  SELECT column_name FROM information_schema.columns
  WHERE table_name='eventos_sync' AND column_name='rechazo_motivo';
  ```
  Esperado: una fila (`rechazo_motivo`).

- **Step 4: Verificación en vivo** (opcional pero recomendada). Con el backend corriendo contra
  la BD real y el POS real (`w:\POS\iniciar_pos.ps1`):
  1. Registrar una venta legítima → confirmar `rechazados == []` en la respuesta de `/sync/push`
     y que materializa normalmente.
  2. Si es fácil de forzar, empujar un evento con `local_id`/ubicación ajena → confirmar que
     `eventos_sync.rechazo_motivo` queda seteado para ese uuid y que **no** materializa (pero sí
     se ACKea, no rompe el lote).
  3. Reportar al usuario exactamente qué se verificó.

## Reglas vigentes (no cambian)

- Aislamiento hexagonal, Ponytail, TDD ya cumplidos — este checkpoint es solo deploy +
  verificación, no agrega código nuevo.
- Enforcement "rechaza-solo-el-evento" ya implementado y probado; no lo reabras.
- Al cerrar (si el usuario aprueba el deploy y, opcionalmente, la verificación en vivo),
  actualizar una línea de cierre en `w:\POS\.superpowers\sdd\progress.md` sección NUBE3 con el
  resultado. El plan **NUBE3 queda completo** tras este checkpoint.

## Skills a cargar

`superpowers:using-superpowers` al arrancar; `planes-pos` (IDs `NUBE3.*`); `supabase` (para el
deploy de migración vía MCP si se usa esa vía). NO hace falta `test-driven-development` (no hay
código nuevo) ni `db-design-pos` (la migración ya está escrita y probada, solo se despliega).
