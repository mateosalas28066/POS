# Separación POS ↔ Web y limpieza de UI/UX — Diseño

> Fecha: 2026-07-08 · Estado: aprobado (brainstorming) · Alcance: `pos-siesa-remake` (POS Qt) + `pos-plataforma-web` (FastAPI + React)

## Problema

El POS acumuló toda la administración del negocio: 12 vistas en el rail
(Venta, Inventario, Clientes, Proveedores, Compras, Cuentas, Gastos, Despiece,
Devoluciones, Reportes, Cierre, Usuarios) más un botón suelto de "Cambiar mi
contraseña". La plataforma web, en cambio, quedó delgada (Login, Dashboard,
Inventario, Catálogo). El desbalance es al revés de lo que deberían ser: el POS
debe **operar el mostrador** y la web debe **administrar y analizar**.

Además, la interacción es pobre: el rail reusa 3 iconos para 12 destinos, ninguna
vista muestra su título, y hay pantallas que existen solo para una acción
("Cambiar mi contraseña").

## Principio rector

- **POS = operar el local:** vender, cobrar, cerrar caja, consultar/ajustar
  inventario, traslados, y devolución en mostrador.
- **Web = administrar y analizar:** maestros de terceros, compras, gastos,
  cuentas, despiece/costeo, catálogo, reportes completos, usuarios/roles.
- **La capacidad no se pierde:** lo que sale del POS aparece en la web.
- **Reusar `core`, no reescribir:** `core` está empaquetado como `pos-core`
  (pip-installable) y el backend ya reutiliza `ServicioReportes`. Todo lo que se
  mueve a la web se expone vía **endpoints FastAPI respaldados por los mismos
  servicios de dominio** (`ServicioClientes`, `ServicioProveedores`,
  `ServicioCompras`, `ServicioGastos`, `ServicioCuentasCobrar/Pagar`,
  `ServicioDespiece`, `ServicioUsuarios`, `ServicioReportes`), cambiando solo el
  repositorio (SQLite → Postgres). El React solo pinta; las reglas de negocio
  nunca se duplican en TypeScript.

## Mapa destino de vistas

### POS — de 12 vistas a 4 + perfil

| Vista POS | Destino | Nota |
|---|---|---|
| **Venta** | Se queda (núcleo) | Absorbe **cobro** y **devolución** (buscar factura → devolver líneas → reembolso). Conserva selector y **alta rápida** de cliente en el flujo. |
| **Inventario** | Se queda (operativo) | Consultar/ajustar stock, movimientos, traslados y bandeja de pendientes. La edición del **maestro de catálogo/precios** es web (ya lo es vía réplica RO + overlay). |
| **Reportes** | Se queda (completo) | Sin recortes. |
| **Cierre** | Se queda (núcleo) | Arqueo, conteo de efectivo, movimientos de caja. |
| Clientes | → Web | POS conserva solo selector/alta rápida en Venta. |
| Proveedores · Compras · Gastos · Cuentas | → Web (hub "Terceros y finanzas") | |
| Despiece | → Web | Costeo administrativo. |
| Devoluciones | → integrada en Venta | La vista suelta desaparece. |
| Usuarios | → Web | POS conserva login. |
| "Cambiar mi contraseña" | → menú de perfil | Deja de ser botón/vista. |

Rail final del POS: **Venta · Inventario · Reportes · Cierre** (+ menú de perfil en el header).

### Web — de 4 vistas a ~7

| Vista Web | Estado | Contenido |
|---|---|---|
| **Inicio / Dashboard** | existe | KPIs. |
| **Reportes** | expandir | Período · categoría · factura · cajero · compras · mensual (≥ POS). |
| **Catálogo** | existe | Maestro de productos + overlay + promociones. |
| **Inventario** | existe | Multi-bodega, ubicaciones, pendientes, stock. |
| **Terceros y finanzas** | NUEVO (hub por secciones) | Clientes · Proveedores · Compras · Gastos · Cuentas (CxC/CxP). |
| **Despiece** | NUEVO | Costeo de canal en cortes. |
| **Usuarios y roles** | NUEVO | Gestión de usuarios + perfil/contraseña. |

## UX e interacción (POS y Web)

Objetivo transversal del usuario: **iconos claros + título de vista visible**, y
limpiar la interacción.

### POS
- **Cabecera por vista (nueva):** franja superior con **icono distintivo + título**.
- **Rail icono + etiqueta:** con solo 4 vistas, cada una con su propio icono y nombre.
- **Menú de perfil (arriba a la derecha):** usuario actual → *Cambiar mi contraseña* ·
  *Cerrar sesión*. Ahí muere el botón/vista suelto de contraseña.
- **Estado de caja** (● Caja #N · efectivo) permanece en la barra inferior.
- **Devolución** como acción dentro de Venta, sin pantalla aparte.

### Web
- **Sidebar agrupada** (reemplaza chip-tabs; 7 ítems se amontonan):
  - Operación & análisis: Inicio · Reportes · Inventario · Catálogo
  - Administración: Terceros y finanzas · Despiece · Usuarios
- **Mismo patrón de cabecera:** cada vista con **icono + título**, consistente con el POS.
- **Terceros y finanzas** con sub-pestañas internas (Clientes/Proveedores/Compras/Gastos/Cuentas).
- **Menú de perfil** arriba a la derecha (sesión Supabase + cambiar contraseña).

### Consistencia de marca
Ambos ya comparten el Sistema de Diseño "Carnes y Fruver RL" (tokens, rojo
`#E01E26`, tipografías). Iconos y cabeceras se definen una vez y se aplican en los dos.

## Fases (un solo plan, con prefijos de task por fase)

El usuario pidió **una sola spec y un solo plan** para todo el programa. El plan
usa un prefijo de task único por fase (convención `planes-pos`), todos nuevos y
sin colisión con epics existentes:

| Fase | Prefijo | Alcance | Riesgo |
|---|---|---|---|
| **A — Shell & UX base** | `SHELL` | POS: cabecera icono+título por vista, iconos distintivos, rail icono+etiqueta, menú de perfil (absorbe "cambiar contraseña", elimina el botón suelto). Web: sidebar agrupada, misma cabecera, menú de perfil. No mueve lógica. | Bajo |
| **B — Devolución en Venta** | `DEVOL` | Integrar devoluciones al flujo de Venta; quitar `PantallaDevoluciones` del rail. Dominio ya existe, es re-UX. | Bajo |
| **C — Terceros y finanzas (web) + salida del POS** | `TERC` | Backend FastAPI sobre `ServicioClientes/Proveedores/Compras/Gastos/CuentasCobrar/CuentasPagar` (repos Postgres); hub web con sub-pestañas; quitar esas 5 vistas del POS (Venta conserva selector/alta rápida de cliente). | Alto |
| **D — Despiece (web) + salida del POS** | `DESP` | Backend `ServicioDespiece` sobre Postgres, UI web, quitar del POS. | Medio |
| **E — Usuarios + Reportes web completos** | `ADMIN` | Web: gestión de usuarios/roles (`ServicioUsuarios`) y Reportes a paridad con POS (período·categoría·factura·cajero·compras·mensual). POS conserva login y sus reportes. | Medio |

**Orden recomendado:** A → B → C → D → E (bajo riesgo primero; el hueco de
capacidad en el POS solo aparece cuando el equivalente web ya existe).

## Regla transversal de verificación

Cada fase corre su suite antes de cerrarse:
- POS: `python -m pytest -q` (verde).
- Backend web: `pytest` con `TEST_DB_URL` (verde).
- Front web: `tsc -b` + `npm run build` + gate `impeccable` limpio.
- Migraciones nuevas se aplican **también a la BD real de Supabase**
  (`SUPABASE_DB_URL`), no solo a la BD de tests (aprendizaje NUBE2).

Al cerrar cada fase se actualiza la fila correspondiente en `docs/README-pos.md`.

## Fuera de alcance

- Facturación electrónica DIAN (epic aparte, pendiente).
- Nuevas reglas de negocio: este programa **mueve y re-expone** lógica existente,
  no inventa dominio nuevo (salvo el mínimo de wiring Postgres por servicio).
- RLS Postgres y roles web avanzados (spec propio de multi-tenant).

## Riesgos y decisiones abiertas

- **Paridad de repositorios Postgres:** varios servicios de `core` solo tienen
  adaptador SQLite. Cada fase que mueve un servicio debe crear su
  `RepositorioXPostgres` en el backend (patrón ya establecido para ventas/catálogo/inventario).
- **Hueco de capacidad temporal:** aceptable por ser demo/propuesta sin datos
  reales; aun así el orden A→E minimiza el tiempo en que una función no está en
  ningún lado.
- **`core` como fuente única:** si una regla vive hoy en la UI Qt (no en `core`),
  moverla obliga a bajarla a `core` primero para que la web la reutilice.
