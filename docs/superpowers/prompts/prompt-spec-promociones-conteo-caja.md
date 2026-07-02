# Prompt para otra sesión — Spec + plan: Promociones por producto + Conteo de efectivo al cierre

> Copia todo lo que está debajo de la línea y pégalo como primer mensaje en una sesión
> nueva de Claude Code abierta en `w:\POS`.

---

Trabaja en el repo `w:\POS` (proyecto **pos-siesa-remake**: POS offline-first en Python 3.11 +
PySide6 + SQLite, arquitectura hexagonal). Lee primero `CLAUDE.md`, `docs/README-pos.md` y la
spec maestra en `docs/superpowers/specs/2026-06-25-pos-siesa-remake-design.md`.

## Tu tarea

**NO implementes código todavía.** Produce **una sola spec** y **un solo plan** en
`docs/superpowers/` que cubran DOS features, en este orden:

1. **Promociones por producto** (empieza por esta).
2. **Conteo de billetes y monedas al cierre de caja** (opcional, ayuda para contar).

Entregables:
- Spec en `docs/superpowers/specs/` (una sola, con ambas features y su interacción).
- Plan TDD en `docs/superpowers/plans/` (uno solo; primero las tasks de promociones, luego las de conteo).

Carga **obligatoriamente** estas skills antes de empezar:
- `superpowers:brainstorming` — acordar el alcance conmigo ANTES de escribir la spec.
- `superpowers:writing-plans` — para el plan.
- `planes-pos` — **convención obligatoria de IDs de task** (ver abajo; no es opcional).
- `pos-dominio`, `db-design-pos` (promociones necesita tabla nueva), `testing-pos`.

Respeta las **Reglas Ponytail** (mínimo código necesario, YAGNI, stdlib primero).

## Convención de IDs de task (skill `planes-pos`) — CRÍTICO

El plan de Usuarios+Cliente usó `Task 1..16` sin prefijo y el ejecutor confundió tasks con las de
otros planes. En ESTE plan, como hay dos features, **usa dos prefijos distintos** (uno por feature),
en MAYÚSCULAS, distintos de los ya usados (`E1..E8`, `E3.b`, `E7.x`, `USUARIOS`, `RPTFAC`):
- Promociones: `PROMO.1`, `PROMO.2`, …
- Conteo: `CONTEO.1`, `CONTEO.2`, …

Título único y específico por task con módulo/archivo destino; nada de títulos que sean solo
`Promociones`/`Cierre`. Cada task nombra sus rutas Create/Modify/Test exactas. En el tracking usa
el ID con prefijo completo. Confírmame los prefijos en el brainstorming.

---

## Feature 1 — Promociones por producto

**Qué quiere el negocio (requisito del dueño):**
- La promoción aplica a **un producto específico** (a diferencia del descuento del cliente, que es
  sobre el total de la venta).
- La puede poner **admin o cajero** (ambos roles; NO es solo-admin).
- Debe poder **programarse su duración** de tres formas: por **tiempo** (rango de fechas), por
  **unidades** (se agota tras N unidades vendidas en promo), o **manual** (activa hasta que alguien
  la apague).

**Contexto verificado del código (no lo re-derives):**
- `Producto` ([src/core/entidades.py](../../src/core/entidades.py)) tiene `precio`, `impuesto_id`,
  `vendido_por_peso`, `id`, etc. No hay ningún concepto de promoción hoy.
- El **descuento existente es distinto y NO se debe confundir**: `Cliente.descuento_pct` y
  `Venta.descuento_pct` aplican un porcentaje al **total de la venta**; `ServicioVenta.establecer_
  descuento(pct)` lo aplica por línea a TODAS las líneas y recalcula el IVA incluido
  ([src/core/servicio_venta.py](../../src/core/servicio_venta.py), método `_linea`). La promoción,
  en cambio, es **por producto** y debe convivir con ese descuento.
- `ServicioVenta._linea(entrada)` calcula `subtotal = aplicar_descuento(subtotal_bruto,
  descuento_pct)` y luego `impuesto_incluido(subtotal, tarifa)`. Aquí es donde una promoción de
  producto tendría que entrar (sobre el precio del producto, antes o en combinación con el
  descuento del cliente).
- `aplicar_descuento` y `impuesto_incluido` viven en [src/core/calculos.py](../../src/core/calculos.py)
  (todo `Decimal`, redondeo `ROUND_HALF_UP` a peso entero).
- **Permisos:** `core/permisos.puede(rol, accion)` — hoy `aplicar_descuento_manual` es solo-admin.
  Ojo: el requisito dice que la promoción la puede crear también el cajero, así que probablemente
  NO uses esa acción; decide en el brainstorming si se añade una acción nueva (p. ej.
  `gestionar_promociones`) permitida a ambos roles.
- Migraciones SQLite numeradas en `scripts/migraciones/` (hoy hasta `005`); la tabla de
  promociones va como `006_*.sql`. El runner `aplicar_migraciones` ya es idempotente (registra en
  `schema_migraciones`).

**Preguntas de alcance (promociones):**
- ¿La promoción es un **porcentaje** sobre el precio del producto, o un **precio promocional fijo**?
- Interacción con `Cliente.descuento_pct`: ¿se aplican ambos (promo primero al producto, luego
  descuento del cliente al total), o la promo excluye el descuento? ¿Cómo se recalcula el IVA incluido?
- Tipo "unidades": ¿el contador de unidades vendidas se persiste y decrece con cada venta? ¿Qué pasa
  al agotarse a mitad de una línea con cantidad > restante?
- Tipo "tiempo": ¿fechas con hora? ¿zona horaria local?
- ¿Una promo activa por producto a la vez, o varias? ¿Dónde se gestionan (nueva `PantallaPromociones`,
  o dentro de la de inventario)? ¿Se marca visualmente el precio promo en la pantalla de venta?
- ¿La venta persiste que una línea llevaba promo (para recibo/reportes), o basta el precio final?

---

## Feature 2 — Conteo de billetes y monedas al cierre (opcional)

**Qué quiere el negocio:**
- Al pulsar **"Cerrar caja"** debe aparecer, **como opción opcional**, un **conteo** que ayude a
  contar el efectivo. **No bloquea nada**: es una ayuda; si el cajero no lo usa, el cierre procede
  igual que hoy.
- Pregunta cuántas monedas de **50, 100, 200, 500, 1000** y cuántos billetes de **1000, 2000, 5000,
  10000, 20000, 50000, 100000** (denominaciones de Colombia).
- El total contado (Σ denominación × cantidad) es el "efectivo contado" que ya usa el arqueo.

**Contexto verificado del código (no lo re-derives):**
- El cierre vive en [src/caja/pantalla_cierre.py](../../src/caja/pantalla_cierre.py): botón
  "Cerrar caja" → `_cerrar()` toma `self._monto_contado` (un `QDoubleSpinBox`) y llama
  `svc_caja.cerrar(sesion_id, fecha, monto_contado)`.
- `ServicioCaja.cerrar` ([src/core/servicio_caja.py](../../src/core/servicio_caja.py)) calcula el
  arqueo (`calcular_arqueo` en calculos.py: `esperado = monto_inicial + efectivo_ventas`,
  `diferencia = contado − esperado`) y persiste la sesión con `monto_contado`.
- Hoy el "efectivo contado" se teclea a mano. Esta feature solo agrega un **ayudante de conteo por
  denominaciones** que produce ese número.

**Preguntas de alcance (conteo):**
- ¿El conteo es un **diálogo** que se abre desde el botón de cierre (o un botón "Contar efectivo"
  junto al campo) y al aceptar **rellena `monto_contado`**? Confirmar que NO se vuelve obligatorio.
- La denominación **1000** aparece como moneda y como billete: ¿dos filas separadas (moneda 1000 /
  billete 1000) o una sola? (ambas suman igual; es cosmética).
- ¿Se **persiste** el desglose del conteo (para auditoría del cierre) o es efímero y solo produce el
  total? (Ponytail: si nadie lo consume, no lo persistas — decidir en brainstorming).
- ¿Las denominaciones van como constante en `core` o en la UI? (regla de negocio del efectivo → `core`).

---

## Formato de los entregables

- **Spec** (una sola): problema y alcance (in/out) de AMBAS features; para promociones el modelo de
  datos nuevo (entidad `Promocion` + tabla `006` + puerto/servicio), reglas de dominio con casos
  límite (promo por unidades agotándose, promo + descuento de cliente, IVA incluido, redondeo) e
  impacto en UI; para conteo, el ayudante de denominaciones y su no-obligatoriedad. Marca lo que
  queda **fuera** (YAGNI).
- **Plan** (uno solo): tasks pequeñas en orden TDD (test primero), dominio → persistencia → UI.
  Primero todas las `PROMO.x`, luego las `CONTEO.x`. Cada task con sus tests y rutas exactas, **con
  IDs prefijados** según `planes-pos`.

Antes de escribir cada archivo, muéstrame un borrador del alcance y espera mi confirmación.
Al terminar, actualiza `docs/README-pos.md` (tabla Estado actual, con filas nuevas para Promociones y
Conteo) y dame las rutas de los dos archivos.
