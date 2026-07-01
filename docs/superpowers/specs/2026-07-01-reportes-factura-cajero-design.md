# Spec — Reportes por factura y por cajero (epic `RPTFAC`)

> Fecha: 2026-07-01
> Proyecto: pos-siesa-remake · Spec maestra: [2026-06-25-pos-siesa-remake-design.md](2026-06-25-pos-siesa-remake-design.md)
> Plan derivado: [../plans/2026-07-01-reportes-factura-cajero.md](../plans/2026-07-01-reportes-factura-cajero.md)

## Problema

`ServicioReportes` hoy agrega ventas por **período** y por **medio de pago**
(`ServicioReportes.ventas`), más inventario y arqueo por sesión (`cierre`). No permite:

- **Auditar factura por factura** dentro de un rango (¿qué se vendió, quién la hizo, a qué
  cliente, en qué estado?).
- **Medir por cajero**: productividad y corte de un cajero en un rango o en su turno (sesión).

El dato ya está persistido y sin usar en reportes: `Venta` tiene `usuario_id`, `cliente_id`,
`estado`, `total`, `total_impuestos`, `descuento_pct`; `Pago` tiene `venta_id`; `Devolucion`
tiene `usuario_id`. Los puertos ya exponen `ventas_en`, `pagos_en`, `devoluciones_en`,
`ventas_de_sesion`, `de_sesion`, `pagos_de`, y `RepositorioUsuarios.por_id`. Esto es
**agregación en Python dentro de `core`**: sin métodos de repositorio nuevos y sin SQL nueva.

## Alcance

### Dentro (in)

1. **Reporte por factura** — listado del rango con detalle al seleccionar.
2. **Reporte por cajero (rango)** — agregado por `usuario_id` con desglose por medio de pago.
3. **Reporte por cajero (sesión)** — cruce del corte por cajero contra una sesión/turno de caja.
4. **UI**: dos pestañas nuevas en `PantallaReportes` reutilizando el filtro de fechas actual.

### Fuera (out — YAGNI)

- **No** se crea un dataclass `FacturaResumen`: `Venta` ya carga todo lo que la tabla y el
  detalle necesitan (`lineas`, `usuario_id`, `cliente_id`, `total`, `total_impuestos`,
  `estado`). El listado devuelve `Venta` directamente.
- **No** hay reimpresión ni exportación de recibos.
- **No** se gatea reportes por rol (no se añade acción `ver_reportes`): acceso libre, como hoy.
- **No** hay cambios de esquema ni métodos de repositorio nuevos.
- **No** se añade desglose por medio en la vista de sesión más allá de lo derivable con
  `pagos_de` (se reutiliza el mismo `ReporteCajero`).

## Nuevas estructuras de dominio

En `src/core/servicio_reportes.py`:

```python
@dataclass(frozen=True)
class ReporteCajero:
    usuario_id: int | None          # None = "Sin cajero" (ventas previas al login)
    num_ventas: int
    total: Decimal                  # Σ Venta.total del cajero
    total_impuestos: Decimal        # Σ Venta.total_impuestos del cajero
    total_devoluciones: Decimal     # Σ Devolucion.total atribuidas al cajero
    neto: Decimal                   # total − total_devoluciones
    por_medio: dict[int, Decimal]   # neto por medio: Σ pagos − Σ reembolsos del cajero
```

No se introduce ninguna otra estructura. El reporte por factura reutiliza la entidad `Venta`.

## Métodos nuevos en `ServicioReportes`

Todos en `src/core/servicio_reportes.py`, solo lectura, agregación en Python:

| Método | Firma | Fuente de datos | Notas |
|---|---|---|---|
| Por factura | `facturas(desde, hasta) -> tuple[Venta, ...]` | `ventas_en(desde, hasta)` | Ordena por `(fecha, id)`. Excluye anuladas (lo hace `ventas_en`). |
| Por cajero (rango) | `por_cajero(desde, hasta) -> tuple[ReporteCajero, ...]` | `ventas_en`, `pagos_en`, `devoluciones_en` | Agrupa por `usuario_id`; ordena `usuario_id` asc con `None` al final. |
| Por cajero (sesión) | `por_cajero_de_sesion(sesion_id) -> tuple[ReporteCajero, ...]` | `sesiones.por_id`, `ventas_de_sesion`, `de_sesion`, `pagos_de` | `raise SesionNoEncontrada` si no existe (reusa la excepción actual). |

### Cómo se computa `por_cajero` (rango)

1. `vs = ventas_en(desde, hasta)` → agrupar por `usuario_id`: `num_ventas`, `total`,
   `total_impuestos`.
2. `pagos_en(desde, hasta)`: cada `Pago` tiene `venta_id`; se mapea `venta_id → usuario_id`
   (a partir de `vs`) y se suma al `por_medio` del cajero. Pagos cuyo `venta_id` no esté en
   `vs` (p. ej. de una venta anulada) se ignoran.
3. `devoluciones_en(desde, hasta)`: cada `Devolucion` aporta `total` a `total_devoluciones`
   del cajero `Devolucion.usuario_id`, y cada reembolso resta en `por_medio` de ese cajero.
4. `neto = total − total_devoluciones` por cajero.

### Cómo se computa `por_cajero_de_sesion`

Igual que el rango pero acotado a la sesión: `ventas_de_sesion(sesion_id)` para las ventas,
`de_sesion(sesion_id)` para las devoluciones, y `pagos_de(venta_id)` por cada venta de la
sesión para el `por_medio`. Reutiliza el mismo `ReporteCajero`.

## Reglas de negocio

- **Cajero nulo**: `usuario_id = None` (ventas previas al login) se agrupa como un cajero más
  con `usuario_id = None`. El dominio **no** inventa un id; la etiqueta "Sin cajero" es de UI.
  En el orden va al final.
- **Exclusión de anuladas**: se hereda de `ventas_en` / `ventas_de_sesion`; el reporte por
  factura por tanto lista `pagada`, `devuelta` y `devuelta_parcial`, nunca `anulada`.
- **Neto con devoluciones**: `neto = total − total_devoluciones`, consistente con
  `ReporteVentas.neto`.
- **Atribución de devoluciones**: la devolución se imputa al cajero que la **procesó**
  (`Devolucion.usuario_id`), no al de la venta original. Es el dato persistido y refleja la
  actividad del turno; se documenta en el código.
- **Pagos huérfanos**: un `Pago` cuyo `venta_id` no aparezca en el conjunto de ventas del
  rango/sesión (p. ej. venta anulada) no se cuenta en `por_medio`.
- Dinero siempre en `Decimal`. `core` no conoce Qt ni SQLite.

## Impacto en UI (`src/caja/pantalla_reportes.py`)

Dos pestañas nuevas en el `QTabWidget` existente, reutilizando la barra de fechas y
`_rango()` ya presentes:

- **"Por factura"**: `QTableWidget` con columnas *#, Fecha, Cajero, Cliente, Total, IVA,
  Estado*. Al seleccionar una fila, un segundo `QTableWidget` (o panel) muestra las
  `Venta.lineas` (descripción, cantidad/peso, subtotal, IVA) y los pagos vía
  `repo_ventas.pagos_de(id)`. Nombres de cajero (`repo_usuarios.por_id`) y cliente
  (`repo_clientes.por_id`) se resuelven en UI, igual que hoy se resuelven medios/productos.
  `usuario_id` nulo → "Sin cajero"; `cliente_id` nulo → "—".
- **"Por cajero"**: `QTableWidget` con *Cajero, # Ventas, Total, Devoluciones, Neto* y, por
  cada cajero, filas de desglose por medio de pago. Un `QComboBox` alterna la fuente:
  **Rango** (usa `por_cajero` con `_rango()`) o **Sesión** (poblado con
  `repo_sesiones.listar()`, usa `por_cajero_de_sesion`). "Sin cajero" para `usuario_id` nulo.

`ContextoApp` ya expone `repo_usuarios`, `repo_clientes`, `repo_sesiones` y `repo_medios_pago`;
**no requiere cambios**.

## Arquitectura y restricciones

- Aislamiento hexagonal: la lógica de agregación vive en `core`; la UI solo formatea y resuelve
  nombres vía puertos.
- Sin dependencias nuevas (stdlib + PySide6 existentes).
- Sin métodos de repositorio nuevos ni SQL nueva.
- Suite actual: **259 passed**. Cada task añade sus tests (TDD, test primero).

## Convención de IDs de task

Prefijo de epic único: **`RPTFAC`** (no colisiona con `E1..E8`, `E3.b`, `E7.x`,
`USUARIOS`/`CLIENTE`). Detalle en el plan derivado.
