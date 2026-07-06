# Guía visual / UI — pos-siesa-remake

> **Propósito:** contrato único de cómo se construye la capa visual (`src/caja/`) para que
> cualquier agente (Claude, Codex, Gemini) o persona añada pantallas y diálogos **sin
> discrepancias** de estilo, estructura ni patrones. Si vas a tocar UI, esta es la fuente de
> verdad operativa; el diseño histórico está en
> [superpowers/specs/2026-06-25-ui-rediseno.md](superpowers/specs/2026-06-25-ui-rediseno.md).

**Regla base:** copia el patrón de una pantalla/diálogo existente del mismo tipo antes de
inventar uno nuevo. La consistencia manda sobre la preferencia personal.

---

## 1. Reglas inamovibles (no negociar)

| Regla | Detalle |
|---|---|
| Toolkit | **PySide6 (Qt6)**, solo widgets nativos. Nada de QtWebEngine, QML, ni HTML. |
| Estilos | **Todo el CSS vive en `src/caja/tema.qss`**. Prohibido `setStyleSheet` por widget, estilos inline y `paintEvent` custom. Se estiliza por `objectName`/propiedades. |
| Animaciones | **Ninguna** (corre en hardware viejo Debian). |
| Dependencias | **Ninguna** fuera de PySide6 ya instalado. Sin librerías de gráficos/charts. |
| Hexagonal | La UI **no** contiene lógica de negocio ni SQL. Recibe servicios/repos por inyección y llama sus métodos. Ver §7. |
| Idioma | **Español** en clases, métodos, atributos, textos y objectNames de dominio (`PantallaVenta`, `_guardar`, `caja_cambiada`). |
| Moneda/fecha | Siempre vía `caja/formato.py` (`formato_moneda`, `formato_cantidad`, `formato_fecha`). Nunca formatear a mano. |

---

## 2. Paleta y tokens (definidos en `tema.qss`)

Tema oscuro *dark navy*. **No introducir colores nuevos**; usar estos tokens vía objectName.

| Token | Hex | Uso |
|---|---|---|
| fondo-app | `#0B0E14` | `QMainWindow`, `QWidget#fondo`, `QDialog` |
| panel | `#151A25` | `QWidget#panel`, `QWidget#rail`, headers, statusbar |
| card | `#1E2330` | `QFrame#card`, tablas, inputs |
| borde | `#2E3548` | bordes de inputs, gridlines, separadores |
| texto-primario | `#F0F2F5` | texto por defecto |
| texto-secundario | `#8B95A8` | `QLabel#secundario`, headers de tabla |
| texto-muted | `#5A6278` | `QLabel#muted`, placeholders, disabled |
| acento | `#EF4444` | botón primario, foco de input, selección, rail activo, errores de borde |
| acento-hover | `#DC2626` | hover del primario |
| positivo | `#22C55E` | `QLabel#positivo` (stock ok, sobrante de arqueo) |
| alerta | `#F59E0B` | `QLabel#alerta`, `badge-promo` (stock bajo, faltante, promo) |
| error | `#EF4444` | `QLabel#error` |

**El rojo `#EF4444` es el acento del negocio (carnes).** Se usa para *la* acción principal de
cada pantalla y para el foco; no lo repartas en elementos secundarios.

---

## 3. Vocabulario de `objectName` (así se aplica el estilo)

En vez de estilos inline, se asigna `setObjectName(...)` o `setProperty(...)` y el QSS pinta.
Lista cerrada de nombres reconocidos por `tema.qss` — **usa estos, no inventes**:

**Contenedores:** `fondo` (central de ventana), `panel` (sidebar/formulario), `rail`,
`card` (tarjeta/frame).

**Labels:** `secundario`, `muted`, `kpi-valor` (número grande 22px bold), `positivo`,
`alerta`, `error`, `badge-promo`, `badge-agotado`.

**Botones:** `primario` (rojo, acción principal — máximo uno destacado por vista),
`chip` (toggle checkable de filtro/categoría), `rail` (`QToolButton` de navegación).

**Propiedades dinámicas** (para estados en el mismo widget):
- `QFrame#card[promo="true"]` → borde ámbar. `[agotado="true"]` → fondo apagado.
- `QLineEdit[error="true"]` → borde rojo (marcar campo inválido).

Al cambiar un objectName/propiedad **después** de crear el widget, repolir el estilo:
```python
w.setProperty("error", True)
w.style().unpolish(w); w.style().polish(w)
```
(Ver `TarjetaKpi.set_estado` en `widgets.py` como referencia canónica.)

---

## 4. Widgets reutilizables (`src/caja/widgets.py`)

Antes de crear un widget nuevo, revisa si ya existe. Los actuales:

| Widget | Qué es | Cuándo usarlo |
|---|---|---|
| `SpinBoxPos` | `QSpinBox` que selecciona todo al enfocar | cantidades enteras |
| `DecimalSpinBoxPos` | `QDoubleSpinBox` que selecciona al enfocar | pesos/decimales |
| `SpinMoneda` | dinero: 0 decimales, separador de miles, prefijo `$ ` | **todo input de dinero** |
| `TarjetaProducto(QFrame)` | card clickable, emite `seleccionado(producto)` | grilla de catálogo |
| `TarjetaKpi(QFrame)` | título + valor grande + subtítulo; `set_valor/set_subtitulo/set_estado` | indicadores/resúmenes |
| `BotonRail(QToolButton)` | icono + tooltip, checkable exclusivo | navegación (solo la usa `VentanaPrincipal`) |

Componentes nuevos van aquí, **composición Qt pura, sin estilo inline** (el estilo va a `tema.qss`).

---

## 5. Anatomía de una Pantalla

Toda pantalla es un `QWidget` que se registra en el rail de `ventana_principal.py` y sigue este
contrato:

```python
class PantallaX(QWidget):
    caja_cambiada = Signal()          # SOLO si toca sesión de caja / efectivo (§6)

    def __init__(self, servicio_o_ctx) -> None:
        super().__init__()
        # construir widgets, layouts; sin lógica de negocio
        self.al_mostrar()             # primer llenado

    def al_mostrar(self) -> None:     # OPCIONAL pero estándar
        # recargar datos desde el servicio cada vez que la pantalla se activa
        ...
```

Reglas:
- **`al_mostrar()`**: la ventana la invoca al entrar a la pantalla. Poné aquí toda recarga de
  datos (listar, recalcular stock, refrescar tabla). No cargues datos pesados en `__init__`
  más allá de la primera llamada a `al_mostrar()`.
- **Inyección**: la pantalla recibe *lo mínimo* — un servicio concreto
  (`PantallaProveedores(servicio)`) o el `ContextoApp` completo si necesita varios
  (`PantallaVenta(ctx)`). El wiring está en `VentanaPrincipal._construir_pantalla`.
- **Sin SQL, sin reglas de negocio.** La pantalla solo orquesta widgets y delega en servicios.

### Layout estándar tabla + formulario (CRUD)

Patrón canónico para maestros (proveedores, clientes, usuarios). Copiar de
[pantalla_proveedores.py](../src/caja/pantalla_proveedores.py):

- `QHBoxLayout` raíz: **tabla 65 / panel 35** (`raiz.addWidget(tabla, 65)`, `addWidget(panel, 35)`).
- Tabla: `NoEditTriggers`, `SelectRows`, `cellClicked` → `_seleccionar_fila(fila)`.
- Panel derecho: `QWidget` con `objectName("panel")`, `QVBoxLayout` con los campos,
  botón guardar `objectName("primario")`, botón "Nuevo", y un `QLabel#error` para estado.
- Botón guardar alterna texto **"Crear" ↔ "Guardar cambios"** según `self._editando`.
- Campos `bloqueado_edicion` → `setEnabled(False)` + mensaje en el label de estado.
- Tras guardar: `self._nuevo()` (limpia) + `self.al_mostrar()` (recarga).

### Layout dos columnas (operativo)

Venta / devoluciones: catálogo o detalle a la izquierda (~65%), carrito/acción a la derecha
(~35%) rematado por un botón `#primario` grande. Ver [pantalla_venta.py](../src/caja/pantalla_venta.py).

---

## 6. Sesión de caja: señal `caja_cambiada`

Cualquier pantalla que abra/cierre caja o mueva efectivo (venta, cobro, cierre, cuentas,
gastos, devoluciones) **debe**:

1. Declarar `caja_cambiada = Signal()` a nivel de clase.
2. Emitirla (`self.caja_cambiada.emit()`) tras cobrar, abrir/cerrar caja o registrar movimiento.

`VentanaPrincipal` la conecta automáticamente (`_construir_pantalla`) a `_refrescar_estado`,
que actualiza la barra de estado (`● Caja #N abierta · Efectivo: $…`). No actualices la
statusbar directamente desde la pantalla; emití la señal.

Regla de negocio de UI: acciones de efectivo (cobrar, abonar, pagar proveedor, gasto en
efectivo) se **deshabilitan** si `ctx.repo_sesiones.abierta() is None`.

---

## 7. Diálogos (`src/caja/dialogos/`)

- Son `QDialog` modales, reciben datos ya cargados (listas de medios, totales) + `parent`.
- Diálogo simple → `QFormLayout` + `QDialogButtonBox(Ok|Cancel)`, con el botón Ok marcado
  `objectName("primario")`. Ver [dialogo_abono_pago.py](../src/caja/dialogos/dialogo_abono_pago.py).
- **No cierres el diálogo ante error de dominio**: mostrá un `QLabel#error` dentro del diálogo.
- El diálogo expone *getters* (`monto()`, `medio_pago_id()`); la pantalla llamadora decide y
  ejecuta el servicio tras `if dlg.exec() == QDialog.Accepted:`. El diálogo no toca servicios
  de escritura salvo que ya sea el patrón (cobro).
- Dinero siempre con `SpinMoneda`.

---

## 8. Manejo de errores en UI

| Caso | Tratamiento |
|---|---|
| Error de dominio en acción puntual (agregar ítem, guardar maestro) | `QLabel#error` o `showMessage` temporal en la statusbar. **Sin `QMessageBox`.** |
| Error dentro de un diálogo | `QLabel#error` en el diálogo; no lo cierres. |
| Campo vacío / inválido | `campo.setProperty("error", True)` + repolir (borde rojo). |
| Error crítico inesperado | `QMessageBox.critical` + log a stderr. |

**Nunca** mostrar `traceback` al cajero. Capturá `(ValueError, LookupError)` de los servicios
y traducí a mensaje en español.

---

## 9. Formato y textos

- Dinero: `formato_moneda(Decimal)` → `"$ 1.234.567"` (COP, sin decimales, punto de miles).
- Cantidades: `formato_cantidad(Decimal, unidad)` → `"1,5 kg"` / `"3 und"` (coma decimal es-CO).
- Fechas: `formato_fecha(datetime)` → `"02/07/2026 14:32"`.
- Placeholders en español y descriptivos (`"Buscar producto…"`, `"Contacto (opcional)"`).
- Botón de la acción principal en imperativo: "Cobrar", "Abrir caja", "Procesar devolución".

---

## 10. Iconos del rail

- SVG monocromos ~24×24 en `src/caja/recursos/iconos/`, cargados con `tema.icono("nombre")`.
- Registro de pantalla en el rail: editar `_DEFINICION` en
  [ventana_principal.py](../src/caja/ventana_principal.py) — tupla
  `(icono, tooltip, FactoryPantalla, permiso_o_None)`. Si la pantalla requiere permiso, pasar
  la acción de `core/permisos.py`; el rail la oculta según el rol del usuario.
- Reutilizá un icono existente si no hay uno específico (varias pantallas comparten `clientes`/
  `inventario` hoy); no agregues assets binarios sin necesidad real (Ponytail/YAGNI).

---

## 11. Checklist antes de dar por hecha una pantalla/diálogo

- [ ] Cero `setStyleSheet`/estilo inline; todo por objectName/propiedad ya soportado en `tema.qss`.
- [ ] Colores solo de la paleta §2.
- [ ] Cero SQL y cero regla de negocio en la clase de UI; todo vía servicio/repo inyectado.
- [ ] `al_mostrar()` recarga datos si la pantalla los muestra.
- [ ] Emití `caja_cambiada` si tocaste caja/efectivo; acciones de efectivo deshabilitadas sin sesión.
- [ ] Dinero con `SpinMoneda` + `formato_moneda`; fechas/cantidades con sus helpers.
- [ ] Errores de dominio → label/statusbar en español; nunca `traceback`.
- [ ] Reutilizaste el patrón CRUD (tabla 65 / panel 35) o dos columnas según corresponda.
- [ ] `python -m pytest -q` en verde; `python -m caja` arranca y se ve consistente.

---

## 12. Cómo levantar la UI

```bash
python -m caja            # usa pos.db por defecto (bootstrap + seed idempotente)
python -m caja ruta.db    # base alterna
# login admin de pruebas: usuario admin / clave admin1234
```

Referencias vivas para copiar patrones:
- CRUD maestro: [pantalla_proveedores.py](../src/caja/pantalla_proveedores.py)
- Operativo dos columnas + señal caja: [pantalla_venta.py](../src/caja/pantalla_venta.py)
- Diálogo simple: [dialogos/dialogo_abono_pago.py](../src/caja/dialogos/dialogo_abono_pago.py)
- Shell/navegación: [ventana_principal.py](../src/caja/ventana_principal.py)
- Estilos: [tema.qss](../src/caja/tema.qss) · Widgets: [widgets.py](../src/caja/widgets.py)
