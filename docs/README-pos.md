# pos-siesa-remake — Mapa del proyecto

POS autónomo (Python + PySide6 + SQLite) que reemplaza el POS de Siesa sobre Linux Debian,
para un negocio de **carnes y frutas**. Offline-first, una caja hoy; costuras para multi-local
y facturación electrónica DIAN mañana.

- **Spec maestro:** [superpowers/specs/2026-06-25-pos-siesa-remake-design.md](superpowers/specs/2026-06-25-pos-siesa-remake-design.md)
- **Guía para Claude:** [../CLAUDE.md](../CLAUDE.md)

## Estructura del workspace

| Carpeta | Rol | Relación con Siesa POS/PDV |
|---|---|---|
| `src/core/` | Dominio puro: entidades, servicios (ServicioVenta, ServicioCaja, ServicioClientes), reglas (impuestos, precio×peso, arqueo), puertos, armado de factura DIAN. Sin Qt ni SQLite. | Lógica de negocio que en Siesa está repartida entre PDV y ERP |
| `src/core/perifericos/` | Puerto `LectorPeso` + adaptadores `BalanzaSerial`, `CodigoPesoGS1`, `IngresoManual`. | Balanzas / códigos de peso del PDV (fruver y carne) |
| `src/inventario/` | Productos, stock, movimientos (adaptadores SQLite). | Módulo Inventarios de Siesa |
| `src/ventas/` | Persistencia no-UI del ciclo venta/caja: clientes, medios de pago, ventas, pagos, sesiones de caja (adaptadores SQLite). | Tablas transaccionales del PDV |
| `src/caja/` | UI Qt: venta, clientes, cobro, devoluciones, cierre/arqueo. | Capa de caja/PDV (terminal) de Siesa |
| `src/facturacion_dian/` | Puerto `EmisorDIAN` + adaptadores (stub hoy, proveedor después). | Capa de facturación electrónica / e-Invoicing |
| `src/sync_pdv/` | Patrón outbox para multi-local (diseñado, no implementado a fondo). | Transmisión/recepción PDV almacén de Siesa |
| `scripts/` | Migraciones, seed de datos, utilidades CLI. | — |
| `tests/` | Pruebas por módulo (pytest), estructura espejo de `src/`. | — |
| `docs/` | Documentación funcional y técnica (este índice). | — |

## Documentación funcional y técnica

- [pos-siesa-funcional.md](pos-siesa-funcional.md) — funcionalidades mínimas que el POS debe cumplir (derivadas de Siesa).
- [pos-open-source-referencias.md](pos-open-source-referencias.md) — qué tomar de OSPOS, uniCenta y Chromis.
- [ponytail.md](ponytail.md) — filosofía de mínimo código necesario.
- [ponytail-instalar.md](ponytail-instalar.md) — instrucciones por si Ponytail existe como plugin en tu marketplace.
- [ecc-plan.md](ecc-plan.md) — cómo se mapean skills y subagentes (ECC con lo nativo de Claude Code).
- [plan-inicial-pos.md](plan-inicial-pos.md) — epics y primeras tareas.

## Estado actual

| Epic | Descripción | Estado |
|---|---|---|
| E1 | ServicioVenta + persistencia ventas (prototipo de pantalla de venta) | ✅ implementado |
| E2 | Inventario (productos, stock, movimientos) | ✅ implementado |
| E3 | Cierre de caja / arqueo + descuento de inventario | ✅ implementado |
| E3.b | Anulación de venta (sin dinero): repone stock, marca anulada | ✅ implementado |
| E4 | Venta por peso (balanza, GS1, manual) | ✅ implementado |
| E5 | Clientes (maestro + ServicioClientes + pantalla CRUD Qt) | ✅ implementado |
| E6 | Devoluciones con reembolso: parcial/total, repone stock, reembolsa y netea el arqueo (dominio + `PantallaDevoluciones` Qt) | ✅ implementado |
| E7 | Reportes: ventas por período, cierre/arqueo de sesión, inventario/movimientos (dominio + `PantallaReportes` Qt) | ✅ implementado |
| UI | Rediseño de caja: tema dark navy, 6 pantallas Qt, `VentanaPrincipal` con rail, `ContextoApp` como composition root (`python -m caja`) | ✅ implementado |
| Escaneo | Campo de escaneo auto-enfocado en venta: decodifica GS1 de peso/precio variable o EAN/PLU y agrega al carrito | ✅ implementado |
| Usuarios+Cliente | Login + roles admin/cajero (`DialogoLogin`, `PantallaUsuarios`, gating del rail y edición por permisos), `usuario_id` trazado en venta/cierre/devolución, selección de cliente y descuento porcentual en la venta ([spec](superpowers/specs/2026-06-30-usuarios-cliente-descuento-design.md) · [plan](superpowers/plans/2026-06-30-usuarios-cliente-descuento.md)) | ✅ implementado |
| RPTFAC | Reportes por factura (listado + detalle) y por cajero (rango y sesión) sobre `ServicioReportes` + 2 pestañas nuevas en `PantallaReportes` ([spec](superpowers/specs/2026-07-01-reportes-factura-cajero-design.md) · [plan](superpowers/plans/2026-07-01-reportes-factura-cajero.md)) | 📝 spec+plan (sin implementar) |
| E8 | Sync offline/outbox | pendiente |
| DIAN | Facturación electrónica (stub → proveedor) | pendiente |

Suite: **259 passed** (`python -m pytest -q`, 2026-06-30).

**Seguridad:** `caja.bootstrap.sembrar_admin` siembra un usuario `admin`/`admin1234` si no
hay usuarios en la base. Esa contraseña por defecto debe cambiarse antes de desplegar en
producción (el cambio de contraseña autoservicio queda fuera de alcance de este plan).
