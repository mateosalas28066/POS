# Prompt handoff — cerrar Fase 1 (core de caja) y arrancar Fase 2

Copia esto en una sesión nueva de Claude Code en `w:\POS`:

---

Trabaja en el repo **pos-siesa-remake** en `w:\POS` (POS autónomo Python + PySide6 + SQLite,
arquitectura hexagonal: `src/core/` sin Qt ni SQLite, SQL solo en adaptadores de repositorio).

## Contexto: qué quedó hecho

La **Fase 1 del roadmap de requerimientos del cliente** está implementada y commiteada en la rama
**`feature/fase-1-core-caja`** (creada desde `fix/errores-acumulados`, que a su vez salió de
`master`). El roadmap completo vive en
[docs/analisis-requerimientos-cliente.md](../../analisis-requerimientos-cliente.md) — léelo primero.

Commits de la rama (suite completa: **367 passed** con `python -m pytest -q`):

1. `423b45a feat(caja)` — **Movimientos manuales de efectivo**: entidad `MovimientoCaja` +
   puerto `RepositorioMovimientosCaja` (core), adaptador `RepositorioMovimientosCajaSQLite`
   (migración `007_caja_movimientos.sql`), `ServicioCaja.registrar_movimiento` (exige caja
   abierta, guardia `EfectivoInsuficiente` en egresos), `calcular_arqueo`/`Arqueo` extendidos con
   `otros_ingresos`/`otros_egresos`, reporte de cierre coherente, `DialogoMovimientoCaja` +
   botón "Movimiento de efectivo" + KPIs "Otros ingresos"/"Egresos" en `PantallaCierre`.
2. `644664d feat(reportes)` — **Ventas por categoría**: `ServicioReportes.por_categoria`
   (agrega subtotales de líneas por `categoria_id` del producto, netea devoluciones; el
   descuento ya viene aplicado por línea) + pestaña "Por categoría" en `PantallaReportes`.
3. `2682919 feat(usuarios)` — **Cambio de contraseña autoservicio**:
   `ServicioUsuarios.cambiar_password` (verifica la actual, error `CredencialInvalida`),
   puerto/adaptador `actualizar_password`, `DialogoCambioPassword` accesible desde un botón
   al pie del rail en `VentanaPrincipal`.
4. `98f0b95 docs` — README-pos (fila FASE1, suite 367) y análisis con Fase 1 marcada ✅.

## Tareas pendientes (en orden)

1. **Verificación manual en la app real**: `python -m caja` (login `admin`/`admin1234`).
   - Abrir caja → botón "Movimiento de efectivo": registrar un ingreso y un egreso con motivo;
     confirmar que los KPIs y el "Esperado" del arqueo cambian, y que un egreso mayor al
     efectivo esperado muestra error sin registrarse.
   - Vender un producto de cada categoría → Reportes → pestaña "Por categoría" muestra las
     líneas Res/Pollo/Cerdo/Fruver correctas y netea una devolución.
   - Botón inferior del rail → cambiar contraseña (probar confirmación distinta y actual
     incorrecta); re-loguear con la nueva.
2. **Integración**: preguntar al usuario si hace merge/PR de `feature/fase-1-core-caja`
   (ojo: la rama base `fix/errores-acumulados` tampoco está integrada a `master` aún —
   proponer integrar primero esa). **No merges ni push sin preguntar.**
3. **Fase 2 del roadmap — Proveedores y Compras** (siguiente feature grande):
   maestro de proveedores (espejo del patrón clientes), registro de compras con proveedor +
   líneas producto/cantidad/costo, soporte de compra "en canal" (res/cerdo) que se despieza
   vía movimientos de inventario, la compra alimenta stock y costo, historial por proveedor,
   reportes de compras por período y proveedor. Para esta fase **sí** sigue el flujo completo:
   `superpowers:brainstorming` → spec en `docs/superpowers/specs/` → plan → implementación
   (cargar skills `pos-dominio`, `db-design-pos`, `planes-pos`, `testing-pos`).

## Reglas del repo

- Ponytail (mínimo código, YAGNI, stdlib primero) — [docs/ponytail.md](../../ponytail.md).
- Tests espejo por módulo en `tests/`, correr `python -m pytest -q` tras cada grupo de cambios.
- Commits pequeños en español estilo `feat(modulo): ...` / `fix(modulo): ...`.
- Nota pendiente de seguridad: el default `admin/admin1234` sigue activo; forzar cambio en el
  primer login quedó fuera de Fase 1 (candidato a ítem suelto).
