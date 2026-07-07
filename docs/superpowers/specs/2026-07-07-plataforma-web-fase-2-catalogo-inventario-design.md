# Diseño — Plataforma web Fase 2 (NUBE2): catálogo multi-local + inventario multi-bodega (bidireccional)

> Fecha: 2026-07-07 · Estado: **aprobado para planificar** · Autor: brainstorming con el dueño del negocio.
> Arranca desde: [2026-07-06-plataforma-web-multi-local-design.md](2026-07-06-plataforma-web-multi-local-design.md) (arquitectura global).
> Continúa: Fase 0+1 (NUBE0/1, ✅ implementada: push del POS → nube → dashboard).
> **Este spec refina y en dos puntos corrige el spec global** — ver §8 (Reconciliación).

## 1. Objetivo y alcance

Convertir la nube en la **fuente de verdad del catálogo** (productos, precios por local, promociones)
y montar el **inventario multi-bodega** con movimientos entre ubicaciones. El POS deja de ser el dueño
del catálogo: baja una **réplica de solo lectura** y vende contra ella (offline-first intacto), pero un
**admin** puede editar el catálogo y registrar movimientos **también desde el POS**, que suben por el
outbox ya existente.

**En alcance (NUBE2):**
- Catálogo maestro en la nube + **precio por local** (overlay), editable desde web y POS (admin).
- **Importar productos por local** (opt-in): un local "vende" un producto al tener su fila overlay.
- Editar precio/promo con selector **"aplicar a: todos / locales específicos"** (upsert masivo).
- **Promociones por local**: se **adapta a la nube** la regla que ya existe en `core`
  (`servicio_promociones`); la evaluación sigue en `core`, no hay lógica nueva.
- **Inventario multi-ubicación**: entrada / salida / ajuste / traslado (con confirmación) / conversión.
- **Sync bidireccional híbrido**: catálogo por snapshot, inventario por delta (§4).
- **Réplica RO en el POS** + edición local del admin (push por outbox).

**Fuera de alcance (fases posteriores):**
- Adelgazar el POS / quitar despiece-costeo local → **Fase 4** (global §10).
- Compras/proveedores/CxC-CxP/CRM/adelantos → **Fase 3** (global §10).
- Endurecimiento de RLS y multi-tenant real (hoy demo sin datos reales) → se anota en §11.

## 2. Decisiones tomadas (brainstorming 2026-07-07)

| Tema | Decisión |
|---|---|
| Dolor a resolver | Catálogo **y** inventario pesan por igual; van juntos en la cabeza del cliente. |
| Dirección de edición | **Bidireccional**: web y POS editan catálogo e inventario. **Solo rol `admin`.** |
| Dueño del catálogo | **Maestro de producto compartido + overlay de precio por local.** Tener overlay = ese local vende el producto. |
| Importar productos | Desde el POS, el admin agrega overlays para los productos que su local vende (opt-in). |
| Editar precio/promo | Selector "aplicar a": todos los locales o específicos → upsert masivo de overlays. |
| Conflictos catálogo | **Last-write-wins por fila** vía `actualizado_en` (autoritativo del servidor). La partición por local hace que el único choque posible sea el mismo admin editando web+POS a la vez. |
| Promociones | La **regla ya existe** en `core`; Fase 2 solo la sincroniza por local (dato), evaluación en `core`. |
| Topología de inventario | **Bodegas compartidas** (nodos centrales, sin dueño de un solo local) + locales. Se mueve entre **cualquier par**: bodega↔bodega, bodega↔local, local↔local (incl. **cross-local**). |
| Conversión | **Solo cantidades** (1 salida origen + N entradas destino, merma permitida). **Sin prorrateo de costo** (coherente con global §6). |
| Traslado | `origen`+`destino`; nace **pendiente** en destino → el destino **confirma**. |
| Mecanismo de sync | **Híbrido**: catálogo = snapshot pull (pocas filas); inventario = delta por cursor append-only. Reusa outbox/`HiloSincronizacion` + `eventos_sync`. |
| Offline-first | No negociable: el POS vende contra su espejo RO aunque no haya red. |

## 3. Modelo de datos (nube, Postgres)

### 3.1 Catálogo — maestro compartido + overlay por local

```
productos                (maestro global; edita admin en web/POS)
  id, codigo_barras, nombre, unidad ('und'|'kg'), vendido_por_peso,
  categoria_id, impuesto_id, actualizado_en
    -- impuesto_id en el maestro: el IVA es nacional, no por local

productos_local          (overlay = "este local vende este producto")
  local_id, producto_id, precio, costo, activo,
  actualizado_en          -- PK (local_id, producto_id)
    -- sin fila overlay ⇒ el local no vende ese producto (opt-in / import)
    -- precio/costo/activo son la decisión comercial de cada local

categorias               (ya existe; + actualizado_en)

promociones              (adaptación a la nube de core.Promocion)
  id, producto_id, local_id, tipo ('fijo'|'porcentaje'), valor,
  vigencia (tiempo/unidades/manual, como en core), activo, actualizado_en
    -- una activa por (producto, local); evaluación = core.servicio_promociones
```

`actualizado_en` (timestamp autoritativo del servidor, `now()` en cada upsert) es la base del LWW.

### 3.2 Inventario — ubicaciones + movimientos append-only

Se **generaliza `almacenes` → `ubicaciones`** (hoy `almacenes.local_id` es NOT NULL; se relaja para
las bodegas compartidas):

```
ubicaciones              (renombra/generaliza almacenes)
  id, nombre, tipo ('bodega'|'local'), local_id (NULL si bodega compartida), activo
    -- 'local' = punto de venta (tiene overlay de precios)
    -- 'bodega' = nodo de stock compartido, sin dueño de un solo local

movimientos_inventario   (append-only salvo el flip de estado en la confirmación)
  uuid, tipo ('entrada'|'salida'|'ajuste'|'traslado'|'conversion'),
  producto_id, cantidad (>0),
  origen_id, destino_id,          -- ubicaciones; según tipo uno puede ser NULL
  estado ('confirmado'|'pendiente'),  -- traslado nace 'pendiente' en destino
  grupo_uuid,                     -- agrupa las filas de un traslado/conversión
  lote_id, ref, fecha, actualizado_en

stock(ubicacion, producto) = Σ movimientos CONFIRMADOS (entradas − salidas), como hoy stock_de
  -- filas inmutables EXCEPTO el único cambio permitido: pendiente→confirmado al confirmar un traslado;
  -- ese flip actualiza `actualizado_en`, por eso la confirmación se propaga por el cursor (§4).
```

- **Migración de compat**: las filas de `almacenes` de Fase 1 pasan a `ubicaciones` con `tipo='local'`;
  `ventas.almacen_id` / `venta_lineas.almacen_id` / `caja_sesiones.almacen_id` siguen apuntando a
  `ubicaciones.id` (se mantiene el nombre de columna para no tocar Fase 1). Las consultas de Fase 1 que
  hacen `FROM almacenes` se migran a `ubicaciones` (o vista de compat `almacenes` = `tipo='local'`).

## 4. Sincronización bidireccional (híbrida)

Reusa el outbox del POS (`sync_pdv/`, `HiloSincronizacion`) y el log `eventos_sync`. Offline-first: el
POS vende siempre contra su espejo local; si no hay red, sigue con el último catálogo bajado.

| Dominio | nube → POS (pull) | POS → nube (push, outbox) | Conflictos |
|---|---|---|---|
| **Catálogo** (pocas filas) | **snapshot**: `GET /sync/catalogo?local_id=X` → productos ∪ overlay(activo) ∪ promos del local; el POS **reemplaza** su espejo RO | edición del admin → evento → **upsert overlay** | **LWW** por `actualizado_en` |
| **Inventario** (muchas filas) | **delta**: `GET /sync/inventario?ubicacion_id=U&desde=<cursor>` → movimientos nuevos que tocan U | movimiento del POS → evento → **insert append-only** | ninguno (inmutable) |

- **Cursor de inventario**: el POS guarda el último `actualizado_en`/uuid aplicado **por ubicación**.
  Cross-local funciona porque la nube es el hub: cada POS baja los movimientos donde su ubicación es
  `origen` o `destino` (incl. traslados entrantes que debe confirmar).
- **Idempotencia**: upsert por `uuid` en ambos (catálogo e inventario). En inventario el upsert solo
  puede crear la fila o aplicar el flip `pendiente→confirmado`; nunca reescribe cantidad/origen/destino.
- **Endpoints nuevos** (backend): `/sync/catalogo`, `/sync/inventario` (pull); las ediciones POS→nube
  entran por el `/sync/push` existente ampliando el `tipo` del evento.

## 5. Inventario multi-ubicación — operaciones

Todas son composiciones de `movimientos_inventario`; el stock por ubicación es la suma de confirmados.

1. **Entrada**: producto + cantidad + `destino` (una ubicación). Ej.: "entraron 200 kg de res".
2. **Salida / ajuste**: producto + cantidad + `origen`. (La venta ya genera su salida vía Fase 1.)
3. **Traslado**: `origen` + `destino` (cualquier par, incl. cross-local). Sale de origen ya
   (confirmado) y entra a destino como **pendiente**; el destino **confirma** (flip a `confirmado`).
   Requisito explícito del cliente (global §6.4).
4. **Conversión (despiece de gestión)**: 1 salida del origen + N entradas de destinos en la **misma
   ubicación**, **solo cantidades**, **merma permitida** (destinos ≠ origen). **Sin prorrateo de
   costo** (el costeo del POS se retira en Fase 4). Reusa los ratios de cantidad, no el `costeo`.

Permiso nuevo: `ACCION_GESTIONAR_INVENTARIO` (+ `ACCION_CONFIRMAR_TRASLADO`), rol `admin`.

## 6. Roles, UI web y POS

- **Roles**: catálogo/inventario/promos = **admin**. El JWT de Supabase ya autentica; falta un **check
  de rol** en los endpoints de gestión (nuevo).
- **Web (React, admin)**:
  - Catálogo: CRUD del maestro; gestión de overlays por local (importar/activar, fijar precio);
    editor de precio/promo con selector "aplicar a: todos / locales específicos".
  - Inventario: registrar entrada/salida/ajuste; crear traslado; **bandeja de traslados pendientes**
    para confirmar; ver **stock por ubicación**.
  - Promos: alta/edición por local (reusa la regla de `core`).
- **POS**: el **admin** importa productos y edita precio local (se empuja por outbox); registra
  movimientos de inventario. El **cajero** solo vende contra el espejo RO.

## 7. Plan de ejecución en olas (para el writing-plans)

Es el "Requisito núcleo" y el de mayor riesgo; el plan lo ejecuta en dos olas verificables:

- **Ola A — Catálogo bidireccional**: modelo maestro+overlay+promos; endpoint snapshot `/sync/catalogo`;
  espejo RO en el POS; edición admin web+POS (upsert masivo, LWW); UI web de catálogo. Verificable e2e
  (editar precio en web → POS lo baja; importar en POS → aparece en web).
- **Ola B — Inventario multi-ubicación**: `ubicaciones` + `movimientos_inventario`; endpoint delta
  `/sync/inventario`; entrada/salida/ajuste/traslado(+confirmación)/conversión; UI web de inventario y
  bandeja de pendientes; stock por ubicación. Verificable e2e (traslado cross-local → destino confirma).

## 8. Reconciliación con el spec global (2026-07-06)

Este spec **cambia** dos decisiones del diseño global y **expande** una tercera; se actualiza aquel doc:

1. **Bodegas "solo desde la web" (global §2, §6) → bidireccional.** El admin opera catálogo e inventario
   también desde el POS (push por outbox). Motivo: el cliente quiere importar/editar desde la caja.
2. **`almacenes.local_id` (global §5) → `ubicaciones` con bodegas compartidas + traslados cross-local.**
   Las bodegas son nodos centrales compartidos; se mueve entre cualquier par de ubicaciones.
3. **Se mantiene** "conversión sin costeo" (global §6.3): conversión = solo cantidades. El despiece con
   costeo del POS se retira en Fase 4, sin cambio aquí.

## 9. Pruebas

- **core** (pytest, TDD): stock por ubicación (suma de confirmados), conversión (cantidades/merma),
  LWW por `actualizado_en`, confirmación de traslado (pendiente→confirmado).
- **backend nube** (pytest, patrón `test_dashboard.py`): `/sync/catalogo` (snapshot por local),
  `/sync/inventario` (delta por cursor/ubicación), upsert masivo de overlay, confirmación de traslado;
  unitarios con conexión fake + integración gated por `TEST_DB_URL`.
- **frontend**: sin runner (igual que hoy) → verificación **manual** en navegador; no se reclama
  cobertura de test que no existe.
- **e2e real** (como Fase 1, contra Postgres real): editar precio web → POS baja; importar en POS →
  web; traslado cross-local → destino confirma.

## 10. Impacto en el POS (repo `w:\POS`)

- Espejo RO del catálogo (nueva tabla replica) + lectura de precios desde la réplica al vender.
- Edición admin del catálogo local + registro de movimientos → encolar en el outbox (`sync_pdv/`).
- Pull de catálogo (snapshot) e inventario (delta) en `HiloSincronizacion`, además del push actual.

## 11. Riesgos y decisiones abiertas

1. **Mayor riesgo del proyecto**: sync bidireccional del catálogo. Mitigado por partición por local +
   LWW por fila + inventario append-only (sin conflicto).
2. **Migración `almacenes`→`ubicaciones`**: relaja `local_id` NOT NULL y toca las consultas de Fase 1
   (`dashboard.py`); se hace con vista de compat o migración de las pocas referencias.
3. **Cursor de inventario por ubicación**: definir el almacenamiento del cursor en el POS (por ubicación).
4. **RLS / seguridad**: hoy demo sin datos reales (Supabase reporta RLS off en `schema_migraciones`);
   el endurecimiento de RLS y multi-tenant real se agenda cuando haya datos reales, no en NUBE2.
5. **Merma en conversión**: se permite destinos ≠ origen; control de merma explícito sería fase posterior.
6. **Colisión de nombres "Fase 2"**: en el README el POS ya tiene una `FASE2` (compras); esta es **NUBE2**
   (plataforma web). Nombrar siempre "NUBE2" para no confundir.
