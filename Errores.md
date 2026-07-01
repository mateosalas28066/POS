# Auditoría de errores — pos-siesa-remake

> Revisión del **2026-07-01**. Acumulado de fallos funcionales, visuales y de
> comodidad/eficiencia detectados en uso + inspección de código. Cada ítem lleva
> ubicación (`archivo:línea`), comportamiento esperado y prioridad.
>
> Origen: **[R]** = reportado por el usuario · **[A]** = hallado en auditoría.
> Prioridad: 🔴 alta · 🟡 media · 🟢 baja.
>
> **Alcance de esta ronda de fixes:** todos los ítems **excepto F6** (marcado
> ⛔ FUERA DE ALCANCE). Al resolver cada ítem, márcalo con ✅ en su encabezado.

---

## 1. Funcionales

### F1 · Conteo de efectivo no se reinicia entre sesiones de caja ✅ 🔴 [R]
Al **cerrar** y **abrir** caja, el "Efectivo contado" conserva el valor anterior;
solo cambia si se vuelve a entrar a "Contar efectivo".
- **Dónde:** [pantalla_cierre.py:33-34](src/caja/pantalla_cierre.py#L33) — `_monto_contado`
  es un widget persistente que nunca vuelve a 0. Ni `_abrir` ([:109](src/caja/pantalla_cierre.py#L109))
  ni `_cerrar` ([:128](src/caja/pantalla_cierre.py#L128)) lo resetean.
- **Esperado:** al cerrar caja → 0; al abrir caja nueva → 0.

### F2 · El desglose de denominaciones no persiste con la caja abierta ✅ 🔴 [R]
Si cuento el efectivo, cierro el diálogo y lo vuelvo a abrir (misma caja abierta),
los billetes/monedas aparecen en 0 — se pierde el conteo, imposible verificar o corregir.
- **Dónde:** [dialogo_conteo.py:16-26](src/caja/dialogos/dialogo_conteo.py#L16) — el diálogo
  crea `QSpinBox` nuevos en cada `__init__`; el desglose no se guarda en ningún lado.
- **Esperado:** mientras la caja siga abierta, reabrir "Contar efectivo" debe mostrar el
  desglose previo (denominación por denominación) para revisar/ajustar. Al cerrar caja se descarta.
- **Nota:** el total contado se persiste al cierre (`monto_contado`), pero el **desglose** no
  existe en el modelo. Decidir si se guarda solo en memoria (mientras la sesión esté abierta)
  o también en BD para auditoría posterior.

### F3 · Reporte "Por cajero" mezcla cajero y método de pago sin distinción ✅ 🔴 [R]
En la pestaña "Por cajero" la columna **Cajero** contiene tanto el nombre del cajero
(admin, "Sin cajero") como los métodos de pago (Efectivo, Tarjeta) indentados con espacios,
en la misma tabla. Es confuso (ver captura).
- **Dónde:** [pantalla_reportes.py:186-203](src/caja/pantalla_reportes.py#L179) — las sub-filas
  de método de pago se insertan con `"    " + nombre` en la columna 0 y el monto en la columna 4.
- **Esperado:** separación clara. Opciones: (a) `QTreeWidget` cajero → métodos anidados;
  (b) columna dedicada "Método de pago"; (c) sub-tabla aparte al seleccionar un cajero.

### F4 · Promociones: fecha por defecto en el año 2000 ✅ 🔴 [R]
"Desde" y "Hasta" arrancan en `1/01/2000 12:00 a. m.`
- **Dónde:** [dialogo_promociones.py:33-34](src/caja/dialogos/dialogo_promociones.py#L33) —
  `QDateTimeEdit()` sin valor inicial usa la fecha mínima de Qt.
- **Esperado:** "Desde" = ahora; "Hasta" = ahora + 1 hora (default).

### F5 · Promociones: Desde/Hasta/Unidades siempre visibles ✅ 🟡 [R]
Los tres campos se muestran aunque no apliquen al tipo de duración elegido.
- **Dónde:** [dialogo_promociones.py:44-46](src/caja/dialogos/dialogo_promociones.py#L44) —
  el formulario los agrega fijos; la lógica de `promocion()` ya los ignora según el tipo
  ([:73-76](src/caja/dialogos/dialogo_promociones.py#L73)) pero la UI no los oculta.
- **Esperado:** `tiempo` → mostrar Desde/Hasta; `unidades` → mostrar Unidades; `manual` → ninguno.
  Conectar `_tipo_duracion.currentTextChanged` para alternar visibilidad.

### F6 · Promociones: sin validación de rango de fechas ni tope de % 🟡 [A] — ⛔ FUERA DE ALCANCE
> Excluido de esta ronda de fixes por decisión del usuario. Se deja documentado.
- No valida que "Hasta" ≥ "Desde".
- En modo `porcentaje`, `_valor` permite hasta 99.999.999 ([dialogo_promociones.py:30](src/caja/dialogos/dialogo_promociones.py#L30));
  un % > 100 produciría precio negativo.
- **Esperado:** validar `hasta > desde`; limitar el valor a ≤ 100 cuando el tipo es `porcentaje`.

### F7 · Desactivar promoción indexa por número de fila ✅ 🟢 [A]
`_desactivar` usa `promos[fila]` asumiendo que el orden de la tabla == orden de `listar()`.
Frágil si cambia el orden o se agregan filtros.
- **Dónde:** [dialogo_promociones.py:93-98](src/caja/dialogos/dialogo_promociones.py#L93).
- **Esperado:** guardar el `id` de la promo en la celda (`setData(Qt.UserRole, promo.id)`) y leerlo.

---

## 2. Visuales

### V1 · Tarjetas de producto crecen cuando hay pocos artículos ✅ 🔴 [R]
Con pocos productos las cards se estiran enormes (ver captura). Se quieren **5 columnas**,
tamaño de card fijo aunque falten artículos para llenar la grilla.
- **Dónde:** [pantalla_venta.py:22](src/caja/pantalla_venta.py#L22) `_COLS_GRID = 4` (se pide 5);
  [pantalla_venta.py:160-169](src/caja/pantalla_venta.py#L160) el `QGridLayout` estira las cards;
  [widgets.py:12](src/caja/widgets.py#L12) `TarjetaProducto` no fija tamaño;
  [tema.qss:12](src/caja/tema.qss#L12) `#card` sin `min/max-width/height`.
- **Esperado:** 5 por fila, `setFixedSize` (o min+max) en la card, y que la grilla no las
  redimensione (alineación arriba-izquierda con `addStretch`/relleno). Objetivo: 5×2 visibles.

### V2 · Al filtrar, la grilla deja huecos irregulares ✅ 🟡 [A]
`_aplicar_filtro` solo hace `setVisible(False)` sobre las cards; no reordena la grilla, así
que quedan celdas vacías dispersas.
- **Dónde:** [pantalla_venta.py:180-187](src/caja/pantalla_venta.py#L180).
- **Esperado:** recolocar las cards visibles de forma contigua (reconstruir la grilla filtrada).

### V3 · Diálogo de promociones pequeño y con orden invertido ✅ 🟡 [R]
El diálogo abre pequeño (poco legible) y muestra primero el formulario de crear y al final la tabla.
- **Dónde:** [dialogo_promociones.py:59-63](src/caja/dialogos/dialogo_promociones.py#L59).
- **Esperado:** `setMinimumSize` mayor por defecto; **primero** la tabla de promociones con
  botones "Agregar"/"Desactivar", y desde "Agregar" desplegar el formulario (diálogo o panel).

### V4 · Tarjeta de producto sin indicación de stock ni promo activa ✅ 🟢 [A]
El catálogo no muestra si un producto está agotado ni si tiene promoción vigente.
- **Dónde:** [widgets.py:12-33](src/caja/widgets.py#L12).
- **Esperado:** badge/borde de "promo" y estado de stock agotado (deshabilitar o marcar).

---

## 3. Comodidad / Eficiencia (formato y UX de entrada)

### C1 · El "0" por defecto no se borra al escribir ✅ 🔴 [R]
En todos los campos numéricos (`QSpinBox`/`QDoubleSpinBox`) el 0 inicial permanece y hay
que borrarlo a mano; molesto y propenso a errores (ej. "05000").
- **Dónde:** transversal — 8 archivos usan spinboxes: `dialogo_cobro`, `dialogo_conteo`,
  `dialogo_movimiento`, `dialogo_producto`, `dialogo_promociones`, `pantalla_cierre`,
  `pantalla_devoluciones`, `pantalla_venta`.
- **Esperado:** al enfocar (o al primer teclazo) seleccionar/limpiar el 0 automáticamente.
  Solución central: subclase `SpinBoxPos`/`SpinMoneda` con `focusInEvent → selectAll()`
  (o `QLineEdit` con validador). Aplicar en un solo lugar y reemplazar usos.

### C2 · Campos de dinero sin separador de miles al escribir ✅ 🟡 [R]
Al teclear montos grandes no hay separador (ej. `99999999`), ilegible. En **reportes** el
display sí usa `formato_moneda` (bien), pero la **entrada** no.
- **Dónde:** los `QDoubleSpinBox` de dinero usan `setDecimals(0)` sin `setGroupSeparatorShown(True)`
  (p.ej. [pantalla_cierre.py:31-34](src/caja/pantalla_cierre.py#L31),
  [dialogo_promociones.py:30](src/caja/dialogos/dialogo_promociones.py#L30)).
- **Esperado:** `setGroupSeparatorShown(True)` en los spin de dinero (idealmente en la misma
  subclase `SpinMoneda` de C1), y prefijo `$`. Mantener `formato_moneda` para todo display.

### C3 · Cantidades en reportes sin formato de miles ✅ 🟢 [A]
Columnas de conteo usan `str(...)` directo (entradas/salidas/# ventas), inconsistente con el
resto que sí formatea.
- **Dónde:** [pantalla_reportes.py:129-131](src/caja/pantalla_reportes.py#L129),
  [pantalla_reportes.py:192](src/caja/pantalla_reportes.py#L192).
- **Esperado:** usar `formato_cantidad`/separador de miles para números grandes.

### C4 · Espacio colgante en cantidades sin unidad (carrito) ✅ 🟢 [A]
`formato_cantidad(v, "")` devuelve `"3 "` (espacio final) cuando la unidad es vacía.
- **Dónde:** [formato.py:16-22](src/caja/formato.py#L16), usado en
  [pantalla_venta.py:231](src/caja/pantalla_venta.py#L231).
- **Esperado:** no agregar el espacio/unidad cuando `unidad == ""`.

---

## 4. Cómo verificar (pruebas manuales)

Levantar la app: `python -m caja` · admin por defecto `admin` / `admin1234`.

- **F1/F2:** abrir caja → Contar efectivo (ingresar denominaciones) → cerrar diálogo →
  reabrir (debe conservar desglose) → cerrar caja → abrir caja de nuevo (debe estar en 0).
- **F3:** Reportes → "Por cajero" → verificar que cajero y método de pago se distinguen.
- **F4/F5:** Inventario → Promociones → tipo `tiempo` (fechas = hoy / hoy+1h) → cambiar a
  `manual`/`unidades` (deben ocultarse Desde/Hasta y mostrarse Unidades solo en `unidades`).
- **V1:** Venta con pocos productos → cards de tamaño fijo, 5 por fila.
- **C1/C2:** cualquier campo numérico → al escribir se borra el 0; montos con separador de miles.

---

## 5. Extras / roadmap (no son bugs — funcionalidad futura)

- Salida y entrada por locales (multi-local / traslados).
- Domicilios.
- Limpieza de cortes.
- Reporte de daños / averías.
