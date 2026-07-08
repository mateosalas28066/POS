# Separación POS ↔ Web y limpieza de UI/UX — Plan de implementación

> **✅ COMPLETADO (2026-07-08).** Las 5 fases están implementadas, verdes y commiteadas
> en ambos repos (`w:\POS` rama `feature/plataforma-web-fase-0-1`, `w:\pos-plataforma-web` rama `master`):
> - **A · SHELL** — shell y UX base (POS rail de 4 vistas + cabecera/perfil; web Sidebar/CabeceraVista/MenuPerfil).
> - **B · DEVOL** — devolución integrada en Venta; se elimina `PantallaDevoluciones`.
> - **C · TERC** — clientes·proveedores·compras·gastos·cuentas en web (migración `008_terceros.sql`); se retiran las 5 pantallas del POS.
> - **D · DESP** — despiece en web (migración `009_despiece.sql`); se retira `PantallaDespiece`.
> - **E · ADMIN** — usuarios/roles + reportes de negocio en web (migración `010_usuarios_admin.sql`); se retira `PantallaUsuarios` (login se queda).
>
> **Gates finales:** backend `97 passed` (pos_test), POS `482 passed`, front `tsc -b`+`build`+`oxlint` limpios.
> Migraciones 008/009/010 aplicadas también a la **BD real** de Supabase (registradas en `schema_migraciones`).
> **Decisión de alcance:** `por_cajero_de_sesion` NO se portó a la web (es cierre de caja, propio del POS).
> **Resultado:** POS = Venta·Inventario·Reportes·Cierre; web = Inicio·Reportes·Catálogo·Inventario·Terceros·Despiece·Usuarios.
> El detalle por epic vive en [docs/README-pos.md](../../README-pos.md) (filas SHELL/DEVOL/TERC/DESP/ADMIN).
> Los checkboxes `- [ ]` de abajo son el registro histórico de ejecución task-a-task.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reenfocar el POS al mostrador (Venta · Inventario · Reportes · Cierre) y volver la plataforma web la administradora (Terceros y finanzas, Despiece, Usuarios, Reportes completos), reusando `core` sin reescribir reglas, con UI/UX consistente (cabecera icono+título y menú de perfil en ambos).

**Architecture:** El POS pierde 8 vistas del rail; su dominio migra a la web vía endpoints FastAPI respaldados por los mismos servicios de `core` con repositorios Postgres nuevos (patrón `repos_pg.py`). El front React solo pinta. Cinco fases con prefijo de task único cada una: `SHELL`, `DEVOL`, `TERC`, `DESP`, `ADMIN`.

**Tech Stack:** POS: Python 3.11, PySide6/Qt6, SQLite, pytest, qt-material. Web: FastAPI + psycopg (Postgres/Supabase) reusando `pos-core`, React + TypeScript + Tailwind v4, Supabase Auth (JWT ES256).

## Global Constraints

- Reusar `core` siempre; **prohibido** reescribir reglas de negocio en TypeScript o duplicarlas en la UI Qt. Si una regla vive hoy en la UI Qt, bajarla a `core` antes de exponerla en web.
- No acceder a SQL fuera de los adaptadores de repositorio (`repos_pg.py` en el backend; adaptadores SQLite en el POS).
- IDs de task con prefijo por fase (`SHELL.N`, `DEVOL.N`, `TERC.N`, `DESP.N`, `ADMIN.N`); en TodoWrite usar el ID con prefijo completo, nunca el número suelto.
- Gate por fase antes de cerrarla: POS `python -m pytest -q` verde; backend `pytest` con `TEST_DB_URL` verde; front `tsc -b` + `npm run build` + gate `impeccable` limpio.
- Migraciones nuevas se aplican **también a la BD real de Supabase** (`SUPABASE_DB_URL`), no solo a la BD de tests (aprendizaje NUBE2).
- Al cerrar cada fase, actualizar la fila correspondiente en `docs/README-pos.md`.
- Nombres de dominio en español. Tests `test_*.py`, estructura espejo por módulo.
- Auth web: routers de administración usan `Depends(admin_web)`; lecturas de dashboard/reportes usan `Depends(usuario_web)`.

---

# Fase A — Shell & UX base (`SHELL`)

Toca solo UI en ambos repos. No mueve lógica. Deja el patrón de cabecera icono+título y el menú de perfil que las demás fases reutilizan.

## Estructura de archivos (Fase A)

- Modify `src/caja/widgets.py` — nuevos widgets `CabeceraVista` y `BotonRail` con etiqueta.
- Modify `src/caja/ventana_principal.py` — header superior (cabecera + menú de perfil), rail icono+etiqueta, quitar botón suelto de contraseña.
- Modify `src/caja/recursos/iconos/` — agregar `perfil.svg` (los 4 del rail ya existen).
- Test `tests/caja/test_shell.py` — cabecera refleja la vista activa; perfil expone acciones.
- Modify `frontend/src/App.tsx` — sidebar agrupada + header con perfil.
- Create `frontend/src/ui/Sidebar.tsx` — navegación lateral agrupada.
- Create `frontend/src/ui/CabeceraVista.tsx` — icono + título por vista.
- Create `frontend/src/ui/MenuPerfil.tsx` — email + cambiar contraseña + salir.

### Task SHELL.1: Widget `CabeceraVista` (caja/widgets.py)

**Files:**
- Modify: `src/caja/widgets.py`
- Test: `tests/caja/test_shell.py`

**Interfaces:**
- Produces: `class CabeceraVista(QFrame)` con `__init__(self, ruta_icono: str, titulo: str)` y método `set_vista(self, ruta_icono: str, titulo: str) -> None`. Expone `self._titulo: QLabel` (objectName `"titulo-vista"`) y un `QLabel` de icono (objectName `"icono-vista"`).

- [ ] **Step 1: Write the failing test**

```python
# tests/caja/test_shell.py
from PySide6.QtWidgets import QApplication
from caja.widgets import CabeceraVista
from caja.tema import icono

app = QApplication.instance() or QApplication([])

def test_cabecera_muestra_titulo_y_cambia_de_vista():
    cab = CabeceraVista(icono("venta"), "Venta")
    assert cab._titulo.text() == "Venta"
    cab.set_vista(icono("cierre"), "Cierre")
    assert cab._titulo.text() == "Cierre"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/caja/test_shell.py::test_cabecera_muestra_titulo_y_cambia_de_vista -v`
Expected: FAIL con `ImportError: cannot import name 'CabeceraVista'`.

- [ ] **Step 3: Implement `CabeceraVista`**

```python
# añadir a src/caja/widgets.py (importar QHBoxLayout, QPixmap ya está)
from PySide6.QtWidgets import QHBoxLayout  # agregar al import de QtWidgets

class CabeceraVista(QFrame):
    """Franja superior de cada vista: icono distintivo + título legible."""

    def __init__(self, ruta_icono: str, titulo: str) -> None:
        super().__init__()
        self.setObjectName("cabecera-vista")
        self._icono = QLabel()
        self._icono.setObjectName("icono-vista")
        self._titulo = QLabel(titulo)
        self._titulo.setObjectName("titulo-vista")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.addWidget(self._icono)
        layout.addWidget(self._titulo)
        layout.addStretch(1)
        self.set_vista(ruta_icono, titulo)

    def set_vista(self, ruta_icono: str, titulo: str) -> None:
        self._icono.setPixmap(QIcon(ruta_icono).pixmap(QSize(22, 22)))
        self._titulo.setText(titulo)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/caja/test_shell.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/caja/widgets.py tests/caja/test_shell.py
git commit -m "feat(SHELL.1): CabeceraVista icono+título (caja/widgets)"
```

### Task SHELL.2: `BotonRail` con etiqueta bajo el icono (caja/widgets.py)

**Files:**
- Modify: `src/caja/widgets.py:165-176`
- Test: `tests/caja/test_shell.py`

**Interfaces:**
- Consumes: `BotonRail(ruta_icono, tooltip)`.
- Produces: `BotonRail` muestra texto bajo el icono; el texto es `tooltip`.

- [ ] **Step 1: Write the failing test**

```python
def test_boton_rail_muestra_etiqueta():
    from caja.widgets import BotonRail
    from PySide6.QtCore import Qt
    b = BotonRail(icono("venta"), "Venta")
    assert b.text() == "Venta"
    assert b.toolButtonStyle() == Qt.ToolButtonTextUnderIcon
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/caja/test_shell.py::test_boton_rail_muestra_etiqueta -v`
Expected: FAIL (`text()` vacío / estilo IconOnly).

- [ ] **Step 3: Modificar `BotonRail`**

Reemplazar el cuerpo de `__init__` de `BotonRail` (src/caja/widgets.py:168-176):

```python
    def __init__(self, ruta_icono: str, tooltip: str) -> None:
        super().__init__()
        self.setObjectName("rail")
        self.setCheckable(True)
        self.setToolTip(tooltip)
        self.setText(tooltip)
        self.setIcon(QIcon(ruta_icono))
        self.setIconSize(QSize(24, 24))
        self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/caja/test_shell.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/caja/widgets.py tests/caja/test_shell.py
git commit -m "feat(SHELL.2): rail icono+etiqueta (caja/widgets)"
```

### Task SHELL.3: Icono `perfil.svg` (recursos)

**Files:**
- Create: `src/caja/recursos/iconos/perfil.svg`

- [ ] **Step 1: Crear el SVG** (silueta simple, hereda `currentColor`)

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
     stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="12" cy="8" r="4"/>
  <path d="M4 20c0-4 4-6 8-6s8 2 8 6"/>
</svg>
```

- [ ] **Step 2: Commit**

```bash
git add src/caja/recursos/iconos/perfil.svg
git commit -m "feat(SHELL.3): icono perfil (caja/recursos)"
```

### Task SHELL.4: Header superior en `VentanaPrincipal` (cabecera + menú de perfil)

**Files:**
- Modify: `src/caja/ventana_principal.py`
- Test: `tests/caja/test_shell.py`

**Interfaces:**
- Consumes: `CabeceraVista`, `_DEFINICION` (ahora con título e icono por vista).
- Produces: `VentanaPrincipal` con `self._cabecera: CabeceraVista` actualizada en `_ir_a`, y un `QToolButton` de perfil con `QMenu` (acciones "Cambiar mi contraseña", "Cerrar sesión").

- [ ] **Step 1: Write the failing test**

```python
def test_cabecera_sigue_a_la_vista_activa(contexto_demo):  # fixture existente que arma ContextoApp
    from caja.ventana_principal import VentanaPrincipal
    win = VentanaPrincipal(contexto_demo)
    win._ir_a(0)
    assert win._cabecera._titulo.text() == "Venta"
    # la última vista del rail visible es Cierre en el POS reenfocado
    idx_cierre = [i for i, p in enumerate(win._pantallas)
                  if p.__class__.__name__ == "PantallaCierre"][0]
    win._ir_a(idx_cierre)
    assert win._cabecera._titulo.text() == "Cierre"

def test_perfil_expone_cambiar_password_y_cerrar_sesion(contexto_demo):
    from caja.ventana_principal import VentanaPrincipal
    win = VentanaPrincipal(contexto_demo)
    textos = [a.text() for a in win._menu_perfil.actions()]
    assert "Cambiar mi contraseña" in textos
    assert "Cerrar sesión" in textos
```

> Si no existe `contexto_demo`, reusar el fixture con que se construye `VentanaPrincipal` en los tests actuales de caja (buscar en `tests/caja/`); si no hay ninguno, crear uno mínimo en `tests/caja/conftest.py` que arme `ContextoApp` en `:memory:` con `sembrar_admin`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/caja/test_shell.py -k "cabecera_sigue or perfil_expone" -v`
Expected: FAIL (`_cabecera`/`_menu_perfil` no existen).

- [ ] **Step 3: Implementar header en `VentanaPrincipal`**

Cambiar `_DEFINICION` para llevar título propio (ya no reusar tooltip como icono ambiguo) y envolver el `_stack` en un contenedor vertical con la cabecera arriba. Añadir el `QToolButton` de perfil en la cabecera. Reemplazar el botón suelto de contraseña (líneas 77-81) por el menú de perfil.

```python
# _DEFINICION: (icono, titulo, factory, permiso) — icono distinto por vista
_DEFINICION = [
    ("venta", "Venta", PantallaVenta, None),
    ("inventario", "Inventario", PantallaInventario, None),
    ("reportes", "Reportes", PantallaReportes, None),
    ("cierre", "Cierre", PantallaCierre, None),
]
# (Clientes/Proveedores/Compras/Cuentas/Gastos/Despiece/Devoluciones/Usuarios salen
#  del rail en sus fases; aquí ya se listan solo las 4 finales.)
```

```python
# en __init__, tras construir el rail y el stack:
from PySide6.QtWidgets import QToolButton, QMenu, QWidget, QVBoxLayout
from caja.widgets import CabeceraVista

self._cabecera = CabeceraVista(icono(_DEFINICION[0][0]), _DEFINICION[0][1])
self._boton_perfil = QToolButton()
self._boton_perfil.setObjectName("perfil")
self._boton_perfil.setIcon(icono_qicon("perfil"))  # QIcon(icono("perfil"))
self._boton_perfil.setPopupMode(QToolButton.InstantPopup)
self._menu_perfil = QMenu(self._boton_perfil)
self._menu_perfil.addAction("Cambiar mi contraseña", self._cambiar_password)
self._menu_perfil.addAction("Cerrar sesión", self.close)
self._boton_perfil.setMenu(self._menu_perfil)
# insertar el botón de perfil en la cabecera (a la derecha):
self._cabecera.layout().addWidget(self._boton_perfil)

cuerpo = QWidget()
cuerpo_lay = QVBoxLayout(cuerpo)
cuerpo_lay.setContentsMargins(0, 0, 0, 0)
cuerpo_lay.addWidget(self._cabecera)
cuerpo_lay.addWidget(self._stack, 1)
# central: rail | cuerpo   (el cuerpo reemplaza al _stack directo)
layout.addWidget(rail)
layout.addWidget(cuerpo, 1)
```

En `_ir_a`, tras fijar el índice, actualizar la cabecera con el `_DEFINICION` de la vista visible:

```python
    def _ir_a(self, indice: int) -> None:
        self._stack.setCurrentIndex(indice)
        ic, titulo, _f, _p = self._visibles[indice]
        self._cabecera.set_vista(icono(ic), titulo)
        pantalla = self._pantallas[indice]
        if hasattr(pantalla, "al_mostrar"):
            pantalla.al_mostrar()
        self._refrescar_estado()
```

Guardar `self._visibles = visibles` al construir el rail. Eliminar el bloque del botón suelto de contraseña (antiguas líneas 77-81).

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/caja/test_shell.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/caja/ventana_principal.py tests/caja/
git commit -m "feat(SHELL.4): header cabecera+perfil en VentanaPrincipal, rail reenfocado a 4 vistas"
```

### Task SHELL.5: Estilo de cabecera/perfil/rail (marca.qss)

**Files:**
- Modify: `src/caja/marca.qss`

- [ ] **Step 1: Añadir reglas** para `#cabecera-vista` (fondo `#card`, borde inferior), `#titulo-vista` (tipografía grande), `#icono-vista`, `QToolButton#perfil` (touch target ≥40px) y ajustar `QToolButton#rail` para texto bajo icono (ancho ~72). Verificar visualmente con `python -m caja`.

- [ ] **Step 2: Commit**

```bash
git add src/caja/marca.qss
git commit -m "style(SHELL.5): cabecera, perfil y rail con etiqueta (marca.qss)"
```

### Task SHELL.6: Sidebar agrupada + header web (`App.tsx`, `ui/Sidebar.tsx`, `ui/CabeceraVista.tsx`, `ui/MenuPerfil.tsx`)

**Files:**
- Create: `frontend/src/ui/Sidebar.tsx`
- Create: `frontend/src/ui/CabeceraVista.tsx`
- Create: `frontend/src/ui/MenuPerfil.tsx`
- Modify: `frontend/src/ui/index.ts` (exportar los tres)
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Produces:
  - `Sidebar({ grupos, vista, onVista })` donde `grupos: { titulo: string; items: { id: string; etiqueta: string; icono: string }[] }[]`.
  - `CabeceraVista({ icono, titulo }: { icono: string; titulo: string })`.
  - `MenuPerfil({ email, onSalir }: { email: string; onSalir: () => void })` con acción "Cambiar contraseña" (`supabase.auth.updateUser` o enlace a recuperación) y "Salir".

- [ ] **Step 1: Crear `Sidebar.tsx`** (nav lateral, dos grupos, ítem activo en rojo de marca)

```tsx
type Item = { id: string; etiqueta: string; icono: string };
type Grupo = { titulo: string; items: Item[] };
export function Sidebar({ grupos, vista, onVista }:
  { grupos: Grupo[]; vista: string; onVista: (id: string) => void }) {
  return (
    <nav className="w-56 shrink-0 flex flex-col gap-6">
      {grupos.map((g) => (
        <div key={g.titulo} className="flex flex-col gap-1">
          <p className="eyebrow px-2">{g.titulo}</p>
          {g.items.map((it) => {
            const on = vista === it.id;
            return (
              <button key={it.id} onClick={() => onVista(it.id)}
                className={`flex items-center gap-2 min-h-[44px] px-3 rounded-pill text-left transition-colors
                  ${on ? "bg-marca text-white" : "text-tinta-2 hover:bg-superficie-2"}`}>
                <span aria-hidden>{it.icono}</span>{it.etiqueta}
              </button>
            );
          })}
        </div>
      ))}
    </nav>
  );
}
```

- [ ] **Step 2: Crear `CabeceraVista.tsx` y `MenuPerfil.tsx`** (icono emoji + `<h1>` de título; perfil con email, cambiar contraseña y Salir reusando `Boton`).

- [ ] **Step 3: Reescribir `App.tsx`** para usar `Sidebar` + `CabeceraVista` + `MenuPerfil`, con los grupos:

```tsx
const GRUPOS = [
  { titulo: "Operación & análisis", items: [
    { id: "inicio", etiqueta: "Inicio", icono: "🏠" },
    { id: "reportes", etiqueta: "Reportes", icono: "📊" },
    { id: "inventario", etiqueta: "Inventario", icono: "📦" },
    { id: "catalogo", etiqueta: "Catálogo", icono: "🏷️" },
  ]},
  { titulo: "Administración", items: [
    { id: "terceros", etiqueta: "Terceros y finanzas", icono: "👥" },
    { id: "despiece", etiqueta: "Despiece", icono: "🔪" },
    { id: "usuarios", etiqueta: "Usuarios", icono: "🔐" },
  ]},
];
```

Layout: `<div className="flex gap-6 ...">` con `<Sidebar/>` y una columna que arriba tiene `<CabeceraVista/>` + `<MenuPerfil/>` y debajo el contenido según `vista`. Las vistas nuevas (`terceros`, `despiece`, `usuarios`, `reportes`) muestran por ahora un placeholder "En construcción" que las fases C/D/E reemplazan.

- [ ] **Step 4: Verificar**

Run (en `frontend/`): `npx tsc -b && npm run build`
Expected: sin errores.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/ui/ frontend/src/App.tsx
git commit -m "feat(SHELL.6): sidebar agrupada, cabecera icono+título y menú de perfil (web)"
```

### Task SHELL.7: Gate Fase A + README

- [ ] POS: `python -m pytest -q` (verde). Web: `npx tsc -b && npm run build`. Ejecutar el gate `impeccable` del front si aplica.
- [ ] Actualizar en `docs/README-pos.md` una fila nueva (epic `SHELL`): shell y UX base en POS+web.
- [ ] Commit: `docs(SHELL.7): cierre Fase A (shell & UX base)`.

---

# Fase B — Devolución dentro de Venta (`DEVOL`)

La capacidad de devolución ya vive en `core` + `PantallaDevoluciones`. Aquí se integra como acción del flujo de Venta y se retira la vista suelta (ya fuera del rail tras SHELL.4; ahora se elimina el archivo y su import).

## Estructura de archivos (Fase B)

- Modify: `src/caja/pantalla_venta.py` — botón/acción "Devolución" que abre el diálogo de devolución sobre una factura.
- Create: `src/caja/dialogos/dialogo_devolucion.py` — diálogo que reusa el servicio de devoluciones (extraído de `PantallaDevoluciones`).
- Delete: `src/caja/pantalla_devoluciones.py` (tras mover la lógica de UI al diálogo).
- Modify: `src/caja/ventana_principal.py` — quitar import de `PantallaDevoluciones`.
- Test: `tests/caja/test_dialogo_devolucion.py`.

### Task DEVOL.1: Extraer `DialogoDevolucion` desde `PantallaDevoluciones`

**Files:**
- Create: `src/caja/dialogos/dialogo_devolucion.py`
- Test: `tests/caja/test_dialogo_devolucion.py`
- Read (referencia): `src/caja/pantalla_devoluciones.py`, `src/core/servicio_venta.py` (método de devolución/anulación con reembolso).

**Interfaces:**
- Produces: `class DialogoDevolucion(QDialog)` con `__init__(self, ctx, parent=None)`; busca una venta por id/factura, lista sus líneas, permite marcar cantidades a devolver y confirma llamando al mismo servicio que usaba `PantallaDevoluciones`. Emite/retorna el resultado y refresca el arqueo (señal `caja_cambiada` si aplica).

- [ ] **Step 1: Leer `pantalla_devoluciones.py`** y localizar el servicio/método de dominio que ejecuta la devolución con reembolso (no reimplementar reglas: reusar el mismo `Servicio...`).

- [ ] **Step 2: Write the failing test** (busca factura, devuelve una línea parcial, verifica que repone stock y netea caja usando el servicio real sobre `:memory:`).

```python
# tests/caja/test_dialogo_devolucion.py — esqueleto; completar con el fixture de contexto
def test_devolucion_parcial_desde_dialogo(contexto_demo, venta_registrada):
    from caja.dialogos.dialogo_devolucion import DialogoDevolucion
    dlg = DialogoDevolucion(contexto_demo)
    dlg.cargar_factura(venta_registrada.id)
    dlg.marcar_devolucion(linea_idx=0, cantidad=1)
    resultado = dlg.confirmar()
    assert resultado.reembolso > 0
```

- [ ] **Step 3: Implementar `DialogoDevolucion`** moviendo la composición de UI de `PantallaDevoluciones` a un `QDialog` y delegando la regla al servicio de `core`.

- [ ] **Step 4: Run tests** → PASS.

- [ ] **Step 5: Commit** `feat(DEVOL.1): DialogoDevolucion reusa servicio de devolución (caja/dialogos)`.

### Task DEVOL.2: Acción "Devolución" en `PantallaVenta`

**Files:**
- Modify: `src/caja/pantalla_venta.py`
- Test: `tests/caja/test_pantalla_venta.py` (o el existente de venta)

**Interfaces:**
- Consumes: `DialogoDevolucion(ctx)`.
- Produces: `PantallaVenta` tiene un botón "Devolución" que abre `DialogoDevolucion`; al aceptar, refresca estado de caja.

- [ ] **Step 1: Write the failing test** (la pantalla expone `self._boton_devolucion` y al dispararlo instancia el diálogo).
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implementar** el botón + slot que abre el diálogo y emite `caja_cambiada`.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat(DEVOL.2): acción Devolución dentro de Venta (caja/pantalla_venta)`.

### Task DEVOL.3: Eliminar `PantallaDevoluciones`

**Files:**
- Delete: `src/caja/pantalla_devoluciones.py`
- Modify: `src/caja/ventana_principal.py` (quitar el import ya sin uso)
- Delete/-adjust: tests que instancien `PantallaDevoluciones` (migrarlos a `DialogoDevolucion`).

- [ ] **Step 1:** Buscar referencias: `grep -rn PantallaDevoluciones src tests`.
- [ ] **Step 2:** Eliminar el archivo y el import; migrar/asserts de tests al diálogo.
- [ ] **Step 3: Run** `python -m pytest -q` → verde.
- [ ] **Step 4: Commit** `refactor(DEVOL.3): elimina PantallaDevoluciones (integrada en Venta)`.

### Task DEVOL.4: Gate Fase B + README

- [ ] `python -m pytest -q` verde. Actualizar fila `DEVOL` en README-pos.md. Commit `docs(DEVOL.4): cierre Fase B`.

---

# Fase C — Terceros y finanzas en web + salida del POS (`TERC`)

Mueve Clientes · Proveedores · Compras · Gastos · Cuentas (CxC/CxP) a la web reusando los servicios de `core`, y los retira del POS (Venta conserva selector/alta rápida de cliente).

## Patrón de referencia del backend (verificado)

Los repos Postgres implementan los puertos de `core` acotados por `almacen_id` cuando aplica (ver `app/repos_pg.py`). Los routers usan `APIRouter(prefix=..., dependencies=[Depends(admin_web)])`, `with conectar() as conn:` y reusan el `Servicio...` de `core`. Este es el molde de **cada** task de backend de esta fase:

```python
# app/<recurso>.py
from fastapi import APIRouter, Depends
from app.auth import admin_web
from app.db import conectar
from app.repos_pg_terceros import Repositorio<Recurso>PG
from core.servicio_<recurso> import Servicio<Recurso>

router = APIRouter(prefix="/<recurso>", dependencies=[Depends(admin_web)])

@router.get("")
def listar() -> list[dict]:
    with conectar() as conn:
        svc = Servicio<Recurso>(Repositorio<Recurso>PG(conn))
        return [ _dto(x) for x in svc.listar() ]
```

**Antes de cada repo**, leer el servicio de `core` correspondiente para copiar la firma exacta del puerto que espera (`core/servicio_clientes.py`, `servicio_proveedores.py`, `servicio_compras.py`, `servicio_gastos.py`, `servicio_cuentas_cobrar.py`, `servicio_cuentas_pagar.py`) y las entidades en `core/entidades.py`. **No** inventar métodos: el repo implementa el puerto que el servicio ya declara.

## Estructura de archivos (Fase C)

- Create: `backend/app/repos_pg_terceros.py` — `RepositorioClientesPG`, `RepositorioProveedoresPG`, `RepositorioComprasPG`, `RepositorioGastosPG`, `RepositorioCuentasCobrarPG`, `RepositorioCuentasPagarPG`.
- Create: `backend/app/terceros.py` — routers `/clientes`, `/proveedores`, `/compras`, `/gastos`, `/cuentas`.
- Modify: `backend/app/main.py` — `include_router` de los nuevos.
- Create: `backend/migraciones/00X_terceros.sql` — tablas que la nube aún no tenga (clientes, proveedores, compras/lineas, gastos/categorias, abonos/pagos). Revisar cuáles ya existen antes de crear.
- Create: `backend/tests/test_terceros.py` — integración contra Postgres de test.
- Create: `frontend/src/terceros/Terceros.tsx` — hub con sub-pestañas.
- Create: `frontend/src/terceros/{Clientes,Proveedores,Compras,Gastos,Cuentas}.tsx`.
- Modify: `frontend/src/api.ts` — funciones de fetch por recurso.
- Modify: `frontend/src/App.tsx` — vista `terceros` deja de ser placeholder.
- POS: Modify `src/caja/ventana_principal.py` (ya no importa las 5 pantallas), Delete `pantalla_clientes.py`, `pantalla_proveedores.py`, `pantalla_compras.py`, `pantalla_gastos.py`, `pantalla_cuentas.py` (conservar en Venta el selector/alta rápida de cliente que hoy ya vive en `pantalla_venta.py`).

### Migración y esquema (una sola vez)

### Task TERC.1: Migración `00X_terceros.sql`

**Files:**
- Read: `backend/migraciones/` (numerar la siguiente; ver cuáles tablas ya existen — `productos`, `ventas`, `ubicaciones`, `inventario_movimientos` ya están).
- Create: `backend/migraciones/00X_terceros.sql`

- [ ] **Step 1:** Inventariar tablas existentes (`\dt` o revisar migraciones previas). Definir solo las faltantes: `clientes`, `proveedores`, `compras`, `compra_lineas`, `gastos`, `categorias_gasto`, `abonos_cliente`, `pagos_proveedor`, con `almacen_id`/`local_id` donde el modelo del POS lo tenga. Copiar tipos desde el esquema SQLite del POS (`scripts/` migraciones) para paridad.
- [ ] **Step 2:** Aplicar a la BD de test (`TEST_DB_URL`) vía `migraciones_runner` y a la **BD real** (`SUPABASE_DB_URL`).
- [ ] **Step 3: Commit** `feat(TERC.1): migración tablas de terceros y finanzas (backend/migraciones)`.

### Tasks TERC.2 – TERC.6: Repos + endpoints por recurso (uno por task)

Cada recurso es un task independiente con el mismo ciclo TDD. Para **cada** uno: leer el servicio de `core`, escribir un test de integración que instancie el servicio con el repo PG contra Postgres de test, verlo fallar, implementar el repo+endpoint, verlo pasar, commitear.

- [ ] **TERC.2: Clientes** — `RepositorioClientesPG` (implementa el puerto de `ServicioClientes`), router `/clientes` (GET listar, POST crear, PUT editar). Test: crear cliente vía servicio y releer. Files: `app/repos_pg_terceros.py`, `app/terceros.py`, `backend/tests/test_terceros.py`. Commit `feat(TERC.2): clientes web (repo PG + endpoint) reusa ServicioClientes`.
- [ ] **TERC.3: Proveedores** — `RepositorioProveedoresPG` + `/proveedores`. Reusa `ServicioProveedores`. Commit `feat(TERC.3): proveedores web reusa ServicioProveedores`.
- [ ] **TERC.4: Compras** — `RepositorioComprasPG` + `/compras` (POST registra compra que alimenta stock/costo vía `ServicioCompras`; GET lista). Ojo: registrar compra afecta inventario — verificar que use el mismo camino que el POS (movimientos/stock). Commit `feat(TERC.4): compras web reusa ServicioCompras`.
- [ ] **TERC.5: Gastos** — `RepositorioGastosPG` + `/gastos` (registrar/listar + categorías admin). Reusa `ServicioGastos`. Commit `feat(TERC.5): gastos web reusa ServicioGastos`.
- [ ] **TERC.6: Cuentas** — `RepositorioCuentasCobrarPG` + `RepositorioCuentasPagarPG` + `/cuentas` (saldos por cliente/proveedor, registrar abono/pago). Reusa `ServicioCuentasCobrar`/`ServicioCuentasPagar`. Nota: en la web no hay "caja"; el abono/pago en efectivo que en el POS pasa por caja debe modelarse como registro sin sesión de caja (o marcado para conciliación). Decidir en el test: la web registra el abono/pago contra la cuenta, sin tocar arqueo. Commit `feat(TERC.6): cuentas CxC/CxP web reusa servicios de core`.

> Cada task TERC.2–.6 termina con `include_router` en `main.py` y su bloque de test verde (`pytest backend/tests/test_terceros.py -k <recurso>`).

### Task TERC.7: Front — hub `Terceros` con sub-pestañas

**Files:**
- Create: `frontend/src/terceros/Terceros.tsx` + `Clientes.tsx`, `Proveedores.tsx`, `Compras.tsx`, `Gastos.tsx`, `Cuentas.tsx`
- Modify: `frontend/src/api.ts`, `frontend/src/App.tsx`

**Interfaces:**
- Consumes: endpoints `/clientes`, `/proveedores`, `/compras`, `/gastos`, `/cuentas`.
- Produces: `Terceros()` con sub-pestañas internas (mismo patrón chip que hoy, pero anidado) que montan cada sub-vista; cada sub-vista es una tabla + formulario sobre los primitivos `Tarjeta/Campo/Boton`.

- [ ] **Step 1:** `api.ts`: funciones `listarClientes()`, `crearCliente(...)`, etc., usando el fetch autenticado ya existente (revisar cómo `Catalogo.tsx`/`Inventario.tsx` llaman al backend con el token de Supabase).
- [ ] **Step 2:** Implementar `Terceros.tsx` con sub-tabs y las 5 sub-vistas (tabla + alta/edición). Reusar estilos de `Inventario.tsx`/`Catalogo.tsx`.
- [ ] **Step 3:** En `App.tsx`, `vista === "terceros"` renderiza `<Terceros/>`.
- [ ] **Step 4:** `npx tsc -b && npm run build` sin errores; verificación manual en navegador.
- [ ] **Step 5: Commit** `feat(TERC.7): hub Terceros y finanzas con sub-pestañas (web)`.

### Task TERC.8: Retirar Clientes/Proveedores/Compras/Gastos/Cuentas del POS

**Files:**
- Delete: `src/caja/pantalla_clientes.py`, `pantalla_proveedores.py`, `pantalla_compras.py`, `pantalla_gastos.py`, `pantalla_cuentas.py`
- Modify: `src/caja/ventana_principal.py` (quitar imports; ya no están en `_DEFINICION`)
- Modify/-migrar tests que instancien esas pantallas.
- Verify: el selector y alta rápida de cliente en `pantalla_venta.py` siguen funcionando (no dependían de `PantallaClientes`).

- [ ] **Step 1:** `grep -rn "Pantalla\(Clientes\|Proveedores\|Compras\|Gastos\|Cuentas\)" src tests`.
- [ ] **Step 2:** Eliminar archivos e imports; migrar tests de CRUD a los servicios de `core` (siguen existiendo) o retirarlos si su cobertura pasa al backend.
- [ ] **Step 3: Run** `python -m pytest -q` → verde (incluye venta con selección de cliente).
- [ ] **Step 4: Commit** `refactor(TERC.8): retira vistas de terceros/finanzas del POS (viven en web)`.

### Task TERC.9: Gate Fase C + README

- [ ] Backend `pytest` (TEST_DB_URL) verde; POS `pytest` verde; front build + impeccable. Migración aplicada a BD real. Actualizar fila `TERC` en README-pos.md. Commit `docs(TERC.9): cierre Fase C`.

---

# Fase D — Despiece en web + salida del POS (`DESP`)

### Estructura de archivos (Fase D)

- Read: `src/core/servicio_despiece.py`, `src/caja/pantalla_despiece.py`, `src/core/calculos.py` (`prorratear_costeo_despiece`).
- Create: `backend/app/repos_pg_despiece.py`, `backend/app/despiece.py`, `backend/tests/test_despiece.py`.
- Create: `frontend/src/despiece/Despiece.tsx`; Modify `api.ts`, `App.tsx`.
- Migración: `backend/migraciones/00Y_despiece.sql` si el despiece persiste tablas propias (revisar el modelo del POS; puede reusar movimientos de inventario + costeo).
- Delete: `src/caja/pantalla_despiece.py`; Modify `ventana_principal.py`.

### Task DESP.1: Repo PG + endpoint de despiece

- [ ] Leer `servicio_despiece.py` para el puerto exacto. Test de integración: prorrateo del costo del canal entre cortes reusando `ServicioDespiece`/`prorratear_costeo_despiece` (la regla ya vive en `core`; el backend solo persiste/expone). Implementar `RepositorioDespiecePG` + router `/despiece` con `Depends(admin_web)`. `include_router`. Commit `feat(DESP.1): despiece web reusa ServicioDespiece`.

### Task DESP.2: Migración de despiece (si aplica)

- [ ] Solo si el despiece persiste tablas que la nube no tenga. Crear `00Y_despiece.sql`, aplicar a test y BD real. Commit `feat(DESP.2): migración despiece (backend/migraciones)`.

### Task DESP.3: Front `Despiece.tsx`

- [ ] Vista con selección de canal, cortes y costeo resultante; sobre primitivos de marca. `App.tsx`: `vista === "despiece"`. Build verde. Commit `feat(DESP.3): vista Despiece (web)`.

### Task DESP.4: Retirar despiece del POS

- [ ] Delete `src/caja/pantalla_despiece.py` + import en `ventana_principal.py`; migrar tests. `pytest` verde. Commit `refactor(DESP.4): retira Despiece del POS (vive en web)`.

### Task DESP.5: Gate Fase D + README

- [ ] Gates verdes; migración a BD real si hubo. Fila `DESP` en README. Commit `docs(DESP.5): cierre Fase D`.

---

# Fase E — Usuarios + Reportes web completos (`ADMIN`)

Cierra la administración: gestión de usuarios/roles en web y Reportes a paridad con el POS. El POS conserva login y sus reportes.

### Estructura de archivos (Fase E)

- Read: `src/core/servicio_usuarios.py`, `src/core/permisos.py`, `src/core/servicio_reportes.py` (métodos `ventas`, `por_cajero`, `por_categoria`, `facturas`, `por_cajero_de_sesion`, `compras`, `compras_por_proveedor`, `mensual`).
- Create: `backend/app/repos_pg_usuarios.py`, `backend/app/usuarios.py`, `backend/tests/test_usuarios.py`.
- Modify: `backend/app/dashboard.py` (o Create `backend/app/reportes.py`) — endpoints faltantes: facturas, por-cajero-de-sesión, compras, compras-por-proveedor, mensual.
- Create: `frontend/src/usuarios/Usuarios.tsx`; Expand `frontend/src/dashboard/` → `frontend/src/reportes/Reportes.tsx` con todas las pestañas.
- Modify: `api.ts`, `App.tsx`.
- Migración: `backend/migraciones/00Z_usuarios.sql` (tabla `usuarios` con hash de contraseña — reusar `core.seguridad`).
- POS: Delete `src/caja/pantalla_usuarios.py`; Modify `ventana_principal.py` (ya fuera del rail; conserva login/`DialogoLogin`).

### Task ADMIN.1: Migración `usuarios`

- [ ] Crear `00Z_usuarios.sql` (`usuarios`: id, nombre, rol, hash). Aplicar a test y BD real. Commit `feat(ADMIN.1): migración usuarios (backend/migraciones)`.

### Task ADMIN.2: Repo PG + endpoint usuarios/roles

- [ ] Leer `servicio_usuarios.py` + `permisos.py`. Test: crear usuario con rol, verificar hash vía `core.seguridad`, `puede(rol, accion)`. Implementar `RepositorioUsuariosPG` + router `/usuarios` (`Depends(admin_web)`): listar, crear, cambiar rol, reset/cambiar contraseña. Reusa `ServicioUsuarios`. `include_router`. Commit `feat(ADMIN.2): usuarios/roles web reusa ServicioUsuarios`.

### Task ADMIN.3: Endpoints de reportes faltantes

- [ ] En `dashboard.py`/`reportes.py`, exponer los métodos de `ServicioReportes` que el dashboard aún no ofrece: `facturas`, `por_cajero_de_sesion`, `compras`, `compras_por_proveedor`, `mensual`. Reusar el patrón `_reportes(conn, almacen_id)` existente (ampliando los repos PG con lo que esos métodos requieran: `RepositorioComprasPG` de Fase C alimenta `compras`). Tests de integración por método. Commit `feat(ADMIN.3): reportes web a paridad con POS (ServicioReportes)`.

### Task ADMIN.4: Front usuarios + reportes completos

- [ ] `Usuarios.tsx` (tabla + alta + rol + contraseña) y `Reportes.tsx` con pestañas Período·Categoría·Factura·Cajero·Compras·Mensual (reusa charts de marca de `dashboard/charts.ts`). `App.tsx`: `vista === "usuarios"` y `vista === "reportes"`. Build verde. Commit `feat(ADMIN.4): vistas Usuarios y Reportes completos (web)`.

### Task ADMIN.5: Retirar Usuarios del POS

- [ ] Delete `src/caja/pantalla_usuarios.py` + import; conservar `DialogoLogin` y `sembrar_admin`. Migrar tests. `pytest` verde. Commit `refactor(ADMIN.5): retira gestión de Usuarios del POS (login se queda)`.

### Task ADMIN.6: Gate Fase E + README + cierre del programa

- [ ] Todos los gates verdes; migraciones en BD real. Actualizar filas `ADMIN` y el resumen de estado en README-pos.md (POS = Venta·Inventario·Reportes·Cierre; web = Inicio·Reportes·Catálogo·Inventario·Terceros·Despiece·Usuarios). Commit `docs(ADMIN.6): cierre Fase E y del programa de separación POS↔web`.

---

## Self-review (cobertura vs spec)

- POS 12→4 vistas: rail reenfocado en SHELL.4; retiros en TERC.8 (5), DESP.4 (1), ADMIN.5 (1), DEVOL.3 (1) = 8 retiradas. ✓
- Devolución integrada en Venta: DEVOL.1–.3. ✓
- Terceros y finanzas (5 secciones) en web reusando core: TERC.1–.9. ✓
- Despiece en web: DESP.1–.5. ✓
- Usuarios + Reportes completos en web: ADMIN.1–.6. ✓
- UX cabecera icono+título + perfil (POS y web): SHELL.1–.6. ✓
- "Cambiar contraseña" deja de ser vista: SHELL.4 (menú de perfil POS) + SHELL.6 (MenuPerfil web). ✓
- Reusar core, no reescribir: patrón de referencia Fase C + "leer el servicio antes de cada repo" en cada task de backend. ✓
- Migraciones a BD real: TERC.1, DESP.2, ADMIN.1 y cada gate. ✓

## Notas para el ejecutor

- Antes de cada repo PG, **leer el servicio de `core`** y su puerto: el repo implementa esa interfaz, no una inventada.
- Varias tablas ya existen en la nube (`productos`, `ventas`, `ubicaciones`, `inventario_movimientos`); las migraciones de C/D/E crean solo lo faltante — inventariar primero.
- El fixture de contexto del POS para tests de UI: reusar el que ya construye `VentanaPrincipal`/pantallas en `tests/caja/`; si no existe, crear `tests/caja/conftest.py` mínimo (`ContextoApp` en `:memory:` + `sembrar_admin`).
- Para el fetch autenticado del front, copiar el patrón de `Catalogo.tsx`/`Inventario.tsx` (token JWT de Supabase en `Authorization: Bearer`).
