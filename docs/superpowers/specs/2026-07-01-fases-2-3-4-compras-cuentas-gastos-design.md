# Spec + Plan — Fases 2, 3 y 4: Proveedores/Compras, Cuentas, Gastos

Documento único (diseño + plan de implementación) para las Fases 2-4 del
[roadmap del cliente](../../analisis-requerimientos-cliente.md). Se escribe combinado y con
tests mínimos por decisión explícita (minimizar tokens): **un test del flujo crítico por
módulo**, no cobertura exhaustiva. Base: rama `feature/fase-1-core-caja` (367 tests).

## Decisiones confirmadas (2026-07-01)

1. **Fiado (CxC) y deuda a proveedores (CxP): saldo global** por cliente/proveedor, no por
   factura. Un número neto (Σ deuda − Σ abonos); sin antigüedad ni aplicación a facturas.
2. **Compra "en canal": módulo de despiece con costeo.** El despiece reparte el costo del canal
   entre los cortes por **valor de venta** (no por peso), para obtener margen real por corte.
3. **Todo el efectivo pasa por la caja.** Abonos, pagos a proveedor y gastos en efectivo se
   registran como ingreso/egreso de caja (Fase 1) y exigen sesión de caja abierta.
4. **Categorías de gasto: lista fija administrable** (tabla + seed), no texto libre.

## Principio rector

Reutilizar lo que ya existe. En particular la infraestructura de la Fase 1:
`MovimientoCaja` + `ServicioCaja.registrar_movimiento` son el **único punto** por donde el
efectivo entra o sale de la caja. Todo abono/pago/gasto en efectivo se canaliza como
`ingreso`/`egreso` de caja (motivo descriptivo), y así el arqueo cuadra sin lógica nueva.

Arquitectura intacta: entidades y servicios en `src/core/` (sin Qt/SQLite), SQL solo en
adaptadores de `src/inventario/` y `src/ventas/`, UI en `src/caja/`.

---

## FASE 2 — Proveedores y Compras

### Modelo de datos (migración `008_proveedores_compras.sql`)

- `proveedores` (id, identificacion UNIQUE, nombre, contacto) — espejo exacto de `clientes`.
- `compras` (id, proveedor_id→proveedores, fecha TEXT, total DECIMAL,
  estado TEXT['pagada'|'credito'], usuario_id→usuarios).
- `compra_lineas` (id, compra_id→compras, producto_id→productos, cantidad DECIMAL,
  costo_unit DECIMAL, subtotal DECIMAL).
- `despieces` (id, producto_canal_id→productos, peso_canal DECIMAL, costo_canal DECIMAL,
  fecha TEXT, usuario_id).
- `despiece_lineas` (id, despiece_id→despieces, producto_corte_id→productos, peso DECIMAL,
  costo_asignado DECIMAL, costo_unit DECIMAL).

**Compra "en canal" + despiece con costeo:** la compra de "res en canal" es una línea normal con
el producto-canal (suma stock del canal). El **despiece** es un módulo aparte: se toma un peso
del canal y se reparte en cortes. El costo del canal se **prorratea por valor de venta**:
para cada corte `valor = precio_venta_corte × peso_corte`; `costo_asignado_corte =
costo_canal × (valor_corte / Σ valores)`; `costo_unit = costo_asignado / peso_corte`. Así el
lomo absorbe más costo que la molida y el margen por corte es realista. El despiece genera los
movimientos de inventario (salida del canal, entradas de cada corte) y actualiza el `costo` de
cada producto-corte. Si un corte no tiene precio de venta, se prorratea por peso como fallback.

### Dominio y comportamiento

- Entidades `Proveedor`, `Compra`, `LineaCompra` en `core/entidades.py`.
- Puertos `RepositorioProveedores`, `RepositorioCompras` en `core/puertos.py`.
- `ServicioProveedores` (CRUD, espejo de `ServicioClientes`).
- `ServicioCompras.registrar(compra)`: persiste la compra y, por cada línea, registra una
  `entrada` de inventario (alimenta stock) y actualiza el `costo` del producto al `costo_unit`
  de la línea. Si `estado == 'credito'`, la compra queda como cuenta por pagar (Fase 3 la lee).
- `ServicioDespiece.registrar(despiece)`: valida que `peso_canal ≤` stock del canal, prorratea
  el `costo_canal` por valor de venta entre los cortes, registra la salida del canal y las
  entradas de cada corte, y actualiza el `costo` de cada producto-corte.
- `ServicioReportes.compras(desde, hasta)` y `.compras_por_proveedor(desde, hasta)`.

### UI (`src/caja/`)

- `PantallaProveedores` (espejo de `PantallaClientes`), entrada en el rail.
- `PantallaCompras`: seleccionar proveedor, agregar líneas (producto/cantidad/costo), elegir
  contado o crédito, confirmar. Incluye acción "Despiezar" (o pantalla propia): elegir canal,
  peso a despiezar y los cortes con su peso; muestra el costo prorrateado por corte antes de
  confirmar. Entrada en el rail.
- Pestaña "Compras" en `PantallaReportes` (por período y por proveedor).

---

## FASE 3 — Cuentas por Cobrar (fiado) y por Pagar

### Modelo de datos (migración `009_cuentas.sql`)

- `INSERT` medio de pago `(4, 'Crédito/Fiado')`.
- `abonos_cliente` (id, cliente_id→clientes, monto, fecha, medio_pago_id→medios_pago,
  caja_sesion_id→caja_sesiones NULL, usuario_id).
- `pagos_proveedor` (id, proveedor_id→proveedores, monto, fecha, medio_pago_id,
  caja_sesion_id NULL, usuario_id).

### CxC — fiado (reusa `pagos` y `ventas` existentes)

- Una venta a crédito es una venta normal con un `Pago` de `medio_pago_id = 4`. El arqueo ya
  la excluye del efectivo (solo cuenta medio=1). Cero lógica nueva en caja para la venta.
- **Saldo del cliente** = Σ pagos fiado del cliente − Σ abonos del cliente.
- `ServicioCuentasCobrar`: `saldo(cliente_id)`, `pendientes()` (clientes con saldo > 0),
  `abonar(cliente_id, monto, medio, fecha, usuario_id)`. Si el abono es en efectivo, además
  llama `ServicioCaja.registrar_movimiento(ingreso, motivo="Abono <cliente>")`.
- Puerto `RepositorioCuentasCobrar` (persiste/lee `abonos_cliente`; el saldo se calcula en el
  servicio combinando abonos + pagos fiado que ya expone `RepositorioVentas`).

### CxP (sobre las compras a crédito de Fase 2)

- **Saldo del proveedor** = Σ compras crédito − Σ pagos al proveedor.
- `ServicioCuentasPagar`: `saldo(proveedor_id)`, `pendientes()`,
  `pagar(proveedor_id, monto, medio, fecha, usuario_id)`. Pago en efectivo → `egreso` de caja.
- Puerto `RepositorioCuentasPagar` (persiste/lee `pagos_proveedor`).

### UI

- `PantallaCuentas` con dos pestañas: "Por cobrar" (lista clientes con saldo + botón Abonar) y
  "Por pagar" (lista proveedores con saldo + botón Pagar). Diálogos de abono/pago reutilizan el
  patrón de `DialogoMovimientoCaja`.
- En `PantallaVenta`/`DialogoCobro`: permitir elegir medio "Crédito/Fiado" (exige cliente
  identificado, no consumidor final).

---

## FASE 4 — Gastos y Reporte Mensual Consolidado

### Modelo de datos (migración `010_gastos.sql`)

- `categorias_gasto` (id, nombre UNIQUE) con seed: arriendo, servicios, transporte, nómina,
  otros. Lista fija administrable (el admin agrega/edita).
- `gastos` (id, fecha, categoria_gasto_id→categorias_gasto, monto DECIMAL, descripcion TEXT,
  medio_pago_id→medios_pago, caja_sesion_id NULL, usuario_id).

### Dominio y UI

- Entidades `CategoriaGasto`, `Gasto`; puertos `RepositorioCategoriasGasto`, `RepositorioGastos`;
  `ServicioGastos.registrar(...)`, `listar(desde, hasta)`, y gestión de categorías. Gasto en
  efectivo → `egreso` de caja.
- `PantallaGastos`: registrar (categoría desde combo) y listar por período; sección para
  administrar categorías (solo admin). Entrada en el rail.
- **Reporte mensual consolidado**: `ServicioReportes.mensual(anio, mes) -> ReporteMensual`
  con `ventas`, `compras`, `gastos`, `saldo_cxc`, `saldo_cxp` (todo derivado de los servicios
  ya existentes). Pestaña "Mensual" en `PantallaReportes` con selector de mes.

---

## Plan de implementación

Orden por task: dominio → persistencia → UI. **Un test por flujo crítico** (el marcado
`+test`); el resto se valida manualmente (`python -m caja`). Correr `python -m pytest -q` tras
cada fase. Commits por task-group en español (`feat(proveedores): …`, etc.).

### Fase 2 — Proveedores y Compras

- **PROV.1 — Proveedor + ServicioProveedores (core)**
  Modify `core/entidades.py` (`Proveedor`), `core/puertos.py` (`RepositorioProveedores`);
  Create `core/servicio_proveedores.py`. Espejo de clientes.
- **PROV.2 — RepositorioProveedoresSQLite + migración 008 (parte proveedores)**
  Create `scripts/migraciones/008_proveedores_compras.sql`; Modify `ventas/repositorio_sqlite.py`.
- **COMPRA.1 — Compra/LineaCompra + ServicioCompras (core)** `+test`
  Modify `core/entidades.py`, `core/puertos.py`; Create `core/servicio_compras.py`.
  Test: `tests/core/test_servicio_compras.py` — registrar compra alimenta stock y actualiza costo.
- **COMPRA.2 — RepositorioComprasSQLite (migración 008 parte compras)**
  Modify `ventas/repositorio_sqlite.py`; wiring en `caja/contexto.py`.
- **DESPIECE.1 — Despiece/LineaDespiece + ServicioDespiece con costeo (core)** `+test`
  Modify `core/entidades.py`, `core/puertos.py`; Create `core/servicio_despiece.py`.
  Test: `tests/core/test_servicio_despiece.py` — prorrateo por valor de venta; salida del
  canal + entradas de cortes; costo por corte actualizado.
- **DESPIECE.2 — RepositorioDespiecesSQLite (migración 008 parte despiece)**
  Modify `scripts/migraciones/008_proveedores_compras.sql`, `ventas/repositorio_sqlite.py`,
  `caja/contexto.py`.
- **COMPRA.3 — Reporte compras + por proveedor (ServicioReportes)**
  Modify `core/servicio_reportes.py` (`compras`, `compras_por_proveedor`).
- **COMPRA.4 — PantallaProveedores + PantallaCompras + PantallaDespiece + pestaña Compras (caja)**
  Create `caja/pantalla_proveedores.py`, `caja/pantalla_compras.py`, `caja/pantalla_despiece.py`;
  Modify `caja/pantalla_reportes.py`, `caja/ventana_principal.py`.

### Fase 3 — Cuentas por cobrar y pagar

- **CXC.1 — ServicioCuentasCobrar + puerto + migración 009 (core + SQLite)** `+test`
  Create `scripts/migraciones/009_cuentas.sql` (medio 4 + `abonos_cliente`);
  Modify `core/entidades.py` (`AbonoCliente`), `core/puertos.py`;
  Create `core/servicio_cuentas_cobrar.py`; Modify `ventas/repositorio_sqlite.py`.
  Test: `tests/core/test_cuentas_cobrar.py` — saldo = ventas fiado − abonos; abono efectivo
  genera ingreso de caja.
- **CXP.1 — ServicioCuentasPagar + puerto + `pagos_proveedor` (core + SQLite)** `+test`
  Modify `009_cuentas.sql` (`pagos_proveedor`), `core/entidades.py`, `core/puertos.py`,
  `ventas/repositorio_sqlite.py`; Create `core/servicio_cuentas_pagar.py`.
  Test: `tests/core/test_cuentas_pagar.py` — saldo proveedor; pago efectivo genera egreso.
- **CUENTAS.UI — PantallaCuentas + medio Fiado en cobro (caja)**
  Create `caja/pantalla_cuentas.py`; Modify `caja/dialogos/dialogo_cobro.py`,
  `caja/ventana_principal.py`, `caja/contexto.py`.

### Fase 4 — Gastos y reporte mensual

- **GASTO.1 — CategoriaGasto + Gasto + ServicioGastos + migración 010 (core + SQLite)** `+test`
  Create `scripts/migraciones/010_gastos.sql` (`categorias_gasto` con seed + `gastos`),
  `core/servicio_gastos.py`; Modify `core/entidades.py`, `core/puertos.py`,
  `ventas/repositorio_sqlite.py`.
  Test: `tests/core/test_servicio_gastos.py` — gasto efectivo genera egreso de caja.
- **MENSUAL.1 — ServicioReportes.mensual (core)** `+test`
  Modify `core/servicio_reportes.py` (`ReporteMensual` + `mensual`).
  Test: `tests/core/test_reporte_mensual.py` — consolida ventas/compras/gastos/saldos.
- **GASTO.UI — PantallaGastos + pestaña Mensual (caja)**
  Create `caja/pantalla_gastos.py`; Modify `caja/pantalla_reportes.py`,
  `caja/ventana_principal.py`.

### Cierre

- Actualizar filas de estado en `docs/README-pos.md` y marcar Fases 2-4 ✅ en el análisis.
- `python -m pytest -q` en verde.

## Notas de decisión (Ponytail)

- CxC/CxP no duplican los montos: el saldo se **deriva** de pagos/compras existentes + la
  tabla de abonos/pagos, sin columna de saldo materializada (decisión 1: saldo global).
- El despiece reusa los movimientos de inventario existentes; solo agrega el encabezado
  `despieces` para trazar el prorrateo. El costeo por valor de venta es una función pura en
  `core` (fácil de testear) que cae a prorrateo por peso si falta un precio (decisión 2).
- Todo efectivo (abono, pago proveedor, gasto) pasa por `ServicioCaja.registrar_movimiento`
  → el arqueo de Fase 1 es la única fuente de verdad del efectivo (decisión 3).
- Categorías de gasto en tabla con seed, administrables por el admin (decisión 4).
