# pos-siesa-remake — Estado actual del código, planes y brechas

> Fecha de corte: **2026-07-05**. Rama: `master`. Suite: **395 passed** (último registro en README-pos, 2026-07-02).
> Propósito: inventario exhaustivo —apartado por apartado, vista por vista, función por función—
> de lo que existe hoy en el código local, lo planificado en specs/planes, y las brechas frente a
> los **nuevos requisitos** (`requeriminetos_new.md`): inventario en la nube con sincronización
> entre locales, CRM de clientes y proveedores, nómina/adelantos y reportes por almacén.

---

## 0. Cómo leer este documento

- ✅ **Hecho**: implementado y con pruebas.
- 🟡 **Parcial**: existe base o costura, pero incompleto para el requisito nuevo.
- ⛔ **Falta**: no existe en el código.
- 🧩 **Costura**: hay un punto de extensión diseñado (puerto, campo, id reservado) aunque sin implementar.

El sistema **hoy es 100% local, mono-caja, mono-almacén, offline**. Toda la lógica de negocio vive en
`src/core/` (sin Qt ni SQLite); los adaptadores concretos (SQLite y UI Qt) se enchufan por inyección
de dependencias vía `ContextoApp` (composition root en [src/caja/contexto.py](../src/caja/contexto.py)).

---

## 1. Resumen ejecutivo (lo hecho vs. lo nuevo)

| Área | Estado hoy | Requisito nuevo | Brecha |
|---|---|---|---|
| Ventas / caja / cobro | ✅ completo local | — | ninguna |
| Inventario (productos, stock, movimientos) | ✅ completo local (1 almacén) | Multi-almacén en la nube + traslados | ⛔ falta almacenes, traslados, sync |
| Clientes | ✅ CRUD + saldo fiado | CRM de clientes | 🟡 base sí; falta "CRM" (historial, seguimiento, contacto) |
| Proveedores | ✅ CRUD + compras + CxP | CRM de proveedores | 🟡 base sí; falta "CRM" |
| Compras / despiece | ✅ completo local | Traslados de cortes y de canal (bruto) | 🟡 despiece sí; traslado entre locales ⛔ |
| Cuentas por cobrar/pagar | ✅ saldo global + abonos/pagos | — | ninguna |
| Gastos | ✅ registro + categorías | — | ninguna |
| Nómina | ⛔ no existe | Adelantos de nómina (desde caja) | ⛔ falta módulo nómina |
| Reportes | ✅ período/factura/cajero/categoría/compras/mensual | Por almacén y total; dentro de almacén por cajero y categoría | 🟡 falta dimensión "almacén" |
| Sync multi-local | ⛔ solo diseñado (outbox) | Núcleo del nuevo pedido | ⛔ falta implementar |
| Facturación DIAN | 🧩 puerto stub | — (no pedido ahora) | pendiente |

**Conclusión de una línea:** el POS local está maduro y probado; lo que exige el pedido nuevo
(**nube + multi-almacén + sync + nómina + CRM**) es en su mayoría **arquitectura nueva** que hoy no
existe, aunque hay costuras (puertos, `sync_pdv/`, campos) donde apoyarse.

---

## 2. Arquitectura y composition root

- **Hexagonal estricta:** `core/` define entidades + servicios de dominio + puertos (`Protocol`).
  Adaptadores: `inventario/` y `ventas/` (SQLite), `caja/` (Qt), `facturacion_dian/`, `sync_pdv/`.
- **`ContextoApp`** ([contexto.py](../src/caja/contexto.py)) arma **todos** los repos y servicios sobre
  una conexión SQLite. Constante clave: `EFECTIVO_MEDIO_PAGO_ID = 1`.
  - `ContextoApp.desde_conn(conn)` — cablea 18 repos + 14 servicios.
  - `ContextoApp.crear(ruta_db)` — abre DB + migraciones + seed.
  - `usuario_actual_id` (property), `nueva_venta()` → nueva `ServicioVenta`.
- **Arranque:** `python -m caja [ruta_db]` → [__main__.py](../src/caja/__main__.py) `main()` → login → `VentanaPrincipal`.
- **Bootstrap** ([bootstrap.py](../src/caja/bootstrap.py)): `preparar_db()` (conecta + migra + seed),
  `sembrar_demo()` (8 productos, 4 categorías, 2 impuestos), `sembrar_admin()` (`admin`/`admin1234`).
  ⚠️ **Contraseña por defecto**: debe cambiarse antes de producción.

---

## 3. Modelo de datos (migraciones SQLite)

Migraciones en `scripts/migraciones/`, aplicadas por `inventario/db.py:aplicar_migraciones` (tabla
`schema_migraciones`). Dinero/cantidades viajan como **texto exacto** (`Decimal`), nunca float.

| # | Archivo | Contenido |
|---|---|---|
| 001 | `001_inventario.sql` | `categorias`, `impuestos`, `productos`, `inventario_movimientos` |
| 002 | `002_ventas.sql` | `medios_pago` (1 Efectivo, 2 Tarjeta, 3 Transferencia), `caja_sesiones`, `ventas`, `venta_lineas`, `pagos` |
| 003 | `003_consumidor_final.sql` | `clientes` + cliente Consumidor Final |
| 004 | `004_devoluciones.sql` | `devoluciones`, `devolucion_lineas` |
| 005 | `005_usuarios_descuento.sql` | `usuarios` (rol, hash), `usuario_id`/descuento en venta |
| 006 | `006_promociones.sql` | `promociones` |
| 007 | `007_caja_movimientos.sql` | `caja_movimientos` (ingresos/egresos manuales de efectivo) |
| 008 | `008_proveedores_compras.sql` | `proveedores`, `compras`, `compra_lineas`, `despieces`, `despiece_lineas` |
| 009 | `009_cuentas.sql` | medio 4 **Crédito/Fiado**, `abonos_cliente`, `pagos_proveedor` |
| 010 | `010_gastos.sql` | `categorias_gasto`, `gastos` |

> **Para el pedido nuevo faltaría** (⛔): tabla `almacenes`/`locales`, `almacen_id` en productos/stock/
> movimientos/ventas/sesiones, `traslados` (cabecera + líneas + estado de aprobación), tablas de
> **nómina** (empleados, adelantos), y la **outbox** de sincronización (hoy `sync_pdv/` está vacío).

---

## 4. Dominio (`src/core/`) — función por función

### 4.1 Entidades ([entidades.py](../src/core/entidades.py)) — dataclasses con validación en `__post_init__`
`Categoria`, `Impuesto`, `Producto`, `MovimientoInventario`, `MedioPago`, `Usuario`, `Cliente`,
`Proveedor`, `Pago`, `LineaCompra`, `Compra`, `LineaVenta`, `Venta`, `CajaSesion`, `Arqueo`,
`MovimientoCaja`, `ItemDevolucion`, `LineaDevolucion`, `Devolucion`, `LineaDespiece`, `Despiece`,
`Promocion`, `AbonoCliente`, `PagoProveedor`, `CategoriaGasto`, `Gasto`.
> Ninguna entidad tiene noción de **almacén/local** ni de **empleado de nómina** → costura a crear.

### 4.2 Puertos ([puertos.py](../src/core/puertos.py)) — 18 interfaces `Protocol`
`RepositorioCategorias, RepositorioImpuestos, RepositorioProductos, RepositorioInventario,
RepositorioClientes, RepositorioProveedores, RepositorioCompras, RepositorioDespieces,
RepositorioMediosPago, RepositorioUsuarios, RepositorioVentas, RepositorioCuentasCobrar,
RepositorioCuentasPagar, RepositorioCajaSesiones, RepositorioMovimientosCaja,
RepositorioDevoluciones, RepositorioPromociones, RepositorioCategoriasGasto, RepositorioGastos`.

### 4.3 Cálculos y reglas puras
- [calculos.py](../src/core/calculos.py): `subtotal_por_peso`, `subtotal_por_unidad`, `impuesto_incluido`,
  `aplicar_descuento`, `calcular_vuelto`, `calcular_arqueo`.
- [seguridad.py](../src/core/seguridad.py): `hash_password`, `verificar` (hash de contraseñas, stdlib).
- [permisos.py](../src/core/permisos.py): `puede(rol, accion)`. Acciones: `gestionar_usuarios`,
  `editar_productos`, `aplicar_descuento_manual`, `gestionar_promociones`. Modelo simple: **admin todo**,
  **cajero todo salvo lo restringido**. ⚠️ Roles hoy = `admin`/`cajero`; sin dimensión por almacén.
- [promociones.py](../src/core/promociones.py): `promo_vigente`, `precio_con_promo`, `consumir_unidades`.

### 4.4 Servicios de dominio (lógica de negocio)
| Servicio | Métodos públicos | Rol |
|---|---|---|
| `ServicioVenta` ([servicio_venta.py](../src/core/servicio_venta.py)) | `establecer_descuento`, `agregar`, `agregar_escaneado`, `lineas`, `total`, `total_impuestos`, `confirmar` | Carrito: aplica promo→descuento cliente, precio×peso, GS1 |
| `ServicioRegistroVenta` | `registrar` (persiste venta+pagos, descuenta stock, consume promos) | |
| `ServicioAnulacion` | `anular` (repone stock, marca anulada, sin dinero) | |
| `ServicioDevolucion` | `devolver` (parcial/total, repone stock, reembolsa, netea arqueo) + `construir_lineas_devolucion`, `entradas_de_devolucion` | |
| `ServicioCaja` ([servicio_caja.py](../src/core/servicio_caja.py)) | `abrir`, `registrar_movimiento`, `arqueo`, `cerrar` | Sesión de caja + arqueo con ingresos/egresos |
| `ServicioClientes` ([servicio_clientes.py](../src/core/servicio_clientes.py)) | `crear`, `actualizar`, `buscar`, `listar`, `consumidor_final` | |
| `ServicioProveedores` ([servicio_proveedores.py](../src/core/servicio_proveedores.py)) | `crear`, `actualizar`, `buscar`, `listar` | |
| `ServicioCompras` ([servicio_compras.py](../src/core/servicio_compras.py)) | `registrar` (alimenta stock + actualiza costo) | |
| `ServicioDespiece` ([servicio_despiece.py](../src/core/servicio_despiece.py)) | `registrar` + `prorratear_costeo_despiece` (costeo por valor de venta, fallback por peso) | Canal → cortes |
| `ServicioCuentasCobrar` ([servicio_cuentas_cobrar.py](../src/core/servicio_cuentas_cobrar.py)) | `saldo`, `pendientes`, `abonar` | Fiado (medio 4), abono→ingreso caja |
| `ServicioCuentasPagar` ([servicio_cuentas_pagar.py](../src/core/servicio_cuentas_pagar.py)) | `saldo`, `pendientes`, `pagar` | Compras a crédito, pago→egreso caja |
| `ServicioGastos` ([servicio_gastos.py](../src/core/servicio_gastos.py)) | `registrar`, `listar`, `listar_categorias`, `crear_categoria`, `actualizar_categoria` | Efectivo→egreso caja |
| `ServicioPromociones` ([servicio_promociones.py](../src/core/servicio_promociones.py)) | `crear`, `activar`, `desactivar`, `listar` | Una activa por producto |
| `ServicioUsuarios` ([servicio_usuarios.py](../src/core/servicio_usuarios.py)) | `crear`, `autenticar`, `cambiar_password`, `listar` | |
| `ServicioReportes` ([servicio_reportes.py](../src/core/servicio_reportes.py)) | `ventas`, `inventario`, `cierre`, `por_cajero`, `por_cajero_de_sesion`, `por_categoria`, `compras`, `compras_por_proveedor`, `facturas`, `mensual` | Todos los reportes |

### 4.5 Periféricos ([core/perifericos/](../src/core/perifericos/))
- `LectorPeso` (puerto) + `IngresoManual`, `BalanzaSerial` (parseo trama serial), `CodigoPesoGS1`.
- GS1 ([gs1.py](../src/core/perifericos/gs1.py)): `es_peso_variable`, `decodificar_gs1`, `FormatoGS1`,
  `ResultadoGS1`, dígito de control EAN‑13.

---

## 5. Adaptadores de persistencia (SQLite)

- **`inventario/repositorio_sqlite.py`**: `RepositorioCategoriasSQLite`, `RepositorioImpuestosSQLite`,
  `RepositorioProductosSQLite` (guardar/actualizar/por_id/por_codigo/listar),
  `RepositorioInventarioSQLite` (registrar/stock_de/movimientos_en), `RepositorioPromocionesSQLite`.
- **`ventas/repositorio_sqlite.py`** (14 repos): Clientes, MediosPago, Ventas
  (guardar, por_id, pagos_de, marcar_estado, anular, `totales_por_medio`, `ventas_en`,
  `ventas_de_sesion`, `pagos_en`, `fiado_por_cliente`), CajaSesiones, MovimientosCaja, Devoluciones,
  Usuarios, Proveedores, Compras (`credito_por_proveedor`), Despieces, CuentasCobrar
  (`abonos_por_cliente`), CuentasPagar (`pagos_por_proveedor`), CategoriasGasto, Gastos.

> Toda consulta SQL vive aquí (regla de aislamiento). Ningún repo filtra por almacén → **al añadir
> multi-local, cada query necesitará `almacen_id`**.

---

## 6. UI Qt (`src/caja/`) — vista por vista

**Shell:** `VentanaPrincipal` ([ventana_principal.py](../src/caja/ventana_principal.py)) = rail de
navegación (60px) + `QStackedWidget` + barra de estado (muestra caja abierta y efectivo).
El rail se filtra por permiso; "Usuarios" solo visible para admin. Botón inferior "Cambiar mi contraseña".

**12 entradas de rail** (orden real):

| # | Vista | Archivo | Funciones clave | Estado |
|---|---|---|---|---|
| 1 | **Venta** | [pantalla_venta.py](../src/caja/pantalla_venta.py) | grid de productos + chips categoría, campo escaneo auto-foco, GS1/EAN/PLU, selección cliente + descuento, scanner serial opcional (`_iniciar_scanner_serial`, `_leer_scanner_serial`), `_cobrar`→`DialogoCobro`, `_registrar_pagos` | ✅ |
| 2 | **Inventario** | [pantalla_inventario.py](../src/caja/pantalla_inventario.py) | listar/filtrar, crear/editar producto (`DialogoProducto`), registrar movimiento (`DialogoMovimiento`), abrir promociones (`DialogoPromociones`) | ✅ |
| 3 | **Clientes** | [pantalla_clientes.py](../src/caja/pantalla_clientes.py) | listar, seleccionar, nuevo, guardar | ✅ CRUD (no "CRM") |
| 4 | **Proveedores** | [pantalla_proveedores.py](../src/caja/pantalla_proveedores.py) | listar, seleccionar, nuevo, guardar | ✅ CRUD (no "CRM") |
| 5 | **Compras** | [pantalla_compras.py](../src/caja/pantalla_compras.py) | agregar líneas, total, confirmar (alimenta stock) | ✅ |
| 6 | **Cuentas** | [pantalla_cuentas.py](../src/caja/pantalla_cuentas.py) | 2 pestañas CxC/CxP, abonar/pagar (`DialogoAbonoPago`) | ✅ |
| 7 | **Gastos** | [pantalla_gastos.py](../src/caja/pantalla_gastos.py) | registrar, consultar por rango, administrar categorías (solo admin) | ✅ |
| 8 | **Despiece** | [pantalla_despiece.py](../src/caja/pantalla_despiece.py) | agregar cortes, previsualizar costeo, confirmar | ✅ |
| 9 | **Devoluciones** | [pantalla_devoluciones.py](../src/caja/pantalla_devoluciones.py) | buscar venta, elegir items, total, reembolso, procesar | ✅ |
| 10 | **Reportes** | [pantalla_reportes.py](../src/caja/pantalla_reportes.py) | 7 pestañas (ver §6.1) | ✅ |
| 11 | **Cierre** | [pantalla_cierre.py](../src/caja/pantalla_cierre.py) | abrir caja, movimiento manual (`DialogoMovimientoCaja`), contar efectivo (`DialogoConteoEfectivo`), arqueo, cerrar | ✅ |
| 12 | **Usuarios** (admin) | [pantalla_usuarios.py](../src/caja/pantalla_usuarios.py) | crear, refrescar/listar | ✅ |

**Diálogos** ([caja/dialogos/](../src/caja/dialogos/)): `DialogoLogin`, `DialogoCobro` (modo cobro/reembolso,
vuelto, medio Fiado si cliente identificado), `DialogoProducto`, `DialogoMovimiento`,
`DialogoMovimientoCaja`, `DialogoConteoEfectivo` (denominaciones COP), `DialogoPromociones`,
`DialogoAbonoPago`, `DialogoCambioPassword`.
**Soporte:** `tema.py` (QSS dark navy + iconos), `widgets.py` (`TarjetaProducto`, `TarjetaKpi`,
`BotonRail`, spinboxes), `formato.py` (moneda/cantidad/fecha), `conteo.py` (`DENOMINACIONES`, `total_conteo`).

### 6.1 Pestañas de Reportes (ya implementadas)
`Ventas` (KPIs + por medio de pago) · `Por categoría` · `Inventario` (entradas/salidas) ·
`Por factura` (listado + detalle) · `Por cajero` (rango o sesión) · `Compras` (por proveedor) ·
`Mensual` (ventas/compras/gastos/saldos CxC/CxP).
> ⛔ **No hay pestaña/columna "Por almacén"** — es exactamente lo que pide el requisito nuevo de reportes.

---

## 7. Trazabilidad de planes y specs (lo planificado)

Todo lo siguiente está **✅ implementado** (specs+planes en `docs/superpowers/`):

| Epic/Fase | Spec/Plan | Estado |
|---|---|---|
| E1 Venta + persistencia | `2026-06-25-e1-caja-venta` | ✅ |
| E2 Inventario | `2026-06-25-e2-inventario-e4-venta-por-peso` | ✅ |
| E3 Cierre/arqueo + descuento inventario | `2026-06-25-e3-cierre-caja-arqueo` | ✅ |
| E3b Anulación de venta | `2026-06-25-e3b-anulacion-venta` | ✅ |
| E4 Venta por peso (balanza/GS1/manual) | (con E2) | ✅ |
| E5 Clientes | `2026-06-25-e5-clientes` | ✅ |
| E6 Devoluciones con reembolso | `2026-06-25-e6-devoluciones-reembolso` | ✅ |
| E7 Reportes | `2026-06-25-e7-reportes` | ✅ |
| UI rediseño (dark navy, rail) | `2026-06-25-ui-rediseno` | ✅ |
| Escaneo automático en venta | `2026-06-26-escaneo-automatico-venta` | ✅ |
| Usuarios + cliente + descuento | `2026-06-30-usuarios-cliente-descuento` | ✅ |
| RPTFAC Reportes factura/cajero | `2026-07-01-reportes-factura-cajero` | ✅ |
| PROMO + CONTEO | `2026-07-01-promociones-conteo-caja` | ✅ |
| FASE1 Core de caja (mov. manual, por categoría, cambio pwd) | `analisis-requerimientos-cliente` | ✅ |
| FASE2 Proveedores/Compras/Despiece | `2026-07-01-fases-2-3-4-compras-cuentas-gastos` | ✅ |
| FASE3 Cuentas CxC/CxP (fiado) | idem | ✅ |
| FASE4 Gastos + reporte mensual | idem | ✅ |

**Pendientes ya reconocidos en el proyecto (pre-existentes al pedido nuevo):**
- **E8 Sync offline / outbox** → ⛔ solo diseñado; `src/sync_pdv/` está **vacío** (solo `__init__.py`).
- **DIAN facturación electrónica** → 🧩 `src/facturacion_dian/` es stub; puerto `EmisorDIAN` previsto.
- **Scanner serial de balanza** → 🟡 decodificación GS1 OK; falta validar un lector serial concreto
  que antepone `08` (ver [scanner-pesa-serial-pendiente.md](scanner-pesa-serial-pendiente.md)).

---

## 8. Requisitos NUEVOS (`requeriminetos_new.md`) — brecha detallada

El nuevo documento pide, textualmente: **inventario en la nube con sincronización entre locales**,
**traslados con permiso (cortes y canal/bruto)**, **adelantos de nómina (caja)**, y **reportes por
almacén / total / por cajero y categoría dentro del almacén**. Análisis:

### 8.1 Inventario en la nube + sincronización entre locales ⛔ (mayor esfuerzo)
- **Hoy:** SQLite local, un solo almacén implícito, sin `almacen_id` en ninguna tabla ni entidad.
- **Falta:**
  1. Concepto de **Almacén/Local** (entidad + tabla + `almacen_id` en productos-stock, movimientos,
     ventas, sesiones, compras, gastos).
  2. **Backend en la nube** (hoy no existe ningún servidor; la ruta a PostgreSQL está mencionada pero
     no implementada).
  3. **Sincronización**: `src/sync_pdv/` (patrón outbox) está diseñado pero **vacío**. Hay que definir
     transporte, resolución de conflictos, identidad por local, y qué es maestro vs. réplica.
- **Costura existente:** el aislamiento hexagonal permite añadir un `RepositorioX` remoto/sincronizable
  sin tocar `core/`. El `stock_de` se calcula desde movimientos (no un contador mutable), lo que ayuda
  a reconstruir stock por almacén.

### 8.2 Traslados con permiso (cortes y canal en bruto) ⛔
- **Hoy:** hay **movimientos de inventario** (`entrada`/`salida`) y **despiece** (canal→cortes), pero
  **no existe "traslado" entre almacenes** ni flujo de **aprobación/permiso**.
- **Falta:** entidad `Traslado` (origen, destino, líneas, estado: solicitado/aprobado/recibido),
  servicio de dominio (descuenta en origen, ingresa en destino tras aprobación), permiso nuevo
  (`ACCION_APROBAR_TRASLADO`), y su UI. Aplica tanto a **cortes** como a **producto en bruto (canal)**.
- **Costura:** `MovimientoInventario` y el modelo de despiece son la base natural para modelar traslados.

### 8.3 Adelantos de nómina (desde caja) ⛔
- **Hoy:** **no existe módulo de nómina/empleados**. Lo más cercano es `MovimientoCaja` (egresos
  manuales) y `Gasto`.
- **Falta:** entidad `Empleado` (o reuso de `Usuario`), entidad `AdelantoNomina`, servicio que registre
  el adelanto como **egreso de caja** (igual que gasto/pago), y su reporte/saldo por empleado.
- **Costura:** el patrón "todo efectivo pasa por caja" (`ServicioGastos`/`ServicioCuentasPagar` generan
  egreso vía `ServicioCaja.registrar_movimiento`) es el molde exacto para el adelanto.

### 8.4 Reportes por almacén ✅base / 🟡falta dimensión
- **Hoy:** existen reportes por período, factura, **cajero**, **categoría**, compras y mensual —pero
  **sin filtro/columna por almacén**.
- **Falta:** añadir dimensión **almacén** a `ServicioReportes` (reporte total, por almacén, y dentro de
  almacén por cajero y categoría, "como ya está"). Esto depende de §8.1 (que exista `almacen_id`).

### 8.5 CRM de clientes y proveedores 🟡
- **Hoy:** CRUD de `Cliente` y `Proveedor` + saldo de fiado/crédito. **No hay** historial de contacto,
  seguimiento, segmentación, notas, ni comunicación —lo que normalmente implica "CRM".
- **Falta (según se defina el alcance):** historial de compras por cliente, notas/interacciones,
  estado, datos de contacto ampliados, quizá recordatorios. Conviene **precisar con el negocio** qué
  entienden por "CRM" antes de dimensionar.

---

## 9. Riesgos / decisiones abiertas para la redefinición

1. **Nube y sync son el 80% del esfuerzo nuevo** y hoy no existen (ni backend ni outbox). Definir
   primero: ¿PostgreSQL central + réplicas SQLite? ¿quién es maestro del catálogo de productos?
   ¿stock por almacén autoritativo dónde?
2. **`almacen_id` es transversal**: tocará casi todas las tablas, repos y queries. Hacerlo temprano
   evita re-migraciones dolorosas.
3. **Roles por almacén**: el modelo de permisos actual (`admin`/`cajero`, global) no distingue local.
4. **"CRM" y "nómina" necesitan alcance explícito** del negocio antes de planificar (evitar YAGNI).
5. **Pendientes previos** (E8 sync, DIAN, scanner serial) conviven con lo nuevo; E8 se solapa
   directamente con el requisito de sincronización.

---

## 10. Índice rápido de archivos

- Composition root: [contexto.py](../src/caja/contexto.py) · Shell UI: [ventana_principal.py](../src/caja/ventana_principal.py)
- Dominio: [core/](../src/core/) (entidades, puertos, 15 servicios, cálculos, permisos, promociones, seguridad)
- Persistencia: [inventario/repositorio_sqlite.py](../src/inventario/repositorio_sqlite.py) · [ventas/repositorio_sqlite.py](../src/ventas/repositorio_sqlite.py)
- Migraciones: [scripts/migraciones/](../scripts/migraciones/) (001→010)
- Vacíos/stub: [sync_pdv/](../src/sync_pdv/) (⛔) · [facturacion_dian/](../src/facturacion_dian/) (🧩)
- Specs y planes: [docs/superpowers/](superpowers/) · Mapa: [README-pos.md](README-pos.md)
- Requisitos nuevos: [../requeriminetos_new.md](../requeriminetos_new.md)
