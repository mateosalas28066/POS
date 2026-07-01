# Prompt para otra sesión — Spec + plan: Reportes por factura y por cajero

> Copia todo lo que está debajo de la línea y pégalo como primer mensaje en una sesión
> nueva de Claude Code abierta en `w:\POS`.

---

Trabaja en el repo `w:\POS` (proyecto **pos-siesa-remake**: POS offline-first en Python 3.11 +
PySide6 + SQLite, arquitectura hexagonal). Lee primero `CLAUDE.md`, `docs/README-pos.md` y la
spec maestra en `docs/superpowers/specs/2026-06-25-pos-siesa-remake-design.md`.

## Tu tarea

**NO implementes código todavía.** Produce dos entregables en `docs/superpowers/`:

1. Una **spec** (en `docs/superpowers/specs/`) para el epic **Reportes por factura y por cajero**.
2. Un **plan de implementación TDD** (en `docs/superpowers/plans/`) derivado de esa spec.

Carga **obligatoriamente** estas skills antes de empezar:
- `superpowers:brainstorming` — para acordar el alcance conmigo ANTES de escribir la spec.
- `superpowers:writing-plans` — para el plan.
- `planes-pos` — **convención obligatoria de IDs de task** (lee el punto de más abajo; esto no es opcional).
- `pos-dominio` y `testing-pos` — dominio y pruebas del POS.

Respeta las **Reglas Ponytail** (mínimo código necesario, YAGNI, stdlib primero).

## Convención de IDs de task (de la skill `planes-pos`) — CRÍTICO

El plan anterior numeró `Task 1..16` sin prefijo y el ejecutor confundió tasks con las de otros
planes (el plan de reportes E7 usa `E7.x`). Para ESTE plan:
- **Prefija cada task con un código de epic único**, en MAYÚSCULAS, distinto de los ya usados
  (`E1..E8`, `E3.b`, `E7.x`). El prefijo `E7` **ya está tomado** por el plan de reportes original,
  así que **NO uses `E7` ni números pelados**. Propuesta: `RPTFAC.1`, `RPTFAC.2`, … (confírmalo
  conmigo en el brainstorming).
- Título único y específico por task, con módulo/archivo destino; nada de títulos que sean solo
  `Reportes`/`Cierre`.
- Cada task nombra sus rutas Create/Modify/Test exactas; en el tracking usa el ID con prefijo.

## Contexto verificado del código (no lo re-derives, ya está comprobado)

**Lo que YA existe** ([src/core/servicio_reportes.py](../../src/core/servicio_reportes.py) +
[src/caja/pantalla_reportes.py](../../src/caja/pantalla_reportes.py)):
- `ServicioReportes.ventas(desde, hasta) -> ReporteVentas`: agrega por **período** y por **medio
  de pago** (`por_medio`), con total, IVA, devoluciones y neto. **No** desglosa por factura ni por
  cajero.
- `ServicioReportes.inventario(...)` y `ServicioReportes.cierre(sesion_id)` (arqueo por sesión).
- `PantallaReportes`: dos pestañas (**Ventas**, **Inventario**), filtro por rango de fechas, KPIs
  y tabla por medio de pago. No hay lista de facturas ni corte por cajero.

**Lo que habilita este epic (ya persistido, sin usar en reportes):**
- `Venta` tiene `usuario_id`, `cliente_id`, `id`, `fecha`, `total`, `total_impuestos`,
  `descuento_pct`, `estado` — y `usuario_id` **ya se guarda** en cada venta (epic Usuarios+Cliente).
- El puerto `RepositorioVentas` ya expone `ventas_en(desde, hasta) -> list[Venta]` (excluye
  anuladas) y `pagos_en(desde, hasta)`. Es decir, "por factura" = listar esas ventas; "por cajero"
  = agrupar esas ventas por `usuario_id` — **mayormente agregación en Python en `core`**, poca o
  ninguna SQL nueva.
- Hay `RepositorioUsuarios`/`ServicioUsuarios` para resolver `usuario_id → nombre`.

**Reglas de arquitectura:** `core/` no conoce Qt ni SQLite; SQL solo en adaptadores de repositorio;
sin dependencias nuevas; dinero en `Decimal`. Suite actual: **259 passed** (`python -m pytest -q`).

## Preguntas de alcance a resolver conmigo en el brainstorming

Reporte por factura:
- ¿Lista de facturas del rango (id, fecha, cajero, cliente, total, estado) con detalle al
  seleccionar una? ¿O basta el listado?
- ¿Incluye anuladas/devueltas o solo `pagada`? ¿Se marca el estado?
- ¿Reimpresión/exportación del recibo entra en alcance o queda fuera (YAGNI)?

Reporte por cajero:
- ¿Agrupar por `usuario_id` en un rango: # ventas, total, neto (menos devoluciones)? ¿También por
  medio de pago dentro de cada cajero?
- ¿Se cruza con la sesión de caja (cortes por cajero por turno) o solo por rango de fechas?
- Ventas antiguas tienen `usuario_id = NULL` (previas al login): ¿cómo se muestran? (p. ej. "Sin
  cajero").

UI:
- ¿Nuevas pestañas en `PantallaReportes` ("Por factura", "Por cajero") o pantallas aparte?
- ¿El acceso a reportes se gatea por rol? (hoy `permisos.puede` existe; ver si "ver_reportes"
  debe ser solo-admin o libre).

## Formato de los entregables

- **Spec**: problema, alcance (in/out), nuevas estructuras de dominio (`ReportePorCajero`,
  `FacturaResumen`, etc.), métodos nuevos en `ServicioReportes`, reglas (usuario nulo, exclusión de
  anuladas, neto con devoluciones), impacto en UI, y qué queda **fuera** (YAGNI).
- **Plan**: tasks pequeñas en orden TDD (test primero), dominio → (persistencia si hace falta) →
  UI, cada una con sus tests y rutas exactas, **con IDs prefijados** según `planes-pos`.

Antes de escribir cada archivo, muéstrame un borrador del alcance y espera mi confirmación.
Al terminar, actualiza la fila de reportes en `docs/README-pos.md` y dame las rutas de los dos archivos.
