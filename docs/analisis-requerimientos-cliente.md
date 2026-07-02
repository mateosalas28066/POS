# Análisis: requerimientos del cliente vs estado actual (2026-07-01)

Comparación entre los **requerimientos del cliente** (supermercado/carnicería multi-local) y el
estado actual de **pos-siesa-remake** (335 tests en verde, rama `fix/errores-acumulados`).

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
| Clientes con saldo pendiente (fiado) | ❌ | Existe maestro de clientes (`ServicioClientes`), pero sin concepto de crédito/saldo |
| Consulta de cuentas pendientes + abonos | ❌ | — |
| Obligaciones con proveedores (CxP) | ❌ | No existe el concepto de proveedor en el sistema |

### 4. Nómina

| Requerimiento | Estado |
|---|---|
| Nómina, adelantos, permisos de personal | ❌ No existe. Ver roadmap: se propone como **extra** (no es función de un POS) |

### 5. Proveedores

| Requerimiento | Estado |
|---|---|
| Maestro de proveedores, contacto, historial de compras | ❌ No existe |

### 6. Ventas separadas por categoría (Res, Pollo, Cerdo, Fruver)

| Requerimiento | Estado | Detalle |
|---|---|---|
| Categorías de producto | ✅ | Tabla `categorias` + `categoria_id` en producto, visible en inventario y venta |
| Reporte de ventas por categoría | ❌ | `ServicioReportes` reporta por período, factura, cajero y sesión — **no por categoría**. Es un agregado más sobre datos que ya existen (gap pequeño) |

### 7. Traslado de mercancía entre locales

❌ No existe. `sync_pdv/` está 📐 diseñado (patrón outbox, E8) pero vacío. Hoy el sistema es
mono-local por diseño (offline-first, "costuras para multi-local mañana").

### 8. Compras a proveedores

❌ No existe registro de compras. Lo más cercano: movimientos de inventario entrada/salida
(sin proveedor, sin documento de compra, sin detalle de canal res/cerdo). El producto ya tiene
campo `costo`, que serviría de base.

### 9. Conexión entre comercios

📐 Diseñado (outbox E8), no implementado. Misma costura que traslados y multi-local.

### 10. Reportes mensuales

🟡 Los reportes existentes aceptan cualquier rango de fechas (incluido un mes): ventas,
inventario/movimientos, cierre, por factura, por cajero. **Faltan** los que dependen de módulos
inexistentes: gastos, compras, CxC, CxP, traslados.

### 11. Gastos

❌ No existe registro ni clasificación de gastos.

### Matriz de reportes requeridos

| Reporte pedido | Estado |
|---|---|
| Ventas por mes | ✅ (reporte por período) |
| Ventas por categoría | ❌ (datos listos, falta el agregado) |
| Compras a proveedores | ❌ (depende de módulo Compras) |
| Gastos | ❌ (depende de módulo Gastos) |
| Cuentas por cobrar | ❌ (depende de CxC) |
| Cuentas por pagar | ❌ (depende de CxP) |
| Inventario trasladado entre locales | ❌ (depende de Traslados) |
| Historial de compras por proveedor | ❌ (depende de Proveedores/Compras) |

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

**Fase 2 — Proveedores y Compras** *(habilita media matriz de reportes)*
- Maestro de proveedores (CRUD, contacto) — espejo del patrón de clientes.
- Registro de compras: documento con proveedor, líneas producto/cantidad/costo, soporte de
  compra "en canal" (res/cerdo) que luego se despieza vía movimientos de inventario.
- La compra alimenta stock y costo; historial de compras por proveedor.
- Reportes: compras por período y por proveedor.

**Fase 3 — Cuentas por cobrar y por pagar** *(la plata pendiente)*
- CxC: venta a crédito ("fiado") como medio de pago, saldo por cliente, abonos, reporte de pendientes. En carnicerías de barrio el fiado es operación diaria → prioridad alta.
- CxP: compra a crédito sobre Fase 2, pagos parciales, reporte de obligaciones.

**Fase 4 — Gastos y reporte mensual consolidado**
- Registro de gastos con clasificación (arriendo, servicios, transporte…), opcionalmente pagado desde caja (egreso de Fase 1).
- Reporte mensual consolidado: ventas + compras + gastos + CxC + CxP en una vista/export.

**Fase 5 — Multi-local** *(activar las costuras 📐)*
- Implementar `sync_pdv` (outbox E8): identidad de local, transmisión/recepción.
- Traslados de mercancía: documento origen→destino, descuenta/acredita stock, historial y reporte.
- "Conexión entre comercios" = este mismo mecanismo de sync compartiendo maestros/consolidados.

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
| 5 | Sync multi-local + traslados | 7, 9 |
| ∥ | DIAN | obligación legal |
| Extra | Nómina y demás | 4 |
