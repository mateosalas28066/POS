# Prompt handoff — Ejecutar MARCA (fundación visual del Sistema de Diseño)

Ejecuta el plan de la **fundación visual de marca "Carnes y Fruver RL"** en modo **batched
inline** (lotes de ~3 tasks afines, sin subagentes, suite+reporte una vez por lote).

## Fuente de verdad

- **Plan:** `w:\POS\docs\superpowers\plans\2026-07-08-sistema-diseno-marca.md`
- **Spec:** `w:\POS\docs\superpowers\specs\2026-07-08-sistema-diseno-marca-design.md`
- Repos: `w:\POS` (POS PySide6) y `w:\pos-plataforma-web` (web React, hermano).
- Logo/marca: `D:\Descargas\Logo_RL.png` (rojo `#E01E26`, carbón, blanco, glow neón).

## Skills a cargar al arrancar

- `superpowers:using-superpowers` (siempre).
- `superpowers:executing-plans` (ejecución del plan por checkpoints).
- `planes-pos` (IDs de task con prefijo — aquí `MARCA.*`, nunca número pelado).
- Lado web, para estética: `frontend-design` y el `taste-skill` ya instalado en
  `w:\pos-plataforma-web\frontend\.agents\skills\` (variantes `redesign-existing-projects`,
  `imagegen-frontend-mobile`). NO hace falta `brainstorming` (el diseño ya está aprobado).

## Qué construir (6 tasks, 2 lotes)

- **LOTE A — Web** (`pos-plataforma-web`, rama `master`):
  `MARCA.1` Tailwind v4 (`@theme`) + fuentes → `MARCA.2` primitivos
  (Boton/Tarjeta/Campo/NavInferior) → `MARCA.3` página `/estilo` + gate impeccable.
- **LOTE B — POS** (`w:\POS`, rama `feature/plataforma-web-fase-0-1`):
  `MARCA.4` qt-material + tema/fuentes de marca → `MARCA.5` overlay `marca.qss` + helper
  de glow → `MARCA.6` ventana "Estilo".

Cada task del plan trae rutas exactas, código completo y pasos TDD. Respeta el orden.

## Estado al arrancar

- Spec, plan y este prompt ya están **committeados** en `w:\POS`
  (rama `feature/plataforma-web-fase-0-1`). Working trees de ambos repos limpios.
  Empieza directamente por `MARCA.1` (sin push ni merge).
- Tooling ya hecho en el brainstorm: `impeccable detect src/` sobre la web → `[]` (limpio);
  `taste-skill` instalado (13 variantes) en `frontend/.agents/skills/` + `skills-lock.json`
  (untracked; `MARCA.1` los agrega a `.gitignore`). `wondelai/skills` descartado.

## Reglas vigentes (no cambian)

- **Alcance = solo lo VISUAL.** NO rediseñar pantallas, navegación, menús, IA ni el set de
  iconos por vista. Eso son los specs siguientes (Rediseño Web, Rediseño POS). No los abras.
- Personalidad **moderna premium**, dark-first. Rojo `#E01E26` solo para intención primaria;
  glow racionado. Fuentes **Space Grotesk / Geist Sans / Geist Mono**, auto-hospedadas
  (prohibido Inter/Roboto). Ponytail: mínimo código; web con mínimas deps.
- **`impeccable` es web-only** (no ve Python/QSS). El guardrail del POS son el overlay de
  marca + los tests pytest de `MARCA.4/5`.
- **Vendorizar fuentes necesita red una vez** (`MARCA.4` Step 2 hace `curl` de los TTF);
  después todo offline. Si una URL upstream cambió, buscar el TTF equivalente del repo oficial.
- **`qt-material` es dependencia nueva aceptada** (decisión del usuario), instalada en el
  venv del POS.
- **NO merge ni push a ningún repo sin preguntar.** Commits, sí, en el repo de cada task.

## Al cerrar

- Correr la suite una vez por lote (LOTE A: `npm run build` + `impeccable detect src/`;
  LOTE B: `pytest tests/caja -q`) y reportar.
- Actualizar la fila correspondiente en `docs/README-pos.md` (fundación de marca lista),
  en un commit de docs aparte.
- La fundación `MARCA` queda completa tras `MARCA.6`. Los rediseños de pantalla van en
  specs nuevos.
