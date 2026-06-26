# E6 — Devoluciones con reembolso — Diseño

> Estado: propuesto (2026-06-25). Siguiente paso: plan de implementación (skill `writing-plans`).
> Contexto: cierra el resto del **flujo crítico #3** (devolución/anulación) del POS. Construye
> sobre [E3.b](2026-06-25-e3b-anulacion-venta-design.md) (anulación sin dinero) y sobre el arqueo de
> [E3](../plans/2026-06-25-e3-cierre-caja-arqueo.md).

## Objetivo

Permitir **devolver una venta `pagada`** —total o parcial por línea/cantidad— **moviendo dinero**:
registrar la salida de dinero por medio de pago (reembolso), reponer el inventario de las líneas
devueltas y reflejar el efectivo devuelto en el arqueo de la caja.

Diferencia con E3.b: la **anulación** corrige una venta sin entregar dinero (no toca `pagos` ni
arqueo); la **devolución** entrega dinero al cliente y debe cuadrar contra la caja. Son operaciones
distintas con invariantes distintas; ver [Reutilización de E3.b](#reutilización-de-e3b).

Alcance acotado (coherente con E3.b):

- Devolución **parcial por línea/cantidad** o **total**.
- **Reembolso** por medio de pago; el efectivo devuelto **resta** del cierre de caja.
- **Solo dominio + persistencia + tests.** Sin UI Qt (la `PantallaDevoluciones` queda diferida,
  igual que `PantallaCierre` en E3).
- **Nota crédito DIAN:** solo se deja la costura (interfaz). Implementación diferida al epic DIAN.

## Principio de diseño

Devolver es la operación **inversa parcial** de vender, con dinero de salida. Reusa el patrón de
E3.b (`entradas_de_anulacion` → `entradas_de_devolucion`, mismo puerto `RepositorioInventario`) y la
maquinaria de arqueo existente. La novedad —dinero— se modela como un **documento `Devolucion`**
que referencia la venta original, con sus líneas devueltas y sus reembolsos. La venta original
queda **inmutable** (su `total` no se reescribe); solo se actualiza un marcador de `estado`.

Esto evita la alternativa frágil de "venta negativa": `LineaVenta`, `MovimientoInventario` y `Pago`
exigen cantidades/montos **positivos** en `__post_init__`; una venta de signo negativo rompería esos
invariantes en cascada. El documento `Devolucion` los respeta y mapea 1:1 con la futura nota crédito
DIAN.

## Componentes

### 1. Dominio (`src/core/`)

**Entidades nuevas** en [`src/core/entidades.py`](../../../src/core/entidades.py):

```python
ESTADOS_VENTA = ("pagada", "anulada", "devuelta_parcial", "devuelta")  # + 2 estados

@dataclass(frozen=True)
class LineaDevolucion:
    producto_id: int
    cantidad_o_peso: Decimal       # cuánto se devuelve de la línea (>0; unidad o kg)
    impuesto: Decimal              # IVA contenido devuelto (prorrateado)
    subtotal: Decimal              # dinero devuelto por esta línea (IVA incluido)
    venta_linea_id: int | None = None   # referencia a la línea original
    devolucion_id: int | None = None
    id: int | None = None

@dataclass(frozen=True)
class Devolucion:
    venta_id: int
    fecha: datetime
    lineas: tuple[LineaDevolucion, ...]
    total: Decimal                 # Σ subtotales devueltos = dinero a reembolsar
    total_impuestos: Decimal
    reembolsos: tuple[Pago, ...]   # salida de dinero por medio (reusa Pago; monto>0)
    caja_sesion_id: int | None = None   # sesión donde SALE el dinero (la abierta hoy)
    usuario_id: int | None = None
    estado: str = "emitida"
    id: int | None = None
```

Los **reembolsos reusan `Pago`** (`medio_pago_id`, `monto > 0`): es el medio por el que devolvemos
el dinero. Que sea *salida* lo da el contexto (tabla `devolucion_reembolsos`), no el signo —
coherente con `MovimientoInventario`, donde el signo lo da `tipo`, no la cantidad.

**Funciones puras** en [`src/core/servicio_venta.py`](../../../src/core/servicio_venta.py):

```python
def construir_lineas_devolucion(
    venta: Venta, items: list[ItemDevolucion], ya_devuelto: dict[int, Decimal]
) -> list[LineaDevolucion]:
    """Valida cada item contra (vendido − ya_devuelto) de su línea y prorratea
    subtotal/impuesto de la línea original (mismo redondeo que la venta)."""
    # ratio = cantidad_devuelta / linea.cantidad_o_peso
    # subtotal_dev = (linea.subtotal * ratio).quantize(PESO);  impuesto_dev = (linea.impuesto * ratio)...

def entradas_de_devolucion(dev: Devolucion) -> list[MovimientoInventario]:
    return [
        MovimientoInventario(
            producto_id=linea.producto_id,
            tipo="entrada",
            cantidad=linea.cantidad_o_peso,
            fecha=dev.fecha,
            ref=f"devolucion:{dev.id}",   # distingue de "anulacion:<id>"
        )
        for linea in dev.lineas
    ]
```

`ItemDevolucion` es un input mínimo (`venta_linea_id`, `cantidad_o_peso`). El **prorrateo parte de
la `LineaVenta` capturada**, no del producto/impuesto vivo: respeta el snapshot de la venta y su
redondeo a pesos enteros. Devolución de línea completa ⇒ `ratio = 1` ⇒ subtotal/impuesto exactos.

**Servicio** `ServicioDevolucion(ventas, devoluciones, inventario)` (mismo patrón que
`ServicioAnulacion`):

```python
class ServicioDevolucion:
    def __init__(self, ventas, devoluciones, inventario) -> None: ...

    def devolver(self, venta_id, items, reembolsos, *, fecha,
                 caja_sesion_id=None, usuario_id=None) -> Devolucion:
        venta = self._ventas.por_id(venta_id)
        if venta is None:
            raise VentaNoEncontrada(...)
        if venta.estado in ("anulada", "devuelta"):
            raise VentaNoDevolvible(...)             # nada que devolver
        ya_devuelto = self._devoluciones.devuelto_por_linea(venta_id)
        lineas = construir_lineas_devolucion(venta, items, ya_devuelto)   # valida sobre-devolución
        total = sum(l.subtotal for l in lineas)
        if sum(r.monto for r in reembolsos) != total:
            raise ReembolsoDescuadrado(...)          # el dinero devuelto debe igualar lo devuelto
        dev = Devolucion(venta_id, fecha, tuple(lineas), total, ..., tuple(reembolsos),
                         caja_sesion_id, usuario_id)
        guardada = self._devoluciones.guardar(dev)
        for movimiento in entradas_de_devolucion(guardada):
            self._inventario.registrar(movimiento)
        nuevo_estado = "devuelta" if _todo_devuelto(venta, ya_devuelto, lineas) else "devuelta_parcial"
        self._ventas.marcar_estado(venta_id, nuevo_estado)
        return guardada
```

Excepciones nuevas (subclases de `ValueError`, como en E3.b): `CantidadDevueltaExcede`,
`ReembolsoDescuadrado`, `VentaNoDevolvible`. Se reusa `VentaNoEncontrada` de E3.b.

### 2. Puertos (`src/core/puertos.py`)

Puerto nuevo:

```python
class RepositorioDevoluciones(Protocol):
    def guardar(self, devolucion: Devolucion) -> Devolucion: ...
    def por_id(self, id: int) -> Devolucion | None: ...
    def de_venta(self, venta_id: int) -> list[Devolucion]: ...
    def devuelto_por_linea(self, venta_id: int) -> dict[int, Decimal]: ...  # venta_linea_id → cant. acumulada
```

`RepositorioVentas` gana un método de marcado de estado genérico:

```python
def marcar_estado(self, venta_id: int, estado: str) -> None: ...
```

`anular` de E3.b queda como caso particular (`marcar_estado(id, "anulada")`); para no tocar el
contrato ni los tests de E3.b se **mantiene `anular`** y se reimplementa el adaptador en términos de
`marcar_estado`.

### 3. Persistencia (`src/ventas/repositorio_sqlite.py`) — único lugar con SQL

`RepositorioDevolucionesSQLite` (nuevo) implementa `guardar` (inserta cabecera + líneas +
reembolsos), `por_id`, `de_venta` y `devuelto_por_linea` (`SUM(cantidad_o_peso) GROUP BY
venta_linea_id`).

`RepositorioVentasSQLite.marcar_estado`:

```python
def marcar_estado(self, venta_id: int, estado: str) -> None:
    self._conn.execute("UPDATE ventas SET estado = ? WHERE id = ?", (estado, venta_id))
    self._conn.commit()
```

**Migración nueva** `scripts/migraciones/004_devoluciones.sql` (no toca tablas existentes):

```sql
CREATE TABLE IF NOT EXISTS devoluciones (
    id             INTEGER PRIMARY KEY,
    venta_id       INTEGER NOT NULL REFERENCES ventas(id),
    fecha          TEXT NOT NULL,
    caja_sesion_id INTEGER REFERENCES caja_sesiones(id),  -- sesión del reembolso (NULLABLE)
    usuario_id     INTEGER REFERENCES usuarios(id),
    total          DECIMAL NOT NULL,
    total_impuestos DECIMAL NOT NULL,
    estado         TEXT NOT NULL DEFAULT 'emitida',
    cufe_nota      TEXT                                    -- reservado DIAN (nota crédito), sin uso fiscal hoy
);

CREATE TABLE IF NOT EXISTS devolucion_lineas (
    id             INTEGER PRIMARY KEY,
    devolucion_id  INTEGER NOT NULL REFERENCES devoluciones(id),
    venta_linea_id INTEGER REFERENCES venta_lineas(id),
    producto_id    INTEGER NOT NULL REFERENCES productos(id),
    cantidad_o_peso DECIMAL NOT NULL,
    impuesto       DECIMAL NOT NULL,
    subtotal       DECIMAL NOT NULL
);

CREATE TABLE IF NOT EXISTS devolucion_reembolsos (
    id            INTEGER PRIMARY KEY,
    devolucion_id INTEGER NOT NULL REFERENCES devoluciones(id),
    medio_pago_id INTEGER NOT NULL REFERENCES medios_pago(id),
    monto         DECIMAL NOT NULL,
    referencia    TEXT
);
```

`cufe_nota` sigue el patrón "reservado DIAN" de `clientes`/`impuestos`: columna lista, sin lógica
fiscal todavía.

### 4. Inventario — sin cambios

`ServicioDevolucion` usa el `RepositorioInventario.registrar` existente (igual que E3.b). El stock
de cada línea devuelta sube por su `cantidad_o_peso`.

## Efecto sobre el arqueo (clave: "el efectivo devuelto resta del cierre")

Se generaliza `totales_por_medio` para **netear reembolsos**: suma de `pagos` de las ventas de la
sesión (no anuladas) **menos** la suma de `devolucion_reembolsos` cuyas devoluciones pertenecen a
esa sesión.

```python
def totales_por_medio(self, caja_sesion_id: int) -> dict[int, Decimal]:
    # ingresos: pagos de ventas de la sesión, excluyendo SOLO las anuladas
    #   ... WHERE v.caja_sesion_id = ? AND v.estado != 'anulada'
    # egresos:  reembolsos de devoluciones de ESTA sesión
    #   ... JOIN devoluciones d ... WHERE d.caja_sesion_id = ?
    # totales[medio] = ingresos[medio] - egresos[medio]
```

Dos consecuencias buscadas:

1. **El cambio de filtro `estado = 'pagada'` → `estado != 'anulada'`** mantiene intacto E3.b
   (la venta anulada sigue fuera) y, a la vez, conserva los pagos originales de las ventas
   `devuelta_parcial`/`devuelta` (que sí siguen contando) — el reembolso se descuenta aparte. Una
   venta **totalmente** devuelta queda neta cero (pago original − reembolso), sin reescribir nada.
2. **`calcular_arqueo` y `ServicioCaja` no cambian.** `efectivo_ventas = totales.get(efectivo_id)`
   ya llega neto, así que `esperado = monto_inicial + efectivo_neto` refleja el cajón físicamente
   reducido por el reembolso. Todo el cambio vive en el adaptador (Ponytail).

**Decisión — la devolución golpea el arqueo de la sesión donde sale el dinero**, no el de la sesión
original de la venta. El efectivo sale del cajón de *hoy*; por eso `Devolucion.caja_sesion_id` es la
sesión abierta al momento del reembolso y el neteo de egresos se hace por `devoluciones.caja_sesion_id`.

## Estado de la venta (decisión registrada)

Se añaden `devuelta_parcial` y `devuelta` a `ESTADOS_VENTA`. Son un **marcador denormalizado**
(reportes, UI, guards de transición): la verdad de "cuánto se devolvió" vive en la tabla
`devoluciones` (`devuelto_por_linea`). Deliberadamente **no se usa el `estado` para el arqueo** —el
neteo se calcula desde `pagos`/`devolucion_reembolsos`— para que el cuadre sea robusto sin importar
el marcador. Por eso `totales_por_medio` excluye solo `anulada` y no depende de los estados nuevos.

No se modela la devolución como "venta negativa" ni se reescribe `ventas.total` (rompería los
invariantes positivos y la inmutabilidad del comprobante original / futura factura DIAN).

## Costura DIAN — nota crédito (diferida)

El documento `Devolucion` es exactamente el insumo de una **nota crédito**: referencia la venta
original (la factura), las líneas y cantidades devueltas y los totales. La costura, alineada con el
spec maestro ("reglas fiscales en `core`; `facturacion_dian` solo transporta/firma"):

- El puerto `EmisorDIAN` (hoy solo docstring en `facturacion_dian/`) ganará
  `emitir_nota_credito(devolucion, venta) -> ComprobanteDIAN`.
- El armado del payload de la nota crédito vivirá en `core` (como el armado de factura).
- `ServicioDevolucion` **no llama a DIAN hoy** (offline-first, DIAN diferido). La columna
  `devoluciones.cufe_nota` queda reservada para cuando el epic DIAN cablee el emisor.

## Reutilización de E3.b

Se evaluó **generalizar `ServicioAnulacion`** a "devolución total con reembolso = []". Se descarta
por ahora (YAGNI / Ponytail = no churn de código probado): anulación y devolución tienen invariantes
distintas (la anulación **prohíbe** mover dinero; la devolución **exige** `Σ reembolsos = total`),
y E3.b ya está implementada y testeada. Lo que sí se reutiliza: el patrón de servicio, la función
pura de movimientos de entrada, el puerto `RepositorioInventario` y el método de marcado de estado.
Si el negocio luego pide unificarlas, `ServicioAnulacion` puede reexpresarse como
`ServicioDevolucion.devolver(total, reembolsos=[])` — costura anotada, no construida.

## Atomicidad

`guardar(devolucion)` + movimientos de `entrada` + `marcar_estado` comparten la `conn` con `commit()`
propio, igual que `ServicioRegistroVenta`/`ServicioAnulacion`. Aceptable para una caja offline de un
solo cajón; el envoltorio transaccional único es el mismo refinamiento futuro ya anotado en E3/E3.b.

## Tests

**Flujo crítico #3 — devolución (integración, `tests/ventas/`):**
vender (descuenta stock, cobra efectivo) → devolver parcial una línea → afirmar:
- stock de esa línea **repuesto por la cantidad devuelta**, el resto intacto;
- `venta.estado == "devuelta_parcial"`;
- el arqueo de la sesión: `esperado` **reducido** por el efectivo reembolsado;
- la `Devolucion` queda persistida y enlazada a la venta.

Luego devolver el resto → `estado == "devuelta"`, neto efectivo de esa venta = 0 en el arqueo.

**Dominio (`tests/core/`):**
- `construir_lineas_devolucion` prorratea subtotal/impuesto; línea completa (`ratio=1`) da exactos.
- devolver más que el remanente lanza `CantidadDevueltaExcede` (suma devoluciones previas).
- `Σ reembolsos ≠ total` devuelto lanza `ReembolsoDescuadrado`.
- devolver venta inexistente → `VentaNoEncontrada`; venta `anulada` o `devuelta` → `VentaNoDevolvible`.
- `entradas_de_devolucion` produce una `entrada` por línea con `ref="devolucion:<id>"`.

**Arqueo (`tests/ventas/` o `tests/core/`):**
- `totales_por_medio` netea: venta efectivo 10 000 + reembolso efectivo 3 000 en la misma sesión ⇒
  bucket efectivo 7 000.
- reembolso en sesión distinta a la de la venta ⇒ afecta el arqueo de la **sesión del reembolso**,
  no el de la venta original.

Suite actual: **104 passed, 2 skipped**. E6 suma tests de dominio, persistencia y arqueo; no debe
romper ninguno existente (E3.b y E3 se preservan vía `estado != 'anulada'` y `anular` intacto).

## Fuera de alcance (costura, YAGNI)

- **UI Qt** de devoluciones (`PantallaDevoluciones`): diferida, como E3.b dejó la anulación y E3 el
  cierre. La sesión abierta y la selección de líneas/medios las proveerá esa pantalla; el core las
  recibe como parámetros (igual que `caja_sesion_id` en ventas).
- **Restringir el medio de reembolso al medio original** de pago: hoy el cajero elige libremente el
  medio de salida (el arqueo netea por medio). Posible regla de negocio futura.
- **Bloquear devolución si no hay caja abierta:** coherente con E3.b (que permite anular con caja
  cerrada), el core no lo fuerza; el guard, si el negocio lo pide, va en el llamador/UI.
- **Nota crédito DIAN** real (armado UBL, CUFE, transmisión): epic DIAN. Aquí solo la interfaz y la
  columna `cufe_nota` reservada.
- **Auditoría extendida** (motivo de la devolución): hoy el rastro es la fila `Devolucion`
  (fecha, usuario, líneas, reembolsos) y los `MovimientoInventario` con `ref="devolucion:<id>"`.
