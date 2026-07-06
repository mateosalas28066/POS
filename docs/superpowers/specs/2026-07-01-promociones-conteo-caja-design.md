# Promociones por producto + Conteo de efectivo al cierre — Diseño

- **Fecha:** 2026-07-01
- **Proyecto:** pos-siesa-remake (POS offline-first, Python 3.11 + PySide6 + SQLite, hexagonal)
- **Spec maestra:** [2026-06-25-pos-siesa-remake-design.md](2026-06-25-pos-siesa-remake-design.md)
- **Plan:** [../plans/2026-07-01-promociones-conteo-caja.md](../plans/2026-07-01-promociones-conteo-caja.md)

Una sola spec para **dos features** independientes que se implementan en este orden:

1. **Promociones por producto** (rebaja de precio sobre un producto concreto).
2. **Conteo de billetes y monedas** al cierre de caja (ayuda opcional para contar el efectivo).

Prefijos de task del plan (convención `planes-pos`, no colisionan con `E1..E8`, `E3.b`, `E7.x`,
`USUARIOS`/`CLIENTE`, `RPTFAC`): **`PROMO.x`** y **`CONTEO.x`**.

---

## Feature 1 — Promociones por producto

### Problema

El negocio (carnes y frutas) necesita rebajar el precio de **un producto concreto** de forma
temporal: "hoy la libra de X a $Y", "20% en manzanas", "descuento hasta agotar 50 unidades".
Hoy no existe ese concepto. El **descuento de cliente** que ya existe es distinto y no debe
confundirse: `Cliente.descuento_pct` / `Venta.descuento_pct` aplican un porcentaje al **total de la
venta** (todas las líneas), mientras la promoción es **por producto** y debe **convivir** con él.

Cualquier usuario que atiende caja (admin **o** cajero) debe poder crear/activar promociones, y
programar su duración de tres formas: por **tiempo** (rango de fechas), por **unidades** (se agota
tras N vendidas) o **manual** (activa hasta que alguien la apague).

### Alcance

**Dentro:**
- Entidad `Promocion` + tabla `promociones` (migración `006`) + columna `venta_lineas.promocion_id`.
- Valor de la promo como **precio fijo** o **porcentaje** (cada promo elige uno).
- Tres tipos de duración: `tiempo`, `unidades`, `manual`.
- **Una** promo activa por producto a la vez.
- Reglas de dominio puras (vigencia, precio con promo, consumo de unidades) en `core`.
- Puerto `RepositorioPromociones` + `ServicioPromociones` (crear/activar/desactivar/consumir).
- Integración en `ServicioVenta` (precio efectivo por línea) y en `ServicioRegistroVenta`
  (consumo de unidades al registrar la venta).
- Persistencia de `promocion_id` por línea (adaptador ventas).
- UI: `DialogoPromociones` abierto desde inventario, permiso `gestionar_promociones` para ambos
  roles, y marca visual mínima del precio promo en la pantalla de venta.

**Fuera (YAGNI):**
- Varias promociones simultáneas por producto.
- Promos por categoría o de carrito (2x1, combos, "lleva 3 paga 2").
- Edición completa de una promo (solo crear + activar/desactivar; para cambiarla se desactiva y se
  crea otra).
- Restaurar unidades de promo cuando hay una devolución (las unidades consumidas quedan consumidas).
- Programación de activación futura más allá del rango `desde/hasta` del tipo `tiempo`.
- Guardas de "precio promo mayor que el precio base" (responsabilidad del operador).

### Modelo de datos

**Entidad `Promocion`** (`core/entidades.py`, `@dataclass(frozen=True)`):

| Campo | Tipo | Notas |
|---|---|---|
| `producto_id` | `int` | producto al que aplica |
| `tipo_valor` | `str` | `"precio_fijo"` \| `"porcentaje"` |
| `valor` | `Decimal` | precio en pesos (fijo) **o** fracción `[0,1)` (porcentaje) |
| `tipo_duracion` | `str` | `"tiempo"` \| `"unidades"` \| `"manual"` |
| `activa` | `bool` | on/off manual; pasa a `False` al agotarse las unidades |
| `desde` | `datetime \| None` | solo `tiempo`; naive local, con hora |
| `hasta` | `datetime \| None` | solo `tiempo`; naive local, con hora |
| `unidades_limite` | `Decimal \| None` | solo `unidades` |
| `unidades_restantes` | `Decimal \| None` | arranca = `unidades_limite`; decrece por venta |
| `id` | `int \| None` | |

Constantes de dominio: `TIPOS_VALOR_PROMO = ("precio_fijo", "porcentaje")`,
`TIPOS_DURACION_PROMO = ("tiempo", "unidades", "manual")`.

Validaciones en `__post_init__`:
- `tipo_valor` en `TIPOS_VALOR_PROMO`; `tipo_duracion` en `TIPOS_DURACION_PROMO`.
- `porcentaje` → `0 ≤ valor < 1`; `precio_fijo` → `valor ≥ 0`.
- `tiempo` → `desde` y `hasta` presentes y `desde ≤ hasta`.
- `unidades` → `unidades_limite > 0`; si `unidades_restantes is None`, se inicializa a
  `unidades_limite` (el servicio de creación lo garantiza).

**Migración `006_promociones.sql`:**
- `CREATE TABLE promociones` con FK `producto_id → productos(id)`, columnas espejo de la entidad
  (`tipo_valor`, `valor`, `tipo_duracion`, `activa`, `desde`, `hasta`, `unidades_limite`,
  `unidades_restantes`).
- `ALTER TABLE venta_lineas ADD COLUMN promocion_id INTEGER REFERENCES promociones(id)` (nullable).
- Idempotente vía el runner `aplicar_migraciones` (registra en `schema_migraciones`); tipos y SQL
  neutros para portabilidad SQLite→PostgreSQL.

**Puerto `RepositorioPromociones`** (`core/puertos.py`):
`guardar(promo) -> Promocion`, `actualizar(promo) -> None`, `por_id(id) -> Promocion | None`,
`activa_por_producto(producto_id) -> Promocion | None`, `listar() -> list[Promocion]`.

**Adaptador SQLite** en `src/inventario/` (la promo es dato de merchandising del producto y se
gestiona desde la pantalla de inventario). El acceso SQL vive **solo** en el adaptador.

### Reglas de dominio (`core/promociones.py`, Python puro)

- `promo_vigente(promo, ahora) -> bool`: requiere `activa`; además —
  - `tiempo`: `desde ≤ ahora ≤ hasta`;
  - `unidades`: `unidades_restantes > 0`;
  - `manual`: solo `activa`.
- `precio_con_promo(precio_base, promo) -> Decimal`:
  - `precio_fijo` → `promo.valor`;
  - `porcentaje` → `precio_base * (1 - promo.valor)` (sin cuantizar aquí; el subtotal cuantiza).
- `consumir_unidades(promo, cantidad) -> Promocion`: devuelve la promo con
  `unidades_restantes -= cantidad` y `activa = False` si el resultado `≤ 0`. Solo aplica a
  `tipo_duracion == "unidades"`.

### Reglas de negocio y casos límite

1. **Promo + descuento de cliente = se acumulan.** La promo cambia el precio del producto y por
   tanto el `subtotal_bruto` de la línea. Luego `ServicioVenta._linea` aplica, **sin cambios**,
   `aplicar_descuento(subtotal_bruto, descuento_pct)` y recalcula `impuesto_incluido` sobre el
   subtotal final. Orden efectivo: **precio promo del producto → descuento del cliente → IVA
   incluido recalculado**.
2. **Tipo unidades agotándose.** Un solo precio por línea: si `unidades_restantes > 0`, la línea
   **entera** va en promo; al registrar la venta se descuenta `cantidad_o_peso` de la línea, de
   modo que la última compra puede exceder ligeramente el límite; al llegar a `≤ 0` la promo se
   desactiva (`activa = False`). El contador decrece por `cantidad_o_peso` (unidades enteras para
   producto por unidad; kg —decimal— para producto por peso).
3. **GS1 con precio embebido.** Cuando el código trae el `importe` ya calculado por la balanza
   (`valor_es_precio`), ese importe es la fuente de verdad y **la promo se ignora** (no se puede
   re-derivar un precio unitario coherente). En GS1 de **peso** variable (no precio) sí se calcula
   el bruto desde el precio, así que la promo **sí** aplica.
4. **Redondeo.** El precio efectivo entra a `subtotal_por_peso`/`subtotal_por_unidad`, que cuantizan
   a peso colombiano entero con `ROUND_HALF_UP`, igual que hoy. El IVA se deriva con
   `impuesto_incluido` sobre el subtotal final.
5. **Devolución de una línea con promo.** Se reembolsa el `subtotal` guardado (que ya refleja la
   promo), prorrateado por `construir_lineas_devolucion` como cualquier línea. **No** se restauran
   unidades de la promo (fuera de alcance).
6. **Promo no vigente** (expirada por tiempo, `activa = False`, o `unidades_restantes ≤ 0`): la
   línea va a **precio normal**; no se marca `promocion_id`.

### Integración en la venta

- `ServicioVenta.__init__` recibe `promociones: RepositorioPromociones | None = None`.
- `ServicioVenta.agregar(..., ahora: datetime | None = None)`: si hay repo de promociones, busca
  `activa_por_producto(producto.id)` y valida `promo_vigente(promo, ahora or datetime.now())`. Si
  vigente (y no es un GS1 con `importe` embebido), usa `precio_con_promo(producto.precio, promo)`
  para el bruto y guarda `promocion_id` en la línea. `_Entrada` y `LineaVenta` ganan
  `promocion_id: int | None = None`.
- `_linea` **no cambia** (el descuento de cliente y el IVA se aplican sobre el bruto ya rebajado).
- `ServicioRegistroVenta.registrar`: tras `guardar`, para cada línea con `promocion_id` cuya promo
  sea de tipo `unidades`, aplica `consumir_unidades` y persiste con `actualizar` (SQL solo en
  adaptador). Recibe `promociones: RepositorioPromociones | None = None`.
- Adaptador `RepositorioVentasSQLite` (`src/ventas/`): persiste y lee `venta_lineas.promocion_id`.

### Impacto en UI

- **Permiso** `gestionar_promociones` (`core/permisos.py`), permitido a **admin y cajero** (no
  entra en `PERMISOS_ADMIN`; `puede(rol, "gestionar_promociones")` es `True` para ambos). No se
  reutiliza `aplicar_descuento_manual` (que es solo-admin).
- **`DialogoPromociones`** (`src/caja/`): se abre con un botón desde la pantalla de inventario/
  productos. Permite crear (elegir producto, `tipo_valor`, `valor`, `tipo_duracion` y sus campos),
  listar y activar/desactivar. Usa `ServicioPromociones.crear`, que exige **una promo activa por
  producto** (lanza si ya hay otra activa).
- **Pantalla de venta**: marca visual mínima (una etiqueta "promo" en la línea) cuando la línea
  tiene `promocion_id`. El `precio_unit`/`subtotal` ya muestran el precio rebajado.

---

## Feature 2 — Conteo de billetes y monedas al cierre (opcional)

### Problema

Al cerrar caja, el cajero teclea a mano el "efectivo contado" en un `QDoubleSpinBox`. Se quiere una
**ayuda opcional** para contar el efectivo por denominaciones colombianas, que produzca ese número.
**No bloquea nada**: si el cajero no la usa, el cierre procede igual que hoy.

### Alcance

**Dentro:**
- Denominaciones colombianas y cálculo del total contado (Σ denominación × cantidad).
- `DialogoConteoEfectivo` con una fila por denominación (spinbox de cantidad) y total en vivo.
- Botón **"Contar efectivo"** junto al campo en `pantalla_cierre` (vista de arqueo) que abre el
  diálogo y, al aceptar, **rellena `monto_contado`**.

**Fuera (YAGNI):**
- Volver obligatorio el conteo (sigue siendo opcional; el botón "Cerrar caja" no cambia su flujo).
- Persistir el desglose por denominación (nadie lo consume hoy; el cierre ya guarda
  `monto_contado`).
- Cambiar `ServicioCaja.cerrar` ni el arqueo (`calcular_arqueo` intacto).

### Diseño

- **Ubicación (decisión del dueño): todo en la capa UI** (`src/caja/`), no en `core`. El cálculo se
  deja como **función pura a nivel de módulo** para poder testearlo sin instanciar Qt.
- `src/caja/conteo.py`:
  - `DENOMINACIONES = (100000, 50000, 20000, 10000, 5000, 2000, 1000, 500, 200, 100, 50)` —
    **una sola fila para 1000** (moneda y billete suman igual; se listan juntos).
  - `total_conteo(conteo: dict[int, int]) -> Decimal`: `Σ denominación × cantidad`. Ignora
    cantidades `0`; valida cantidades no negativas.
- `DialogoConteoEfectivo` (`src/caja/`): una fila por denominación con `QSpinBox` de cantidad,
  etiqueta de total en vivo recalculada con `total_conteo`, botones Aceptar/Cancelar.
- `PantallaCierre` (vista de arqueo): botón **"Contar efectivo"** junto a "Efectivo contado". Al
  aceptar el diálogo, escribe el total en `self._monto_contado` (dispara `valueChanged` →
  `_recalcular_arqueo`). El conteo es **efímero**: solo produce el total.

---

## Plan de implementación (resumen; detalle en el plan)

Orden TDD (test primero), dominio → persistencia → UI. Primero **todas** las `PROMO.x`, luego las
`CONTEO.x`.

**Promociones**
- `PROMO.1` — Entidad `Promocion` + validaciones (`core/entidades.py`).
- `PROMO.2` — Reglas puras `promo_vigente` / `precio_con_promo` / `consumir_unidades`
  (`core/promociones.py`).
- `PROMO.3` — Puerto `RepositorioPromociones` (`core/puertos.py`) + `ServicioPromociones`
  (`core/servicio_promociones.py`).
- `PROMO.4` — Migración `scripts/migraciones/006_promociones.sql` (tabla + `venta_lineas.promocion_id`).
- `PROMO.5` — Adaptador `RepositorioPromocionesSQLite` (`src/inventario/`).
- `PROMO.6` — Integración en `ServicioVenta` (precio efectivo + `promocion_id` por línea).
- `PROMO.7` — Consumo de unidades en `ServicioRegistroVenta`.
- `PROMO.8` — Persistencia de `promocion_id` en `RepositorioVentasSQLite` (`src/ventas/`).
- `PROMO.9` — Permiso `gestionar_promociones` (`core/permisos.py`).
- `PROMO.10` — `DialogoPromociones` (`src/caja/`) + botón desde inventario.
- `PROMO.11` — Marca visual del precio promo en la pantalla de venta.

**Conteo**
- `CONTEO.1` — `caja/conteo.py`: `DENOMINACIONES` + `total_conteo` (función pura).
- `CONTEO.2` — `DialogoConteoEfectivo` (`src/caja/`).
- `CONTEO.3` — Botón "Contar efectivo" en `PantallaCierre` que rellena `monto_contado`.

## Estrategia de pruebas

- Dominio sin DB: entidad `Promocion`, reglas (`core/promociones.py`), `ServicioPromociones` con
  repo fake, integración en `ServicioVenta`/`ServicioRegistroVenta` con fakes.
- Integración de repositorios contra SQLite temporal: adaptador de promociones, `promocion_id` en
  el adaptador de ventas, migración `006` idempotente.
- Casos límite obligatorios con test: promo + descuento cliente (acumulación e IVA), unidades
  agotándose a mitad de línea, GS1 con precio embebido ignora promo, redondeo a peso entero.
- Conteo: test unitario de `total_conteo` (sin Qt); diálogo/botón como smoke test mínimo.
