---
name: planes-pos
description: Use when writing, numbering, or executing an implementation plan or spec for pos-siesa-remake (docs/superpowers/plans, docs/superpowers/specs). Defines the mandatory task-ID convention that prevents tracking collisions during execution.
---

# Planes de implementación del POS (pos-siesa-remake)

Cargar al **escribir o ejecutar** una spec o un plan (`docs/superpowers/specs/`,
`docs/superpowers/plans/`). Define cómo identificar las tasks para que el ejecutor
(subagentes / tracking) no las confunda.

## Problema que esto evita

El plan de Usuarios+Cliente numeró sus tasks como `Task 1..16` (sin prefijo). `"Task N"`
es una etiqueta genérica que **todos los planes repiten**; con el plan de reportes usando
`E7.x` en paralelo, el ejecutor mezcló referencias durante el tracking. La causa no fue el
título, sino el **ID numérico sin prefijo único**.

## Convención OBLIGATORIA de identificación de tasks

1. **Prefija cada task con un código de epic único al plan**, nunca números pelados.
   Slug corto en MAYÚSCULAS derivado del epic: `Task CIERRE.1`, `Task CIERRE.2`, …
   (NO `Task 1`, `Task 2`).
2. **El prefijo debe ser distinto de los ya usados** en otros planes: `E1..E8`, `E3.b`,
   `E7.x`, `USUARIOS`/`CLIENTE`. Elige uno nuevo e inequívoco para tu epic.
3. **El título de cada task debe ser único y específico**, dentro y fuera del plan: incluye
   el módulo/archivo destino. Prohibido un título que sea solo un sustantivo ya existente
   (`Reportes`, `Cierre`, `Usuarios`) — colisiona con artefactos y con otras tasks.
   Bien: `Task CIERRE.3: DialogoConteoDenominaciones (caja/dialogos)`.
4. **Cada task nombra sus rutas de archivo exactas** (Create / Modify / Test), para que el
   ejecutor identifique la task por su artefacto y no por el número.
5. Si generas ítems de tracking (TodoWrite), usa el **ID con prefijo completo**
   (`CIERRE.2 — …`), nunca el número suelto.

## Convenciones generales de plan/spec

- Nombres de archivo fechados: `specs/AAAA-MM-DD-<slug>-design.md`, `plans/AAAA-MM-DD-<slug>.md`.
- Numeración de epics: **README-pos.md** (tabla "Estado actual") es la fuente de verdad;
  `plan-inicial-pos.md` es histórico y su numeración diverge — no la uses.
- Orden de tasks: dominio → persistencia → UI, en pasos TDD (test primero).
- Al cerrar el epic, actualizar la fila correspondiente en README-pos.md.
