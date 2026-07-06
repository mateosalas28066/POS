# Prompt para continuar en otra sesión — Ejecución PROMO/CONTEO con subagentes

> Copia todo lo que está debajo de la línea y pégalo como primer mensaje en una
> sesión nueva de Claude Code abierta en `w:\POS`.

---

Continúa la ejecución del plan de **Promociones por producto + Conteo de efectivo al
cierre** en el repo `pos-siesa-remake`, usando la skill `superpowers:subagent-driven-development`.

## Estado actual (no lo re-derives, ya está verificado)

- **Worktree activo:** `W:\POS\.worktrees\promociones-conteo-caja`, rama
  `worktree-promociones-conteo-caja`, creada desde el `HEAD` local de `master`
  (commit `e9768c3`) — **no** desde `origin/master`, que está desactualizado
  (le faltan todos los commits de RPTFAC y posteriores). Si usas `EnterWorktree`
  con un `name` nuevo, por defecto rama desde `origin/master` y te va a faltar
  historia; usa `EnterWorktree` con `path: "W:\\POS\\.worktrees\\promociones-conteo-caja"`
  para entrar al worktree que ya existe.
- **Spec:** `docs/superpowers/specs/2026-07-01-promociones-conteo-caja-design.md`
- **Plan:** `docs/superpowers/plans/2026-07-01-promociones-conteo-caja.md`
  (14 tasks: `PROMO.1..11`, `CONTEO.1..3`, más cierre del epic). Ambos archivos
  están **sin commitear** en `master` (son intencionalmente untracked ahí) pero
  ya fueron copiados dentro del worktree — están presentes en
  `W:\POS\.worktrees\promociones-conteo-caja\docs\superpowers\`. Si por algún
  motivo el worktree no existe ya, cópialos de nuevo desde `w:\POS\docs\superpowers\`
  antes de arrancar.
- **Ledger de progreso:** `.superpowers/sdd/progress.md` dentro del worktree.
  Contenido actual:
  ```
  PROMO.1: complete (commits e9768c3..b3e2adc, review clean — Minor nitpicks only, no fix needed)
  PROMO.2: complete (commits b3e2adc..bb00c93, review clean — Minor: unconsumed over-consumption edge case, not required)
  PROMO.3: complete (commits bb00c93..6ab3685, review clean — Minor: PromocionNoEncontrada untested, not required)
  PROMO.4: complete (commits 6ab3685..faf1a27, review clean — Minor: no CHECK/index, out of scope)
  ```
- **HEAD actual del worktree:** `faf1a27` (feat(promociones): migración 006 ...).
  Suite completa: `python -m pytest -q` → **290 passed**.
- **Brief ya extraído y listo:** `.superpowers/sdd/task-PROMO.5-brief.md` (el
  siguiente task, PROMO.5, aún NO fue dispatcheado a ningún implementador).
- **Helper de extracción de briefs:** el script oficial de la skill
  (`scripts/task-brief`) espera encabezados `## Task N`, pero este plan usa
  IDs con prefijo (`## PROMO.1:`, `## CONTEO.1:`, convención obligatoria de la
  skill `planes-pos`). Por eso se creó un helper equivalente, ya copiado
  dentro del worktree en `.superpowers/sdd/task-brief-pos.sh`. Úsalo así:
  ```bash
  bash .superpowers/sdd/task-brief-pos.sh docs/superpowers/plans/2026-07-01-promociones-conteo-caja.md "PROMO.5" .superpowers/sdd/task-PROMO.5-brief.md
  ```
  (cambia el ID y el nombre de salida para cada task; el patrón de headings es
  `## <PREFIJO>.<N>:` seguido de la siguiente `## `).

## Qué falta

En orden, siguiendo el plan (dominio → persistencia → UI, primero todas las
`PROMO.x` y luego las `CONTEO.x`):

- [ ] `PROMO.5` — Adaptador `RepositorioPromocionesSQLite` (`src/inventario/repositorio_sqlite.py`)
- [ ] `PROMO.6` — `ServicioVenta` aplica la promo + wiring en `ContextoApp`
- [ ] `PROMO.7` — Consumo de unidades al registrar la venta
- [ ] `PROMO.8` — Persistir `promocion_id` en el adaptador de ventas
- [ ] `PROMO.9` — Permiso `gestionar_promociones`
- [ ] `PROMO.10` — `DialogoPromociones` + botón en pantalla de inventario
- [ ] `PROMO.11` — Marca visual del precio promo en la pantalla de venta
- [ ] `CONTEO.1` — Denominaciones + `total_conteo` (`caja/conteo.py`)
- [ ] `CONTEO.2` — `DialogoConteoEfectivo`
- [ ] `CONTEO.3` — Botón "Contar efectivo" en la pantalla de cierre
- [ ] Cierre del epic: suite completa verde + actualizar `docs/README-pos.md`
- [ ] Revisión final de todo el branch (whole-branch code review, modelo más capaz)

## Cómo continuar

1. Carga la skill `superpowers:subagent-driven-development` (y
   `superpowers:using-git-worktrees` si necesitas re-entrar al worktree).
2. Entra al worktree existente (no crees uno nuevo):
   `EnterWorktree` con `path: "W:\\POS\\.worktrees\\promociones-conteo-caja"`.
3. Verifica baseline: `git log --oneline -5` (debe mostrar `faf1a27` como HEAD)
   y `python -m pytest -q` (debe dar 290 passed). Si no coincide, para y
   reporta antes de seguir — no reintentes tasks que el ledger ya marca como
   `complete`.
4. Extrae el brief de `PROMO.5` (ya está extraído, solo reutilízalo) y
   dispacha el implementador siguiendo el patrón usado en `PROMO.1..4`:
   implementador (modelo barato si la task trae código exacto en el plan,
   modelo estándar si hay integración de varios archivos) → package de
   review (`scripts/review-package BASE HEAD`) → revisor (spec + calidad) →
   si hay Critical/Important, fix y re-review → marcar completo en el ledger
   y en el todo list → siguiente task.
5. Sigue el mismo patrón para el resto de tasks en orden.
6. Al terminar todas las tasks, corre la revisión final de todo el branch
   (`superpowers:requesting-code-review`'s `code-reviewer.md`, con el modelo
   más capaz disponible) contra el diff completo `merge-base(master, HEAD)..HEAD`.
7. Actualiza `docs/README-pos.md` (tabla "Estado actual") marcando PROMO y
   CONTEO como implementados, con el conteo de tests actualizado.
8. No hagas merge ni push del branch sin preguntar primero — al terminar,
   usa `superpowers:finishing-a-development-branch` para presentar las
   opciones de integración.

**Reglas Ponytail** (mínimo código necesario, YAGNI, stdlib primero) y la
arquitectura hexagonal del proyecto (`src/core/` no conoce Qt ni SQLite, SQL
solo en adaptadores) siguen aplicando a cada task igual que en las anteriores.
