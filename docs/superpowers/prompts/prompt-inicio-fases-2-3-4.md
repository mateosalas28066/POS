# Prompt handoff — implementar Fases 2, 3 y 4 (Compras, Cuentas, Gastos)

Copia esto en una sesión nueva de Claude Code en `w:\POS`:

---

Trabaja en el repo **pos-siesa-remake** en `w:\POS` (POS autónomo Python + PySide6 + SQLite,
arquitectura hexagonal: `src/core/` sin Qt ni SQLite, SQL solo en adaptadores de repositorio,
UI en `src/caja/`).

## Tu tarea

Implementar las **Fases 2, 3 y 4** del roadmap del cliente siguiendo el spec+plan ya aprobado:
**[docs/superpowers/specs/2026-07-01-fases-2-3-4-compras-cuentas-gastos-design.md](../specs/2026-07-01-fases-2-3-4-compras-cuentas-gastos-design.md)**.
Léelo completo antes de tocar código: es la fuente de verdad (diseño + plan de 14 tasks con
prefijos únicos + 4 decisiones ya confirmadas por el cliente). No lo reinterpretes.

## Estado de partida

- Rama actual: **`feature/fase-1-core-caja`** (Fase 1 ya implementada, suite **367 passed**).
  Si el spec aún no está commiteado, commitéalo primero (`docs: spec+plan fases 2-4`).
- Crea una rama nueva para este trabajo: **`feature/fases-2-3-4-compras-cuentas`**.
- Roadmap general: [docs/analisis-requerimientos-cliente.md](../../analisis-requerimientos-cliente.md).

## Decisiones ya tomadas (NO re-preguntar)

1. **CxC/CxP: saldo global** por cliente/proveedor (Σ deuda − Σ abonos), no por factura.
2. **Compra "en canal": módulo de despiece con costeo**, prorrateo del costo del canal **por
   valor de venta** de cada corte (fallback a peso si falta precio).
3. **Todo el efectivo pasa por la caja**: abonos, pagos a proveedor y gastos en efectivo se
   registran vía `ServicioCaja.registrar_movimiento` (Fase 1) y exigen sesión de caja abierta.
4. **Categorías de gasto: lista fija administrable** (tabla `categorias_gasto` con seed).

## Cómo trabajar

- **Orden:** Fase 2 → Fase 3 → Fase 4, y dentro de cada una las tasks en el orden del plan
  (dominio → persistencia → UI). Los IDs de task (PROV.1, COMPRA.1, DESPIECE.1, CXC.1, CXP.1,
  CUENTAS.UI, GASTO.1, MENSUAL.1, etc.) son los del spec; úsalos tal cual en TodoWrite.
- **Tests:** solo el flujo crítico por módulo (los marcados `+test` en el plan); el resto se
  valida manual (`python -m caja`, admin `admin`/`admin1234`). Convención: `tests/` espejo de
  `src/`, `test_*.py`. Corre `python -m pytest -q` tras cada fase; no rompas los 367 existentes.
- **Reutiliza:** `ServicioCaja.registrar_movimiento`/`MovimientoCaja` (migración 007) para todo
  efectivo; el patrón de `ServicioClientes`/`PantallaClientes` para proveedores; el patrón de
  `DialogoMovimientoCaja` para diálogos de abono/pago. Sigue Ponytail (mínimo código, YAGNI).
- **Migraciones:** nuevas y versionadas en `scripts/migraciones/` (008 proveedores+compras+
  despiece, 009 cuentas, 010 gastos). El producto-corte necesita `precio` cargado antes de
  despiezar (para el prorrateo por valor).
- **Git:** commits pequeños y temáticos en español (`feat(proveedores): …`, `feat(compras): …`,
  `feat(despiece): …`, `feat(cuentas): …`, `feat(gastos): …`). **No merge ni push sin preguntar.**

## Al cerrar

- `python -m pytest -q` en verde.
- Actualizar la tabla "Estado actual" de [docs/README-pos.md](../../README-pos.md) (filas
  Fases 2-4 + conteo de tests) y marcar las fases ✅ en el análisis.
- Reportar resumen de lo implementado y cómo se verificó; preguntar antes de integrar.

## Skills a cargar

`superpowers:executing-plans` al arrancar; `pos-dominio` (toca lógica de negocio),
`db-design-pos` (nuevas tablas/migraciones), `testing-pos` (pruebas), `planes-pos`
(convención de IDs de task).
