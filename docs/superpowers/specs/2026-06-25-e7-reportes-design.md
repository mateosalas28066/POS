# E7 — Reportes — Diseño

> Estado: propuesto (2026-06-25). Siguiente paso: plan de implementación (skill `writing-plans`).
> Contexto: implementa el epic **E7 (Reportes)** del [spec maestro](2026-06-25-pos-siesa-remake-design.md)
> (depende de E1 y E3). Construye **solo lectura** sobre lo que E1–E6 ya persisten; no añade tablas.

## Objetivo

Dar visibilidad del negocio leyendo los datos transaccionales existentes, con tres reportes:

1. **Ventas por período:** total, impuestos, desglose por medio de pago y **neto de devoluciones**,
   acotado por un rango de fechas `[desde, hasta)`.
2. **Cierre/arqueo de una sesión:** bundle de la sesión + su `Arqueo` (ya en `core`) + desglose por
   medio + conteo de ventas y devoluciones, acotado por `caja_sesion_id`.
3. **Inventario/movimientos:** por producto en el rango (entradas, salidas, neto) **y** la lista plana
   de movimientos con su `ref` (`venta`/`anulacion`/`devolucion`), acotado por rango de fechas.

Alcance acotado (Ponytail / YAGNI):

- **Solo dominio + persistencia + tests.** Sin UI Qt (la `PantallaReportes` queda diferida, como E3
  difirió `PantallaCierre` y E6 `PantallaDevoluciones`). La UI será un consumidor fino posterior.
- **Sin migración nueva ni tablas nuevas.** E7 es agregación de lectura sobre el modelo actual.
- **Sin export** (CSV/PDF), **sin reportes por cajero**, **sin top-sellers ni valuación por costo**:
  costuras anotadas (los datos ya existen), no construidas.

## Principio de diseño

Un reporte es una **proyección de lectura**: leer filas y **sumar `Decimal` en Python**. La regla del
proyecto —*"sumas en Python, nunca `SUM()` de SQL"*— fija la forma: los **adaptadores devuelven
entidades/valores sin agregar** (scoped por rango o por sesión) y un `ServicioReportes` en `core`
arma los objetos-valor de reporte sumando.

Por los **límites de módulo** ("SQL solo en adaptadores de `src/ventas/` y `src/inventario/`"), no
existe un adaptador único de reportes que cruce ambos. Por eso E7 **extiende los repos existentes**
con métodos de lectura acotados, reutilizando los mappers ya probados de E1–E6 sin tocar su lógica.
Esto evita un módulo nuevo y mantiene cada SQL en su frontera.

El reporte de cierre **reusa `calcular_arqueo`** (función pura de `core/calculos.py`) y el ya existente
`RepositorioVentas.totales_por_medio` (que desde E6 **netea reembolsos por sesión**): el cierre no
recalcula el neteo, lo compone.

## Componentes

### 1. Objetos-valor de reporte (`src/core/servicio_reportes.py`, módulo nuevo)

Dominio puro; `@dataclass(frozen=True)`. Todos los montos son `Decimal` ya cuantizados a peso entero
(provienen de cifras guardadas); E7 **solo las suma**, no reintroduce redondeo.

```python
@dataclass(frozen=True)
class ReporteVentas:
    desde: datetime
    hasta: datetime
    num_ventas: int                      # ventas no anuladas en el rango
    total: Decimal                       # Σ ventas.total (no anuladas)
    total_impuestos: Decimal             # Σ ventas.total_impuestos (no anuladas)
    por_medio: dict[int, Decimal]        # NETO por medio: Σ pagos − Σ reembolsos (del rango)
    total_devoluciones: Decimal          # Σ devoluciones.total del rango
    total_devoluciones_impuestos: Decimal
    neto: Decimal                        # total − total_devoluciones


@dataclass(frozen=True)
class MovimientoProducto:
    producto_id: int
    entradas: Decimal                    # Σ cantidad de movimientos tipo "entrada"
    salidas: Decimal                     # Σ cantidad de movimientos tipo "salida"
    neto: Decimal                        # entradas − salidas


@dataclass(frozen=True)
class ReporteInventario:
    desde: datetime
    hasta: datetime
    por_producto: tuple[MovimientoProducto, ...]   # agregado (orden estable por producto_id)
    movimientos: tuple[MovimientoInventario, ...]  # detalle plano con ref


@dataclass(frozen=True)
class ReporteCierre:
    sesion: CajaSesion                   # apertura/cierre, montos, estado
    arqueo: Arqueo                       # reusa la entidad y calcular_arqueo
    por_medio: dict[int, Decimal]        # neto por medio de la sesión (totales_por_medio)
    num_ventas: int                      # ventas no anuladas de la sesión
    total_devoluciones: Decimal          # Σ devoluciones.total de la sesión
```

`por_medio` usa `medio_pago_id` **crudo**: resolver nombres es trabajo de la UI futura, no del reporte
(`core` no conoce `medios_pago` por nombre). Coherente con `totales_por_medio`.

### 2. Servicio `ServicioReportes` (`src/core/servicio_reportes.py`)

```python
class ServicioReportes:
    def __init__(self, ventas: RepositorioVentas, devoluciones: RepositorioDevoluciones,
                 inventario: RepositorioInventario, sesiones: RepositorioCajaSesiones,
                 efectivo_medio_pago_id: int = 1) -> None: ...

    def ventas(self, desde: datetime, hasta: datetime) -> ReporteVentas:
        vs = self._ventas.ventas_en(desde, hasta)            # ya excluye anuladas
        pagos = self._ventas.pagos_en(desde, hasta)          # ya excluye anuladas
        devs = self._devoluciones.devoluciones_en(desde, hasta)
        # total = Σ v.total ; total_impuestos = Σ v.total_impuestos ; num_ventas = len(vs)
        # ingresos[medio] = Σ pagos.monto ; egresos[medio] = Σ reembolsos.monto (de devs)
        # por_medio[medio] = ingresos − egresos
        # total_devoluciones = Σ d.total ; neto = total − total_devoluciones
        ...

    def inventario(self, desde: datetime, hasta: datetime) -> ReporteInventario:
        movs = self._inventario.movimientos_en(desde, hasta)
        # agrupar por producto_id: entradas (tipo "entrada"), salidas (tipo "salida"), neto
        # por_producto ordenado por producto_id; movimientos = tuple(movs)
        ...

    def cierre(self, sesion_id: int) -> ReporteCierre:
        sesion = self._sesiones.por_id(sesion_id)            # CajaNoEncontrada si None
        por_medio = self._ventas.totales_por_medio(sesion_id)  # ya netea reembolsos (E6)
        efectivo = por_medio.get(self._efectivo_id, CERO)
        contado = sesion.monto_contado if sesion.monto_contado is not None else efectivo
        arqueo = calcular_arqueo(sesion.monto_inicial, efectivo, contado)
        num_ventas = len(self._ventas.ventas_de_sesion(sesion_id))
        total_devoluciones = sum((d.total for d in self._devoluciones.de_sesion(sesion_id)), CERO)
        ...
```

Detalle del `monto_contado` en `cierre`: una sesión **cerrada** guarda su `monto_contado` → el arqueo
del reporte refleja el cuadre real registrado al cerrar. Una sesión **abierta** aún no tiene conteo
físico; el reporte usa el **efectivo esperado** como `contado` (diferencia 0), de modo que el reporte
de una caja viva muestra el esperado sin inventar un faltante/sobrante. Excepción nueva
`SesionNoEncontrada(ValueError)` si la sesión no existe.

### 3. Métodos de lectura nuevos en puertos (`src/core/puertos.py`)

Aditivos; no cambian las firmas existentes.

```python
class RepositorioVentas(Protocol):
    ...  # guardar, por_id, pagos_de, anular, marcar_estado, totales_por_medio (intactos)
    def ventas_en(self, desde: datetime, hasta: datetime) -> list[Venta]: ...
    def pagos_en(self, desde: datetime, hasta: datetime) -> list[Pago]: ...
    def ventas_de_sesion(self, caja_sesion_id: int) -> list[Venta]: ...

class RepositorioDevoluciones(Protocol):
    ...  # guardar, por_id, de_venta, devuelto_por_linea (intactos)
    def devoluciones_en(self, desde: datetime, hasta: datetime) -> list[Devolucion]: ...
    def de_sesion(self, caja_sesion_id: int) -> list[Devolucion]: ...

class RepositorioInventario(Protocol):
    ...  # registrar, stock_de (intactos)
    def movimientos_en(self, desde: datetime, hasta: datetime) -> list[MovimientoInventario]: ...
```

`puertos.py` debe importar `datetime` para los nuevos tipos de firma.

**Convención de rango:** `[desde, hasta)` (inicio inclusivo, fin exclusivo). En SQL:
`fecha >= ? AND fecha < ?`, comparando las cadenas ISO-8601 ya almacenadas (orden lexicográfico =
orden cronológico para ISO-8601). Filtro de estado: `ventas_en`/`pagos_en` excluyen `anulada`
(`estado != 'anulada'`), igual que `totales_por_medio`.

### 4. Adaptadores (extensión de los existentes)

**`src/ventas/repositorio_sqlite.py`** — `RepositorioVentasSQLite`:

- `ventas_en(desde, hasta)`: `SELECT id FROM ventas WHERE fecha >= ? AND fecha < ? AND estado !=
  'anulada' ORDER BY id` y rehidratar cada `Venta` con el mapper existente (reusa `por_id`). El
  volumen offline de una caja es pequeño; la simplicidad (reuso del mapper probado) prima sobre evitar
  el N+1. `ventas_de_sesion` igual pero con `WHERE caja_sesion_id = ? AND estado != 'anulada'`.
- `pagos_en(desde, hasta)`: `SELECT p.* FROM pagos p JOIN ventas v ON v.id = p.venta_id
  WHERE v.fecha >= ? AND v.fecha < ? AND v.estado != 'anulada' ORDER BY p.id` → `list[Pago]`.

**`src/ventas/repositorio_sqlite.py`** — `RepositorioDevolucionesSQLite`:

- `devoluciones_en(desde, hasta)`: `SELECT id FROM devoluciones WHERE fecha >= ? AND fecha < ?
  ORDER BY id` y rehidratar con `por_id` (reusa el mapper que ya carga líneas + reembolsos).
- `de_sesion(caja_sesion_id)`: igual con `WHERE caja_sesion_id = ?`.

**`src/inventario/repositorio_sqlite.py`** — `RepositorioInventarioSQLite`:

- `movimientos_en(desde, hasta)`: `SELECT * FROM inventario_movimientos WHERE fecha >= ? AND fecha < ?
  ORDER BY id` → `list[MovimientoInventario]` (nuevo mapper `_fila_a_movimiento`, hoy `stock_de` solo
  lee `tipo`/`cantidad`).

Ningún método nuevo agrega con `SUM()`; todos devuelven filas y `core` suma.

## Modelo de datos — sin cambios

E7 no añade tablas ni columnas ni migración. Lee `ventas`, `venta_lineas`, `pagos`, `caja_sesiones`,
`devoluciones`, `devolucion_lineas`, `devolucion_reembolsos`, `inventario_movimientos`.

## Tests

**Dominio (`tests/core/test_servicio_reportes.py`, con fakes):**

- `ventas`: dos ventas (una con reembolso parcial) → `total`/`total_impuestos`/`num_ventas` correctos;
  `por_medio` neteado (ingresos − reembolsos); `total_devoluciones` y `neto = total − devoluciones`.
- `ventas`: una venta `anulada` en el rango **no** cuenta (ni en `total`, ni `num_ventas`, ni medios).
- `inventario`: movimientos mixtos de dos productos → `por_producto` con entradas/salidas/neto correctos
  y orden estable; `movimientos` conserva la lista plana con `ref`.
- `cierre`: sesión cerrada con `monto_contado` → `arqueo` con su diferencia real; `por_medio` neto;
  `num_ventas` y `total_devoluciones` de la sesión.
- `cierre`: sesión abierta (sin `monto_contado`) → `arqueo` usa el esperado como contado (diferencia 0).
- `cierre`: sesión inexistente → `SesionNoEncontrada`.

**Persistencia ventas (`tests/ventas/test_reportes_sqlite.py`):**

- `ventas_en` filtra por `[desde, hasta)` y excluye `anulada`; `ventas_de_sesion` filtra por sesión.
- `pagos_en` devuelve los pagos de ventas no anuladas del rango.
- `devoluciones_en` / `de_sesion` rehidratan la `Devolucion` completa (líneas + reembolsos).

**Persistencia inventario (`tests/inventario/test_reportes_movimientos.py`):**

- `movimientos_en` devuelve los movimientos del rango con `tipo`/`cantidad`/`ref`/`fecha` correctos.

Suite base: **128 passed, 2 skipped.** E7 suma tests; ningún test existente puede romperse (todos los
métodos nuevos son aditivos; no se modifican firmas ni SQL de E1–E6).

## Fuera de alcance (costura, YAGNI)

- **UI Qt** `PantallaReportes`: diferida; consumirá `ServicioReportes` y resolverá nombres de medio.
- **Reportes por cajero/usuario**: `usuario_id` ya está en `ventas`/`devoluciones`; el reporte se añade
  cuando el negocio lo pida (mismo patrón `ventas_en`).
- **Top-sellers / productos más vendidos**: `venta_lineas` ya está; `ventas_en` devuelve `Venta`
  completa (con líneas) para que ese reporte futuro no exija nuevo SQL.
- **Valuación de inventario por costo**: `productos.costo` existe; fuera de alcance hoy.
- **Export CSV/PDF y rango por defecto "hoy"**: los provee la UI/CLI futura.
- **Envoltura transaccional**: E7 es solo lectura; no aplica.
