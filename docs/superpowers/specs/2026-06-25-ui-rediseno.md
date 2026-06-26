# Spec: Rediseño UI completo — pos-siesa-remake

**Fecha:** 2026-06-25  
**Rama:** `feat/ui-rediseno`  
**Estado:** aprobado para implementación

---

## 1. Contexto y motivación

El proyecto tiene toda la lógica de dominio completa (E1–E7, 140 pruebas en verde), pero la capa de UI es un prototipo mínimo: dos widgets sueltos (`PantallaVenta`, `PantallaClientes`) sin shell de navegación, sin estilos, sin arranque unificado. Este spec define la UI completa del POS: una app ejecutable, linda y funcionalmente completa para las operaciones diarias de caja en un negocio de carnes y frutas.

---

## 2. Decisiones de diseño (inamovibles)

| Decisión | Valor |
|---|---|
| Toolkit | PySide6 (Qt6), solo widgets nativos |
| Estilos | QSS global en `src/caja/tema.qss`; sin `paintEvent`, sin estilos inline, sin QtWebEngine |
| Animaciones | Ninguna (hardware viejo) |
| Dependencias nuevas | Ninguna fuera de PySide6 ya instalado |
| Hexagonal | `src/core/` sin imports Qt; UI accede a datos solo vía servicios/repos inyectados |
| Idioma de dominio | Español (nombres de entidades, puertos, servicios) |

### Paleta de color

| Token | Color | Uso |
|---|---|---|
| `fondo-app` | `#0B0E14` | Ventana principal |
| `panel` | `#151A25` | Rail, sidebars |
| `card` | `#1E2330` | Tarjetas de producto, filas de tabla |
| `borde` | `#2E3548` | Separadores, bordes de input |
| `texto-primario` | `#F0F2F5` | Etiquetas principales |
| `texto-secundario` | `#8B95A8` | Etiquetas secundarias |
| `texto-muted` | `#5A6278` | Placeholder, hints |
| `acento` | `#EF4444` | Botones primarios, selección activa en rail |
| `acento-hover` | `#DC2626` | Hover de botones primarios |
| `positivo` | `#22C55E` | Stock ok, sobrante de arqueo |
| `alerta` | `#F59E0B` | Stock bajo, faltante de arqueo |

---

## 3. Estructura de archivos

```
src/caja/
  __init__.py              # sin cambios
  __main__.py              # python -m caja [pos.db]  → punto de entrada
  contexto.py              # ContextoApp: repos + servicios construidos y expuestos
  bootstrap.py             # ruta DB, aplica migraciones, seed demo idempotente
  ventana_principal.py     # VentanaPrincipal: rail + QStackedWidget + barra estado
  tema.qss                 # hoja de estilo dark navy (único lugar de CSS/QSS)
  tema.py                  # carga_tema(app): aplica tema.qss
  formato.py               # formato_moneda / formato_cantidad / formato_fecha
  widgets.py               # TarjetaProducto, TarjetaKpi, BotonRail (composición Qt pura)
  recursos/
    iconos/                # SVGs monocromos del rail (venta, inventario, clientes,
                           #   devoluciones, reportes, cierre) — ~24×24 px
  pantalla_venta.py        # rediseño (era prototipo mínimo)
  pantalla_clientes.py     # rediseño + edición inline
  pantalla_inventario.py   # NUEVA
  pantalla_reportes.py     # NUEVA
  pantalla_cierre.py       # NUEVA
  pantalla_devoluciones.py # NUEVA
  dialogos/
    __init__.py
    dialogo_cobro.py       # multi-medio + vuelto
    dialogo_producto.py    # crear / editar Producto
    dialogo_movimiento.py  # registrar movimiento de inventario
```

`scripts/caja.py` se reduce a una llamada a `python -m caja`; su lógica pasa a `__main__.py`.

---

## 4. Composition root (`contexto.py` + `bootstrap.py`)

### bootstrap.py

Responsabilidad: abrir la conexión SQLite, aplicar migraciones y sembrar datos demo si la tabla está vacía. **Todo idempotente** (`INSERT OR IGNORE`).

Seed que las migraciones no cubren:
- **Categorías:** Carnes, Frutas, Verduras, Abarrotes
- **Impuestos:** IVA 0% (`id=1`), IVA 19% (`id=2`)
- **Productos demo** (4-6 ítems: pechuga, manzana, papa, arroz con código, precio, unidad)
- **Movimiento inicial de stock** por producto demo

`medios_pago` y `Consumidor final` ya los siembran las migraciones existentes; no se duplican.

### contexto.py — `ContextoApp`

Clase que construye y expone todos los adaptadores y servicios. Cada pantalla recibe solo los objetos que necesita (DI explícita, sin singleton global).

```python
@dataclass
class ContextoApp:
    conn: sqlite3.Connection
    # repos
    repo_productos: RepositorioProductosSQLite
    repo_categorias: RepositorioCategoriasSQLite
    repo_impuestos: RepositorioImpuestosSQLite
    repo_inventario: RepositorioInventarioSQLite
    repo_clientes: RepositorioClientesSQLite
    repo_medios_pago: RepositorioMediosPagoSQLite
    repo_ventas: RepositorioVentasSQLite
    repo_sesiones: RepositorioCajaSesionesSQLite
    repo_devoluciones: RepositorioDevolucionesSQLite
    # servicios
    svc_venta: ServicioVenta
    svc_registro: ServicioRegistroVenta
    svc_anulacion: ServicioAnulacion
    svc_clientes: ServicioClientes
    svc_caja: ServicioCaja
    svc_devolucion: ServicioDevolucion
    svc_reportes: ServicioReportes

    @classmethod
    def crear(cls, ruta_db: str) -> "ContextoApp": ...
```

`__main__.py` llama `bootstrap(ruta)`, construye `ContextoApp`, crea `QApplication`, instancia `VentanaPrincipal(ctx)` y llama `app.exec()`.

---

## 5. Extensiones de puertos (mínimas, hexagonal intacta)

El CRUD de productos y los chips de categoría requieren lecturas que los puertos actuales no exponen. Se añaden solo las firmas necesarias:

| Puerto (Protocol en `core/puertos.py`) | Método nuevo |
|---|---|
| `RepositorioCategorias` | `listar() -> list[Categoria]`; `por_id(id) -> Categoria \| None` |
| `RepositorioImpuestos` | `listar() -> list[Impuesto]` |
| `RepositorioProductos` | `actualizar(producto: Producto) -> Producto` |
| `RepositorioCajaSesiones` | `listar() -> list[CajaSesion]` (para el combo de sesiones en Reportes) |

Implementaciones SQLite en `inventario/repositorio_sqlite.py`. `core` solo amplía la firma Protocol; sin SQL, sin Qt.

---

## 6. Sistema de estilos (`tema.qss` + `tema.py`)

`tema.qss` cubre todos los widgets usados:
- `QMainWindow`, `QWidget#fondo` → `#0B0E14`
- `QWidget#panel`, `QWidget#rail` → `#151A25`
- `QWidget#card`, `QTableWidget` → `#1E2330`; `gridline-color: #2E3548`
- `QHeaderView::section` → `#151A25`, texto `#8B95A8`
- `QLineEdit`, `QDateEdit`, `QSpinBox` → borde `#2E3548`, fondo `#1E2330`, texto `#F0F2F5`; `::focus` borde `#EF4444`
- `QPushButton#primario` → `#EF4444`; `:hover` → `#DC2626`; `:disabled` → `#5A6278`
- `QPushButton#secundario` → `transparent`, borde `#2E3548`
- `QToolButton#rail` → `#151A25`; `:checked` → borde izquierdo 3px `#EF4444`, fondo `#1E2330`
- `QLabel#kpi-valor` → `#F0F2F5`, font-size 22px bold
- `QLabel#positivo` → `#22C55E`; `QLabel#alerta` → `#F59E0B`
- `QScrollBar` → fondo `#151A25`, handle `#2E3548`
- `QMessageBox` → fondo `#1E2330`, texto `#F0F2F5`

`tema.py` expone `carga_tema(app: QApplication)` que lee el `.qss` relativo a su propio directorio y lo aplica con `app.setStyleSheet(...)`.

### widgets.py — componentes reutilizables

- **`TarjetaProducto(QFrame)`**: nombre (bold), precio, categoría. Click emite señal `seleccionado(producto)`. `setObjectName("card")`.
- **`TarjetaKpi(QFrame)`**: label título + label valor (objeto `kpi-valor`) + label subtítulo. Sin lógica.
- **`BotonRail(QToolButton)`**: checkable, icono SVG, tooltip, `setObjectName("rail")`.

---

## 7. Shell de navegación (`ventana_principal.py`)

`VentanaPrincipal(QMainWindow)`:

```
┌──────────────────────────────────────────────────────┐
│ rail(60px) │          QStackedWidget                 │
│  [●] Venta │                                         │
│  [ ] Inv.  │  pantalla activa                        │
│  [ ] Cli.  │                                         │
│  [ ] Dev.  │                                         │
│  [ ] Rep.  │                                         │
│  [ ] Cie.  │                                         │
├────────────┴─────────────────────────────────────────┤
│ barra estado: ● Caja #3 abierta │ Efectivo: $45.200  │
└──────────────────────────────────────────────────────┘
```

- Rail: `QButtonGroup` exclusivo de `BotonRail`. Click → `stack.setCurrentIndex(i)` + llama `pantalla.al_mostrar()`.
- Orden de pantallas (índice 0–5): Venta, Inventario, Clientes, Devoluciones, Reportes, Cierre.
- Barra de estado: `QStatusBar`. Muestra caja abierta (id + estado) y efectivo en vivo. Se refresca en `al_mostrar()` de cada pantalla y tras cobrar/cerrar.
- La `VentanaPrincipal` expone el `sesion_abierta()` actual (leído de `repo_sesiones.abierta()`) para que pantallas lo consulten.

---

## 8. Pantallas

### 8.1 PantallaVenta

Layout dos columnas (proporción ~65/35):

**Columna izquierda — catálogo:**
- `QLineEdit` búsqueda con placeholder "Buscar producto…" (filtra por nombre o código en la grilla).
- Fila de chips de categoría: `QPushButton` checkable por categoría + "Todas". Filtra la grilla.
- `QScrollArea` con `QGridLayout` de `TarjetaProducto` (4 columnas). Adaptado al ancho.

**Columna derecha — carrito:**
- `QTableWidget` (3 cols: Descripción, Cant/Peso, Subtotal). Ítems no editables. Click derecho o botón × quita ítem.
- `QLabel` Total en texto grande (`kpi-valor`).
- `QPushButton#primario` "Cobrar": deshabilitado si `ctx.repo_sesiones.abierta() is None` o carrito vacío. Click abre `DialogoCobro`.

**Flujo "agregar producto":**
1. Click en `TarjetaProducto`.
2. Si `producto.vendido_por_peso`: mini-diálogo (`QInputDialog`) pide kg; valida `> 0`.
3. `svc_venta.agregar(codigo, peso_kg=...)` → agrega fila al carrito, actualiza total.
4. Error de dominio → barra de estado roja temporal (sin `QMessageBox`).

**Tras cobro exitoso:** carrito limpiado, `svc_venta` reemplazado por una nueva instancia de `ServicioVenta` (construida desde el contexto), barra estado refrescada.

### 8.2 DialogoCobro

`QDialog` modal. Recibe: total de venta, lista de medios de pago, `caja_sesion_id`.

Layout:
- Total a cobrar (grande).
- Tabla de medios: checkbox + nombre + `QLineEdit` monto por medio.
- `QLabel` "Vuelto en efectivo" (calculado en vivo al cambiar montos; `textChanged`).
- Validación: suma de montos ≥ total; al menos un medio seleccionado.
- `QPushButton#primario` "Confirmar": llama `svc_registro.registrar(venta, pagos)`.
- Error de dominio (`CajaNoAbierta`, etc.) → `QMessageBox.warning`.

### 8.3 PantallaInventario

**Tabla de productos** (`QTableWidget`, columnas: Código, Nombre, Categoría, Precio, Costo, Stock, Unidad, Por Peso):
- Stock calculado en `al_mostrar()` con `repo_inventario.stock_de(producto.id)`.
- Stock ≤ 0: celda en color `alerta`.
- `QLineEdit` búsqueda arriba filtra la tabla (`hideRow`/`showRow`).

**Barra de herramientas** (encima de la tabla):
- `QPushButton` "Nuevo producto" → `DialogoProducto(modo=crear)`.
- `QPushButton` "Editar" → `DialogoProducto(modo=editar, producto=seleccionado)`; deshabilitado si no hay selección.
- `QPushButton` "Movimiento" → `DialogoMovimiento(producto=seleccionado)`; deshabilitado si no hay selección.

**DialogoProducto:** campos: código barras, nombre, precio, costo, categoría (combo), impuesto (combo), vendido por peso (checkbox), unidad. En modo editar llama `repo_productos.actualizar(p)`.

**DialogoMovimiento:** tipo (entrada/salida combo), cantidad (`QDoubleSpinBox`), referencia (`QLineEdit` opcional). Llama `repo_inventario.registrar(MovimientoInventario(...))`.

### 8.4 PantallaClientes

Layout: tabla a la izquierda + panel de formulario a la derecha (colapsado si no hay selección).

**Tabla** (Identificación, Nombre, Contacto). Búsqueda por identificación o nombre. Click → llena el panel de edición.

**Panel formulario:**
- Campos: identificación, nombre, contacto.
- Botón "Crear" (si panel vacío) / "Guardar cambios" (si editando).
- `bloqueado_edicion=True` → campos deshabilitados (solo lectura), tooltip explicativo.
- Errores (`ClienteDuplicado`, `ValueError`) → `QLabel` de estado en rojo en el panel.

### 8.5 PantallaDevoluciones

**Paso 1 — buscar venta:**
- `QLineEdit` "ID de venta" + botón "Buscar" → `repo_ventas.por_id(id)`.
- Si no encontrada o estado `anulada`/`devuelta`: mensaje de error inline.
- Si válida: muestra resumen de venta (fecha, cliente, total) y tabla de líneas.

**Tabla de líneas devolvibles** (Producto, Vendido, Ya devuelto, Remanente, A devolver):
- "A devolver": `QDoubleSpinBox` por fila, máximo = remanente (de `repo_devoluciones.devuelto_por_linea`).
- Total a reembolsar: calculado en vivo.

**Paso 2 — reembolso:**
- Misma UI del `DialogoCobro` adaptada: medios de pago, montos, validación suma = total devuelto.
- Botón "Procesar devolución" → `svc_devolucion.devolver(venta_id, items, reembolsos, ...)` con `caja_sesion_id` activa.
- Éxito: mensaje de confirmación, resetea formulario.

### 8.6 PantallaCierre

**Si no hay caja abierta — formulario apertura:**
- `TarjetaKpi` mostrando estado "Caja cerrada".
- `QDoubleSpinBox` monto inicial.
- `QPushButton#primario` "Abrir caja" → `svc_caja.abrir(fecha=now(), monto_inicial=...)`.

**Si hay caja abierta — panel arqueo:**

```
┌─────────────────────────────────────────────────┐
│ [KPI] Monto inicial  [KPI] Ventas efectivo      │
│ [KPI] Esperado       [KPI] Diferencia (±color)  │
├─────────────────────────────────────────────────┤
│ Desglose por medio de pago  │ # ventas           │
│ Efectivo: $45.200           │ Devoluciones: $0   │
│ Transferencia: $20.000      │                    │
├─────────────────────────────────────────────────┤
│ Efectivo contado: [___________]   [Calcular]     │
├─────────────────────────────────────────────────┤
│             [Cerrar caja]                        │
└─────────────────────────────────────────────────┘
```

- Campo "Efectivo contado" (`QDoubleSpinBox`) → al cambiar recalcula arqueo en vivo vía `svc_caja.arqueo(sesion_id, monto_contado)`.
- "Diferencia" verde si ≥ 0, naranja si < 0.
- "Cerrar caja" → `svc_caja.cerrar(...)`, redirige a PantallaVenta, refresca barra estado.

### 8.7 PantallaReportes

**Controles superiores:** `QDateEdit` desde / hasta (defecto: hoy 00:00→23:59) + botón "Consultar".

**`QTabWidget`** con tres pestañas:

**Ventas:**
- `TarjetaKpi`: # ventas, total bruto, IVA, devoluciones, **neto**.
- Tabla por medio de pago (nombre resuelto vía `repo_medios_pago.por_id`): monto neto.

**Inventario:**
- Tabla por producto (nombre resuelto vía `repo_productos.por_id`): entradas, salidas, neto.

**Cierre por sesión:**
- `QComboBox` de sesiones en el rango (de `repo_sesiones`) → al seleccionar muestra `ReporteCierre` igual que `PantallaCierre` (solo lectura).

Sin librerías de gráficos — solo tablas y KPIs.

---

## 9. Helpers (`formato.py`)

```python
def formato_moneda(v: Decimal) -> str:              # "$ 1.234.567"
def formato_cantidad(v: Decimal, unidad: str) -> str:  # "1.500 kg" / "3 und"
def formato_fecha(dt: datetime) -> str:             # "25/06/2026 14:32"
```

Usados en todas las pantallas para homogeneidad visual. Sin dependencias externas (stdlib `format`).

---

## 10. Manejo de errores en UI

| Caso | Tratamiento |
|---|---|
| Error de dominio en acción puntual (agregar ítem) | `QLabel` de estado temporal en la pantalla; sin `QMessageBox` |
| Error en dialogo (cobro, devolución, movimiento) | `QLabel` de error dentro del diálogo; sin cerrar el diálogo |
| Error crítico inesperado | `QMessageBox.critical` + log a stderr |
| Validación de campo vacío | Resaltar borde `#EF4444` en el `QLineEdit` afectado |

Nunca mostrar trazas (`traceback`) al cajero.

---

## 11. Pruebas

- No se rompen los 140 tests existentes.
- Las pantallas mantienen testabilidad por DI (reciben servicios inyectados).
- Tests nuevos en `tests/caja/`:
  - `test_formato.py` — `formato_moneda`, `formato_fecha`, `formato_cantidad`.
  - `test_bootstrap.py` — seed idempotente (llamar dos veces no duplica).
  - `tests/inventario/test_repositorio_extensiones.py` — `listar()` categorías/impuestos, `actualizar()` producto.
- Tests de pantallas Qt (con `pytest-qt` si disponible) quedan fuera del scope inicial; se añadirán en E9.

---

## 12. Fuera de alcance (YAGNI)

- Login / gestión de usuarios
- Imágenes de producto
- Gráficos (charts/plots)
- Impresión de recibo
- Temas claros o modo claro
- Soporte multi-idioma
- Multi-caja / sync offline (E8)
- Facturación electrónica DIAN

---

## 13. Archivos afectados (resumen)

| Archivo | Acción |
|---|---|
| `src/core/puertos.py` | Añadir métodos a 3 Protocol |
| `src/inventario/repositorio_sqlite.py` | Implementar métodos nuevos (categorias.listar, impuestos.listar, productos.actualizar) |
| `src/ventas/repositorio_sqlite.py` | Implementar `RepositorioCajaSesionesSQLite.listar()` |
| `src/caja/__main__.py` | NUEVO |
| `src/caja/contexto.py` | NUEVO |
| `src/caja/bootstrap.py` | NUEVO |
| `src/caja/ventana_principal.py` | NUEVO |
| `src/caja/tema.qss` | NUEVO |
| `src/caja/tema.py` | NUEVO |
| `src/caja/formato.py` | NUEVO |
| `src/caja/widgets.py` | NUEVO |
| `src/caja/recursos/iconos/*.svg` | NUEVO (6 iconos) |
| `src/caja/pantalla_venta.py` | REESCRIBIR |
| `src/caja/pantalla_clientes.py` | REESCRIBIR |
| `src/caja/pantalla_inventario.py` | NUEVO |
| `src/caja/pantalla_reportes.py` | NUEVO |
| `src/caja/pantalla_cierre.py` | NUEVO |
| `src/caja/pantalla_devoluciones.py` | NUEVO |
| `src/caja/dialogos/__init__.py` | NUEVO |
| `src/caja/dialogos/dialogo_cobro.py` | NUEVO |
| `src/caja/dialogos/dialogo_producto.py` | NUEVO |
| `src/caja/dialogos/dialogo_movimiento.py` | NUEVO |
| `scripts/caja.py` | SIMPLIFICAR (delegar a `__main__`) |
| `tests/caja/test_formato.py` | NUEVO |
| `tests/caja/test_bootstrap.py` | NUEVO |
| `tests/inventario/test_repositorio_extensiones.py` | NUEVO |
