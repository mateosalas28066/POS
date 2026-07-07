# pos-siesa-remake — Mapa del proyecto

POS autónomo (Python + PySide6 + SQLite) que reemplaza el POS de Siesa sobre Linux Debian,
para un negocio de **carnes y frutas**. Offline-first, una caja hoy; costuras para multi-local
y facturación electrónica DIAN mañana.

- **Spec maestro:** [superpowers/specs/2026-06-25-pos-siesa-remake-design.md](superpowers/specs/2026-06-25-pos-siesa-remake-design.md)
- **Guía para Claude:** [../CLAUDE.md](../CLAUDE.md)

## Estructura del workspace

| Carpeta | Rol | Relación con Siesa POS/PDV |
|---|---|---|
| `src/core/` | Dominio puro: entidades, servicios (ServicioVenta, ServicioCaja, ServicioClientes, ServicioUsuarios, ServicioReportes), reglas (impuestos, precio×peso, arqueo, descuento, permisos por rol, hash de contraseñas), puertos, armado de factura DIAN. Sin Qt ni SQLite. | Lógica de negocio que en Siesa está repartida entre PDV y ERP |
| `src/core/perifericos/` | Puerto `LectorPeso` + adaptadores `BalanzaSerial`, `CodigoPesoGS1`, `IngresoManual`. | Balanzas / códigos de peso del PDV (fruver y carne) |
| `src/inventario/` | Productos, stock, movimientos (adaptadores SQLite). | Módulo Inventarios de Siesa |
| `src/ventas/` | Persistencia no-UI del ciclo venta/caja: clientes, medios de pago, ventas, pagos, sesiones de caja (adaptadores SQLite). | Tablas transaccionales del PDV |
| `src/caja/` | UI Qt: login, venta (cliente + descuento), clientes, cobro, devoluciones, cierre/arqueo, reportes (período/factura/cajero), usuarios/roles. | Capa de caja/PDV (terminal) de Siesa |
| `src/facturacion_dian/` | Puerto `EmisorDIAN` + adaptadores (stub hoy, proveedor después). | Capa de facturación electrónica / e-Invoicing |
| `src/sync_pdv/` | Outbox local (`eventos_sync`) + `ClienteSync`/`TransporteHTTP`: push de ventas (idempotente por uuid) y **pull de catálogo** a la réplica RO (`replica.py`: `RepositorioReplicaSQLite` + decorator de precio + novedades de precio de la nube). | Transmisión/recepción PDV almacén de Siesa |
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
| RPTFAC | Reportes por factura (listado + detalle) y por cajero (rango y sesión) sobre `ServicioReportes` (`facturas`, `por_cajero`, `por_cajero_de_sesion`) + pestañas "Por factura" y "Por cajero" en `PantallaReportes` ([spec](superpowers/specs/2026-07-01-reportes-factura-cajero-design.md) · [plan](superpowers/plans/2026-07-01-reportes-factura-cajero.md)) | ✅ implementado |
| PROMO | Promociones por producto (precio fijo o %, duración por tiempo/unidades/manual): dominio `Promocion` + reglas `promo_vigente/precio_con_promo/consumir_unidades`, `ServicioPromociones` (una activa por producto), `RepositorioPromocionesSQLite` (migración 006), `ServicioVenta` aplica la promo antes del descuento del cliente y consume unidades al registrar, `DialogoPromociones` desde inventario y marca visual en la venta ([spec](superpowers/specs/2026-07-01-promociones-conteo-caja-design.md) · [plan](superpowers/plans/2026-07-01-promociones-conteo-caja.md)) | ✅ implementado |
| CONTEO | Conteo de efectivo por denominaciones (COP) en el cierre: `caja/conteo.py` (`DENOMINACIONES` + `total_conteo`), `DialogoConteoEfectivo` y botón "Contar efectivo" que rellena el monto contado (ayuda opcional, no bloquea el cierre) ([spec](superpowers/specs/2026-07-01-promociones-conteo-caja-design.md) · [plan](superpowers/plans/2026-07-01-promociones-conteo-caja.md)) | ✅ implementado |
| FASE1 | Core de caja (roadmap cliente): movimientos manuales de efectivo (`MovimientoCaja`, migración 007, `ServicioCaja.registrar_movimiento`, arqueo con otros ingresos/egresos, `DialogoMovimientoCaja` en cierre), reporte de ventas por categoría (`ServicioReportes.por_categoria` + pestaña "Por categoría"), cambio de contraseña autoservicio (`cambiar_password` + `DialogoCambioPassword` desde el rail) ([análisis](analisis-requerimientos-cliente.md)) | ✅ implementado |
| FASE2 | Proveedores y Compras: maestro `Proveedor` + `ServicioProveedores` + `PantallaProveedores`; `Compra`/`LineaCompra` + `ServicioCompras` (alimenta stock y actualiza costo); despiece con costeo por valor de venta (`ServicioDespiece` + `prorratear_costeo_despiece`, prorrateo del costo del canal entre cortes, fallback por peso); migración 008; `PantallaCompras`/`PantallaDespiece` + pestaña "Compras" en reportes (`ServicioReportes.compras`/`compras_por_proveedor`) ([spec+plan](superpowers/specs/2026-07-01-fases-2-3-4-compras-cuentas-gastos-design.md)) | ✅ implementado |
| FASE3 | Cuentas por cobrar (fiado) y por pagar: saldo global por cliente/proveedor (Σ deuda − Σ abonos/pagos); `ServicioCuentasCobrar` (`AbonoCliente`, medio 4 Crédito/Fiado) y `ServicioCuentasPagar` (`PagoProveedor`, sobre compras a crédito); todo efectivo pasa por caja (abono→ingreso, pago→egreso); migración 009; `PantallaCuentas` (2 pestañas) + `DialogoAbonoPago` + medio Fiado en el cobro solo para cliente identificado ([spec+plan](superpowers/specs/2026-07-01-fases-2-3-4-compras-cuentas-gastos-design.md)) | ✅ implementado |
| FASE4 | Gastos y reporte mensual consolidado: `CategoriaGasto` (lista fija administrable con seed) + `Gasto` + `ServicioGastos` (efectivo→egreso de caja); migración 010; `PantallaGastos` (registrar + listar + administrar categorías solo admin); reporte mensual `ServicioReportes.mensual` (ventas/compras/gastos/saldos CxC/CxP) + pestaña "Mensual" ([spec+plan](superpowers/specs/2026-07-01-fases-2-3-4-compras-cuentas-gastos-design.md)) | ✅ implementado |
| NUBE0/1 | Plataforma web multi-local Fase 0+1: `core` empaquetado como `pos-core` (pip installable, import `core`); outbox local (`eventos_sync`, migración 011, `RepositorioOutboxSQLite` + `serializar_venta`), `ServicioRegistroVentaConOutbox` (serializador inyectado) y `ClienteSync`/`TransporteHTTP`/`HiloSincronizacion` en `sync_pdv/`; cableado opcional en `ContextoApp` por `LOCAL_ID`/`ALMACEN_ID` (encola en outbox) y adicionalmente `SYNC_URL`/`LOCAL_TOKEN` (arranca el push periódico en background, intervalo `SYNC_INTERVALO_SEGUNDOS`, default 30s; requiere `ruta_db` real, no `:memory:`). Repo hermano `w:\pos-plataforma-web`: backend FastAPI + Supabase Postgres (`almacen_id` transversal, `/sync/push` idempotente por uuid, `/dashboard/*` reusando `ServicioReportes`, CORS habilitado, auth local-token + JWT JWKS con tolerancia a desfase de reloj) y frontend React con login Supabase y dashboard multi-bodega ([spec](superpowers/specs/2026-07-06-plataforma-web-multi-local-design.md) · [plan](superpowers/plans/2026-07-06-plataforma-web-fase-0-1.md)) | ✅ implementado (Fase 0+1) |
| NUBE2·OlaA | Catálogo bidireccional (implementado): maestro en la nube (`productos`+overlay `productos_local`+`promociones`, migración 005) con gestión web admin (`/catalogo/*`, allowlist `ADMIN_EMAILS`), pull snapshot por local (`GET /sync/catalogo`), materialización LWW de ediciones del POS en `/sync/push`, réplica RO en el POS (migración 012, `catalogo_replica`) que alimenta precio de venta **e inventario** vía decorator, edición local→outbox, y **sync híbrido**: el precio de la nube se aplica solo y se avisa de forma no bloqueante (`novedades_catalogo` migración 014 + aviso en `VentanaPrincipal`). UI web con pestaña Catálogo + editor de overlay "aplicar a" ([spec](superpowers/specs/2026-07-07-plataforma-web-fase-2-catalogo-inventario-design.md) · [plan](superpowers/plans/2026-07-07-plataforma-web-fase-2-catalogo-inventario.md)) | ✅ implementado (Ola A) |
| NUBE2·OlaB | Inventario multi-bodega (implementado): `ubicaciones` compartidas (migración 006 nube + 013 POS) con movimientos append-only entrada/salida/ajuste/traslado+confirmación/conversión; backend `/inventario/*` (admin) + delta por cursor (`GET /sync/inventario`) + materialización en `/sync/push` (append + único flip pendiente→confirmado por `ON CONFLICT(uuid)`); POS `RepositorioMovimientosUbicacionSQLite`, pull delta en `ClienteSync`, admin registra movimientos→outbox (permisos `ACCION_GESTIONAR_INVENTARIO`/`ACCION_CONFIRMAR_TRASLADO`, UI mínima Traslado+Pendientes); UI web con pestaña **Inventario** (operaciones, bandeja de pendientes, stock por ubicación) sobre `GET /inventario/ubicaciones`. Migración 006 aplicada a la **BD real**. Verificado por suites de integración contra Postgres real (backend 55) + POS 475; click-through en navegador + dos POS = verificación en vivo del usuario | ✅ implementado (Ola B) |
| E8 | Sync offline/outbox (push de ventas ✅ vía NUBE0/1; pull de catálogo y conflictos = Fase 2/NUBE2, 📋 specado) | 🟡 parcial |
| DIAN | Facturación electrónica (stub → proveedor) | pendiente |

Suite: **448 passed** (`python -m pytest -q`, 2026-07-07). Backend nube: **40 passed** con `TEST_DB_URL` (`w:\pos-plataforma-web\backend`).

**Despliegue de la nube (aprendizaje NUBE2, obligatorio para cada fase):** las migraciones de
`w:\pos-plataforma-web\backend\migraciones` deben aplicarse **también a la BD real de Supabase**
(`SUPABASE_DB_URL` → `/postgres`), no solo a la BD de tests `pos_test`. La suite verde NO garantiza
que producción esté migrada. Correr como paso de deploy:
`python -c "import psycopg,os; from app.migraciones_runner import aplicar_migraciones; aplicar_migraciones(psycopg.connect(os.environ['SUPABASE_DB_URL']))"`.
El catálogo del POS y la nube deben compartir ids de `productos` (bootstrap: sembrar el maestro
nube desde el catálogo local del POS antes de crear overlays).

**Seguridad:** `caja.bootstrap.sembrar_admin` siembra un usuario `admin`/`admin1234` si no
hay usuarios en la base. Esa contraseña por defecto debe cambiarse antes de desplegar en
producción (el cambio de contraseña autoservicio queda fuera de alcance de este plan).
