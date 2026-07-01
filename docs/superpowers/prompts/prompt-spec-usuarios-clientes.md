# Prompt para otra sesión — Spec + plan de implementación: Usuarios y Clientes-en-venta

> Copia todo lo que está debajo de la línea y pégalo como primer mensaje en una sesión
> nueva de Claude Code abierta en `w:\POS`.

---

Trabaja en el repo `w:\POS` (proyecto **pos-siesa-remake**: POS offline-first en Python 3.11 +
PySide6 + SQLite, arquitectura hexagonal). Lee primero `CLAUDE.md`, `docs/README-pos.md` y la
spec maestra en `docs/superpowers/specs/2026-06-25-pos-siesa-remake-design.md`.

## Tu tarea

**NO implementes código todavía.** Produce dos entregables en `docs/superpowers/`:

1. Una **spec** (en `docs/superpowers/specs/`) para el epic **Usuarios + Cliente/descuento en la venta**.
2. Un **plan de implementación TDD** (en `docs/superpowers/plans/`) derivado de esa spec.

Empieza **obligatoriamente** invocando el skill `superpowers:brainstorming` para acordar el
alcance conmigo antes de escribir la spec, y luego `superpowers:writing-plans` para el plan.
Carga también los skills del proyecto que apliquen: `pos-dominio`, `db-design-pos`, `testing-pos`.
Respeta las **Reglas Ponytail** (mínimo código necesario, YAGNI, stdlib primero).

## Contexto verificado del código (no lo re-derives, ya está comprobado)

**Usuarios — NO existe nada hoy.** No hay entidad `Usuario`, ni tabla, ni autenticación, ni
roles. El campo `usuario_id: int | None` ya viaja en `Venta`, `CajaSesion` y `Devolucion`
([src/core/entidades.py](../../src/core/entidades.py)) pero **no está respaldado por ninguna
tabla ni se cablea desde la UI** — siempre va en `None`.

**Cliente — el maestro existe, falta usarlo en la venta.**
- Entidad `Cliente` con campos reservados DIAN (`tipo_documento`, `regimen`,
  `tipo_responsabilidad`) y `bloqueado_edicion`. Hay `ServicioClientes` (crear/actualizar/
  buscar/listar) y `consumidor_final()` (identificación `222222222222`, sembrado por migración
  `003_consumidor_final.sql`).
- `Venta.cliente_id` existe y `ServicioVenta.confirmar(..., cliente_id=...)` lo acepta, **pero
  `src/caja/pantalla_venta.py` NO selecciona cliente** (grep de `cliente_id` en la pantalla de
  venta: 0 coincidencias). Hoy toda venta queda sin cliente.
- **No existe** ningún concepto de descuento (ni por cliente, ni por línea, ni global) en
  dominio ni en UI.

**Infra relevante:**
- Migraciones SQL numeradas en `scripts/migraciones/` (hoy `001`..`004`); se aplican con
  `aplicar_migraciones()` en [src/inventario/db.py](../../src/inventario/db.py). La nueva tabla
  de usuarios y cualquier cambio de esquema van como `005_*.sql`, `006_*.sql`, etc.
- Composition root: `src/caja/contexto.py` (`ContextoApp`). Shell UI: `src/caja/ventana_principal.py`.
- Puertos de datos en `src/core/puertos.py`; adaptadores SQLite en `src/ventas/` e `src/inventario/`.
  **Regla de oro:** `core/` no conoce Qt ni SQLite; nada de SQL fuera de los adaptadores de repositorio.
- Tests: pytest, estructura espejo en `tests/`. Suite actual: **196 passed** (`python -m pytest -q`).

## Preguntas de alcance que debes resolver conmigo en el brainstorming

Usuarios:
- ¿Login real con contraseña o solo selección de cajero + PIN? (el negocio es una sola caja hoy).
- Roles: ¿solo `admin` y `cajero`, y qué acciones restringe cada uno? (p. ej. anular venta, editar
  precios, ver reportes, hacer cierre).
- Almacenamiento de credenciales: si hay contraseña/PIN, ¿hash con `hashlib`/`hmac` de stdlib
  (Ponytail: sin dependencias nuevas)? ¿sal por usuario?
- ¿Sesión de app (quién está logueado) vive en `ContextoApp`? ¿Cómo se cablea `usuario_id` en
  venta, cierre y devolución una vez hay usuario activo?

Clientes/descuento:
- ¿Selección de cliente en la pantalla de venta con default a consumidor final?
- Descuento por cliente: ¿porcentaje, monto fijo, o ambos? ¿Dónde se guarda (campo nuevo en
  `Cliente`)? ¿Se aplica al total o por línea? ¿Cómo interactúa con el IVA incluido (recalcular
  `impuesto`/`subtotal`) y con el redondeo `ROUND_HALF_UP` a peso entero que ya usa el dominio?
- ¿El descuento se persiste en la `Venta`/`LineaVenta` para el recibo y los reportes?

## Formato de los entregables

- **Spec**: problema, alcance (in/out), modelo de datos nuevo (tablas + entidades + puertos),
  reglas de dominio (con casos límite: descuento sobre IVA incluido, redondeo, cliente
  bloqueado, permisos por rol), impacto en UI, y qué queda **fuera** de alcance (YAGNI).
- **Plan**: tareas pequeñas en orden TDD (test primero), de dominio → persistencia → UI, cada una
  con los tests que la cubren, siguiendo el estilo de los planes existentes en
  `docs/superpowers/plans/`. Marca dependencias entre tareas.

Antes de escribir cada archivo, muéstrame un borrador del alcance y espera mi confirmación.
Cuando termines, deja los dos archivos creados y dame las rutas.
