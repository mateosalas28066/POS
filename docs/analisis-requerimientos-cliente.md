# Análisis: requerimientos del cliente vs estado actual (2026-07-01)

Comparación entre los **requerimientos del cliente** (supermercado/carnicería multi-local) y el
estado actual de **pos-siesa-remake**.

> **Reconciliado 2026-07-08:** este análisis es del 2026-07-01 y quedó anterior al track **NUBE**
> (0/1/2/3). La **Fase 5 — Multi-local** ya está entregada por ese track (sync outbox, catálogo
> bidireccional, inventario multi-bodega **con traslados**, aislamiento por evento). Las secciones
> §7 (traslados), §9 (conexión) y el roadmap Fase 5 se actualizaron abajo. Suite actual: **448
> passed** en el POS. Único reporte del cliente aún pendiente: **traslados entre locales** (la
> función existe; falta el reporte). Fuente de verdad viva: [README-pos.md](README-pos.md).

Leyenda: ✅ implementado · 🟡 parcial · ❌ no existe · 📐 diseñado (costura lista, sin implementar)

---

## 1. Comparación módulo por módulo

### 1. Caja

| Requerimiento | Estado | Detalle |
|---|---|---|
| Módulo de caja para ventas | ✅ | `PantallaVenta` + `ServicioVenta`: carrito, escaneo GS1/EAN/PLU, venta por peso, cliente, descuento, promociones, múltiples medios de pago |
| Apertura y cierre de caja | ✅ | `ServicioCaja` + `PantallaCierre`: apertura con monto inicial, cierre con arqueo y conteo de efectivo por denominaciones COP |
| Registro de movimientos de efectivo | 🟡 | El arqueo netea ventas y devoluciones, pero **no hay ingresos/egresos manuales de efectivo** (retiros a bóveda, pago de domicilios, base adicional). `DialogoMovimiento` existente es de *inventario*, no de caja |

### 2. Permisos y administración

| Requerimiento | Estado | Detalle |
|---|---|---|
| Sistema de usuarios | ✅ | `ServicioUsuarios` + `PantallaUsuarios` + `DialogoLogin`, `usuario_id` trazado en venta/cierre/devolución |
| Roles y permisos | 🟡 | Roles fijos **admin/cajero** (`core/permisos.py`). No hay permisos granulares configurables por rol |
| Administrador con acceso total | ✅ | Rol admin con gating del rail y de edición |
| Gestión de usuarios | ✅ | CRUD desde `PantallaUsuarios` (solo admin) |
| Administración de contraseñas | 🟡 | Hash seguro en `core/seguridad.py`; el admin puede resetear. **Falta cambio de contraseña autoservicio** y el default `admin/admin1234` debe cambiarse antes de producción |

### 3. Cuentas por cobrar y por pagar

| Requerimiento | Estado | Detalle |
|---|---|---|
| Clientes con saldo pendiente (fiado) | ✅ | Fase 3: venta a crédito con medio "Crédito/Fiado" (solo cliente identificado); saldo global por cliente (Σ fiado − Σ abonos) en `ServicioCuentasCobrar` |
| Consulta de cuentas pendientes + abonos | ✅ | `PantallaCuentas` pestaña "Por cobrar": clientes con saldo + abono (efectivo pasa por caja como ingreso) |
| Obligaciones con proveedores (CxP) | ✅ | Fase 3: `ServicioCuentasPagar` sobre compras a crédito (Fase 2); saldo por proveedor + pagos (efectivo→egreso); `PantallaCuentas` pestaña "Por pagar" |

### 4. Nómina

| Requerimiento | Estado |
|---|---|
| Nómina, adelantos, permisos de personal | ❌ No existe. Ver roadmap: se propone como **extra** (no es función de un POS) |

### 5. Proveedores

| Requerimiento | Estado |
|---|---|
| Maestro de proveedores, contacto, historial de compras | ✅ | Fase 2: `Proveedor` + `ServicioProveedores` + `PantallaProveedores`; historial vía `ServicioReportes.compras_por_proveedor` |

### 6. Ventas separadas por categoría (Res, Pollo, Cerdo, Fruver)

| Requerimiento | Estado | Detalle |
|---|---|---|
| Categorías de producto | ✅ | Tabla `categorias` + `categoria_id` en producto, visible en inventario y venta |
| Reporte de ventas por categoría | ✅ | Fase 1: `ServicioReportes.por_categoria` + pestaña "Por categoría" en reportes |

### 7. Traslado de mercancía entre locales

✅ **Implementado (NUBE2·OlaB, 2026-07-07).** `ubicaciones` compartidas + movimientos append-only
(entrada/salida/ajuste/**traslado**+confirmación/conversión); el admin registra un traslado
origen→destino (encola al outbox) y confirma la entrada desde la **bandeja de pendientes**; el
stock se descuenta/acredita por ubicación. `sync_pdv/` ya no está vacío: outbox + `ClienteSync`
+ push periódico. **Pendiente solo el reporte de traslados** (la operación existe; falta
`ServicioReportes.traslados()` + pestaña).

### 8. Compras a proveedores

✅ Fase 2: `Compra`/`LineaCompra` + `ServicioCompras` registran la compra (documento con
proveedor, líneas producto/cantidad/costo, contado o crédito), alimentan el stock y actualizan el
`costo` del producto. La compra "en canal" (res/cerdo entero) es una línea normal; el **despiece**
(`ServicioDespiece`) reparte el costo del canal entre los cortes **por valor de venta** (fallback a
peso), genera los movimientos de inventario y actualiza el costo de cada corte. `PantallaCompras` y
`PantallaDespiece` en el rail.

### 9. Conexión entre comercios

✅ **Implementado (NUBE0/1/2, 2026-07-06→07).** El mecanismo de sync (outbox local → `/sync/push`
idempotente, pull de catálogo `/sync/catalogo` e inventario `/sync/inventario`) conecta cada POS
con la plataforma web en la nube (`pos-plataforma-web`), compartiendo maestro de catálogo,
inventario multi-bodega y consolidados en el dashboard web. Aislamiento de escritura por evento
en NUBE3.

### 10. Reportes mensuales

✅ Fase 4: `ServicioReportes.mensual(anio, mes)` consolida ventas, compras, gastos y saldos
globales CxC/CxP del mes en un `ReporteMensual`, con pestaña "Mensual" en reportes. Los reportes
por rango (ventas, inventario, cierre, factura, cajero, categoría, compras) siguen disponibles.
Pendiente solo el de traslados (depende de multi-local, E8).

### 11. Gastos

✅ Fase 4: `CategoriaGasto` (lista fija administrable con seed: arriendo, servicios, transporte,
nómina, otros) + `Gasto` + `ServicioGastos` (gasto en efectivo → egreso de caja); `PantallaGastos`
registra, lista por período y administra categorías (solo admin).

### Matriz de reportes requeridos

| Reporte pedido | Estado |
|---|---|
| Ventas por mes | ✅ (reporte por período + consolidado mensual) |
| Ventas por categoría | ✅ (Fase 1: `por_categoria`) |
| Compras a proveedores | ✅ (Fase 2: pestaña "Compras") |
| Gastos | ✅ (Fase 4: `PantallaGastos` + mensual) |
| Cuentas por cobrar | ✅ (Fase 3: `PantallaCuentas` "Por cobrar") |
| Cuentas por pagar | ✅ (Fase 3: `PantallaCuentas` "Por pagar") |
| Inventario trasladado entre locales | 🟡 (traslados implementados en NUBE2·OlaB; falta el **reporte** dedicado) |
| Historial de compras por proveedor | ✅ (Fase 2: `compras_por_proveedor`) |

---

## 2. Lo que ya tenemos y el cliente NO pidió (valor extra ya entregado)

- **Venta por peso** (balanza serial, códigos GS1 peso/precio, ingreso manual) — crítico para carnes/fruver aunque el documento no lo liste.
- **Devoluciones con reembolso** (parcial/total, repone stock, netea arqueo) y **anulación de venta**.
- **Promociones** por producto (precio fijo o %, por tiempo/unidades/manual).
- **Conteo de efectivo por denominaciones** en el cierre.
- **Escaneo auto-enfocado** en venta.
- **Costura DIAN** (`EmisorDIAN` stub) — la facturación electrónica es obligación legal en Colombia; el cliente no la menciona pero tarde o temprano la necesitará.
- Arquitectura hexagonal + suite de 335 tests: base sólida para crecer sin romper.

---

## 3. Lo que hay por mejorar (sobre lo existente)

1. **Movimientos manuales de efectivo en caja** (ingreso/egreso con motivo) — hoy el arqueo solo cuadra ventas−devoluciones; cualquier retiro descuadra la caja.
2. **Cambio de contraseña autoservicio** y forzar cambio del default `admin1234` en el primer login.
3. **Reporte de ventas por categoría** — gap pequeño y de alto valor para el cliente (líneas Res/Pollo/Cerdo/Fruver).
4. **Permisos granulares** solo si un tercer rol lo exige (YAGNI: admin/cajero basta hoy).
5. Cerrar el backlog de `Errores.md` en curso (rama `fix/errores-acumulados`).

---

## 4. Roadmap propuesto

Criterio: primero lo que **un POS debe tener sí o sí** (vender, cuadrar caja, comprar,
controlar inventario y plata), después lo multi-local, y al final lo que no es propio de un POS.

### Núcleo — imprescindible (en orden)

**Fase 1 — Cerrar el core de caja** *(gaps pequeños, alto impacto)* ✅ **implementada** (rama `feature/fase-1-core-caja`, 2026-07-01)
- ✅ Movimientos manuales de efectivo (ingreso/egreso con motivo, afectan arqueo).
- ✅ Reporte de ventas por categoría (Res/Pollo/Cerdo/Fruver) en `ServicioReportes` + pestaña en reportes.
- ✅ Cambio de contraseña autoservicio.

**Fase 2 — Proveedores y Compras** *(habilita media matriz de reportes)* ✅ **implementada** (rama `feature/fases-2-3-4-compras-cuentas`, 2026-07-02)
- ✅ Maestro de proveedores (CRUD, contacto) — espejo del patrón de clientes.
- ✅ Registro de compras: documento con proveedor, líneas producto/cantidad/costo, soporte de
  compra "en canal" (res/cerdo) que luego se despieza con costeo por valor de venta.
- ✅ La compra alimenta stock y costo; historial de compras por proveedor.
- ✅ Reportes: compras por período y por proveedor.

**Fase 3 — Cuentas por cobrar y por pagar** *(la plata pendiente)* ✅ **implementada** (rama `feature/fases-2-3-4-compras-cuentas`, 2026-07-02)
- ✅ CxC: venta a crédito ("fiado") como medio de pago, saldo por cliente, abonos, reporte de pendientes. En carnicerías de barrio el fiado es operación diaria → prioridad alta.
- ✅ CxP: compra a crédito sobre Fase 2, pagos, reporte de obligaciones. (Saldo global por decisión del cliente, no por factura.)

**Fase 4 — Gastos y reporte mensual consolidado** ✅ **implementada** (rama `feature/fases-2-3-4-compras-cuentas`, 2026-07-02)
- ✅ Registro de gastos con clasificación (arriendo, servicios, transporte…), pagado desde caja (egreso de Fase 1) cuando es en efectivo.
- ✅ Reporte mensual consolidado: ventas + compras + gastos + CxC + CxP en una vista.

**Fase 5 — Multi-local** *(activar las costuras 📐)* ✅ **implementada vía track NUBE** (0/1/2/3, 2026-07-06→08)
- ✅ `sync_pdv` (outbox E8): identidad de local (`LOCAL_ID`/`LOCAL_TOKEN`), push periódico y pull de catálogo/inventario (NUBE0/1).
- ✅ Traslados de mercancía: documento origen→destino, descuenta/acredita stock, bandeja de pendientes + confirmación (NUBE2·OlaB). **Falta solo el reporte de traslados.**
- ✅ "Conexión entre comercios" = el mismo mecanismo de sync compartiendo maestro de catálogo, inventario multi-bodega y consolidados en el dashboard web (NUBE2), con aislamiento de escritura por evento (NUBE3).

### Vía paralela — obligación legal

- **Facturación electrónica DIAN**: pasar del stub al proveedor tecnológico cuando el negocio lo requiera. No la pide el cliente pero es ley; la costura ya existe.

### Extras — deseable, no es core de un POS

- **Nómina, adelantos y permisos de personal**: es dominio de un sistema de RRHH, no de un POS. Si se hace, versión mínima al final (registro de adelantos como egreso de caja de Fase 1 + un listado). Recomendación: gestionarlo aparte o como último módulo.
- Permisos granulares configurables por rol.
- Notas crédito/débito y anticipos (llegarán con DIAN).
- Dashboard de indicadores, exportes a Excel/PDF más allá de lo básico.

### Resumen visual

| Fase | Entrega | Requerimientos cubiertos |
|---|---|---|
| 1 | Efectivo manual + ventas por categoría + contraseñas | 1, 2, 6 |
| 2 | Proveedores + Compras (incl. canal) | 5, 8 |
| 3 | CxC (fiado) + CxP | 3 |
| 4 | Gastos + reporte mensual consolidado | 10, 11 |
| 5 ✅ | Sync multi-local + traslados (track NUBE 0/1/2/3) — falta solo el reporte de traslados | 7, 9 |
| ∥ | DIAN | obligación legal |
| Extra | Nómina y demás | 4 |
