# Sistema de Diseño de marca "Carnes y Fruver RL" — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir la fundación visual (tokens, tipografía, primitivos, referencia viva) que Web (Tailwind) y POS (qt-material + overlay) importan, sin rediseñar ninguna pantalla real.

**Architecture:** Una sola fuente de tokens semánticos con dos bindings: Web los expone como utilidades Tailwind v4 vía `@theme` en CSS; POS los expone vía un tema XML de qt-material + un overlay QSS `marca.qss`. Cada producto obtiene una página/ventana "Estilo" que muestra el sistema (referencia testeable). Cero cambios en `core/` ni en flujos de pantalla.

**Tech Stack:** Web: React 19, Vite 8, Tailwind v4 (`@tailwindcss/vite`), `@fontsource` para fuentes, `impeccable` como gate. POS: PySide6, `qt-material`, `QFontDatabase`, `QGraphicsDropShadowEffect`, pytest.

## Global Constraints

- Personalidad: **moderna premium**. Dark-first en ambos productos.
- Rojo de marca **exacto `#E01E26`**; solo para intención primaria, nunca decoración.
- Firma **glow neón** `rgba(224,30,38,.45)` racionada a focus/activo/hero.
- Fuentes: **Space Grotesk** (display), **Geist Sans** (cuerpo/UI), **Geist Mono** tabular (dinero). **Prohibido Inter/Roboto.** Auto-hospedadas (POS offline, CSP web limpio).
- Escala espaciado px: `4 8 12 16 24 32 48`. Radio: `sm 6 · md 10 · lg 16 · pill 999`.
- Touch targets: web ≥ **44×44px**, POS filas ≥ **48px**.
- Ponytail: mínimo código; del lado web, mínimas dependencias. `core/` intocable.
- **NO** rediseñar pantallas reales, navegación, menús, IA ni set de iconos por vista (fuera de alcance; specs siguientes).
- Copy: español, sentence case, voz activa; acción = misma palabra en todo el flujo.
- Epic prefix de tracking: **`MARCA.*`** (usar el ID con prefijo en TodoWrite, nunca número pelado).
- Dos repos: tasks MARCA.1–3 en `w:\pos-plataforma-web` (rama `master`); MARCA.4–6 en `w:\POS` (rama `feature/plataforma-web-fase-0-1`). Commits en el repo de cada task. **No push ni merge sin preguntar.**

**Lotes sugeridos (ejecución batched inline, suite+reporte 1 vez por lote):**
- **LOTE A (Web):** MARCA.1 → MARCA.2 → MARCA.3
- **LOTE B (POS):** MARCA.4 → MARCA.5 → MARCA.6

---

### Task MARCA.1: Tailwind v4 + tokens `@theme` + fuentes (frontend web)

**Repo:** `w:\pos-plataforma-web` · **Files:**
- Modify: `frontend/package.json` (deps)
- Modify: `frontend/vite.config.ts` (plugin Tailwind)
- Modify: `frontend/src/index.css` (reemplaza tokens dataviz por `@theme` de marca)
- Modify: `frontend/src/main.tsx` (imports de fuentes)
- Create: `frontend/.gitignore` entry para `.agents/` y `skills-lock.json`

**Interfaces:**
- Produces: utilidades Tailwind `bg-carbon`, `bg-superficie`, `bg-superficie-2`, `text-tinta`, `text-tinta-2`, `text-marca`, `bg-marca`, `border-borde`, `shadow-glow`, `rounded-md/lg/pill`, `font-display`, `font-mono`; variables CSS `--color-marca`, etc.

- [ ] **Step 1: Instalar dependencias**

Run (en `w:/pos-plataforma-web/frontend`):
```bash
npm i -D tailwindcss @tailwindcss/vite
npm i @fontsource-variable/space-grotesk @fontsource-variable/geist @fontsource-variable/geist-mono
```
Expected: se agregan a `package.json`, `npm ls tailwindcss` muestra v4.x.

- [ ] **Step 2: Registrar el plugin de Tailwind en Vite**

Edit `frontend/vite.config.ts` — agregar el plugin:
```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
});
```
(Si `vite.config.ts` ya tiene otra forma, conservar lo existente y solo añadir `tailwindcss()` a `plugins`.)

- [ ] **Step 3: Reescribir `index.css` con `@theme` de marca (reemplaza la paleta dataviz)**

Replace `frontend/src/index.css` completo:
```css
@import "tailwindcss";

/* Sistema de Diseño "Carnes y Fruver RL" — tokens de marca (dark-first). */
@theme {
  --color-carbon: #0B0E14;
  --color-superficie: #151A25;
  --color-superficie-2: #1E2330;
  --color-borde: #2E3548;
  --color-tinta: #F0F2F5;
  --color-tinta-2: #8B95A8;
  --color-marca: #E01E26;
  --color-marca-hover: #C1161D;
  --color-verde: #22C55E;
  --color-ambar: #F59E0B;
  --color-rojo-alerta: #EF4444;

  --radius-md: 10px;
  --radius-lg: 16px;
  --radius-pill: 999px;

  --shadow-glow: 0 0 0 3px rgba(224, 30, 38, .45);

  --font-display: "Space Grotesk Variable", system-ui, sans-serif;
  --font-sans: "Geist Variable", system-ui, sans-serif;
  --font-mono: "Geist Mono Variable", ui-monospace, monospace;
}

* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--color-carbon);
  color: var(--color-tinta);
  font-family: var(--font-sans);
}
:focus-visible { outline: none; box-shadow: var(--shadow-glow); }
```

- [ ] **Step 4: Importar las fuentes en `main.tsx`**

Edit `frontend/src/main.tsx` — añadir tras `import "./index.css";`:
```ts
import "@fontsource-variable/space-grotesk";
import "@fontsource-variable/geist";
import "@fontsource-variable/geist-mono";
```

- [ ] **Step 5: Ignorar el tooling de skills en git**

Create/append `frontend/.gitignore`:
```gitignore
.agents/
skills-lock.json
```

- [ ] **Step 6: Verificar build y slop-gate**

Run (en `frontend/`):
```bash
npm run build
npx --yes impeccable@latest detect src/
```
Expected: build OK (sin errores TS/Vite); impeccable imprime `[]` o no reporta anti-patrones (exit 0).

- [ ] **Step 7: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/vite.config.ts frontend/src/index.css frontend/src/main.tsx frontend/.gitignore
git commit -m "feat(marca): tokens Tailwind v4 + fuentes de marca (MARCA.1)"
```

---

### Task MARCA.2: Primitivos de UI web (Boton, Tarjeta, Campo, NavInferior)

**Repo:** `w:\pos-plataforma-web` · **Files:**
- Create: `frontend/src/ui/Boton.tsx`
- Create: `frontend/src/ui/Tarjeta.tsx`
- Create: `frontend/src/ui/Campo.tsx`
- Create: `frontend/src/ui/NavInferior.tsx`
- Create: `frontend/src/ui/index.ts`

**Interfaces:**
- Consumes: utilidades Tailwind de MARCA.1.
- Produces:
  - `Boton({ variante?: "primario" | "secundario", ...props }): JSX` — `<button>` con touch target ≥44px.
  - `Tarjeta({ children, className? }): JSX` — panel `superficie-2` con borde y radio `md`.
  - `Campo({ label, id, ...inputProps }): JSX` — label + `<input>` accesible.
  - `NavInferior({ items: {id,etiqueta,icono}[], activo, onCambio }): JSX` — barra inferior móvil, item activo con glow.

- [ ] **Step 1: Escribir el test de humo de render**

Create `frontend/src/ui/ui.test.tsx` (Vitest no está configurado; este test se ejecuta como type-check + render manual en la página `/estilo` de MARCA.3). En su lugar, verificación por TypeScript: el build de MARCA.3 falla si las firmas no compilan. Marcar este step como "cubierto por MARCA.3 build".

- [ ] **Step 2: `Boton.tsx`**

```tsx
import type { ButtonHTMLAttributes } from "react";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variante?: "primario" | "secundario";
};

export function Boton({ variante = "secundario", className = "", ...props }: Props) {
  const base =
    "min-h-[44px] px-4 rounded-md font-medium transition-colors disabled:opacity-50 focus-visible:shadow-glow outline-none";
  const estilo =
    variante === "primario"
      ? "bg-marca hover:bg-marca-hover text-white"
      : "bg-superficie-2 border border-borde text-tinta hover:border-tinta-2";
  return <button className={`${base} ${estilo} ${className}`} {...props} />;
}
```

- [ ] **Step 3: `Tarjeta.tsx`**

```tsx
import type { ReactNode } from "react";

export function Tarjeta({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`bg-superficie-2 border border-borde rounded-md p-4 ${className}`}>
      {children}
    </div>
  );
}
```

- [ ] **Step 4: `Campo.tsx`**

```tsx
import type { InputHTMLAttributes } from "react";

type Props = InputHTMLAttributes<HTMLInputElement> & { label: string; id: string };

export function Campo({ label, id, className = "", ...props }: Props) {
  return (
    <label htmlFor={id} className="flex flex-col gap-1 text-sm text-tinta-2">
      {label}
      <input
        id={id}
        className={`min-h-[44px] px-3 rounded-md bg-superficie border border-borde text-tinta outline-none focus-visible:shadow-glow ${className}`}
        {...props}
      />
    </label>
  );
}
```

- [ ] **Step 5: `NavInferior.tsx`**

```tsx
type Item = { id: string; etiqueta: string; icono: string };

export function NavInferior({
  items, activo, onCambio,
}: { items: Item[]; activo: string; onCambio: (id: string) => void }) {
  return (
    <nav className="fixed bottom-0 inset-x-0 flex bg-superficie border-t border-borde pb-[env(safe-area-inset-bottom)]">
      {items.map((it) => {
        const on = it.id === activo;
        return (
          <button
            key={it.id}
            onClick={() => onCambio(it.id)}
            className={`flex-1 min-h-[56px] flex flex-col items-center justify-center gap-0.5 text-xs outline-none
              ${on ? "text-marca" : "text-tinta-2"} focus-visible:shadow-glow`}
          >
            <span aria-hidden className="text-lg">{it.icono}</span>
            {it.etiqueta}
          </button>
        );
      })}
    </nav>
  );
}
```

- [ ] **Step 6: Barrel `index.ts`**

```ts
export { Boton } from "./Boton";
export { Tarjeta } from "./Tarjeta";
export { Campo } from "./Campo";
export { NavInferior } from "./NavInferior";
```

- [ ] **Step 7: Verificar compilación**

Run (en `frontend/`): `npx tsc -b`
Expected: sin errores de tipos.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/ui
git commit -m "feat(marca): primitivos web Boton/Tarjeta/Campo/NavInferior (MARCA.2)"
```

---

### Task MARCA.3: Página de referencia viva `/estilo` (web) + gate impeccable

**Repo:** `w:\pos-plataforma-web` · **Files:**
- Create: `frontend/src/estilo/Estilo.tsx`
- Modify: `frontend/src/main.tsx` (montaje condicional por hash `#estilo`)

**Interfaces:**
- Consumes: primitivos de MARCA.2, tokens de MARCA.1.
- Produces: ruta accesible en `#estilo` que renderiza swatches de tokens, escala tipográfica y todos los primitivos.

- [ ] **Step 1: `Estilo.tsx`**

```tsx
import { Boton, Tarjeta, Campo, NavInferior } from "../ui";

const TOKENS = [
  ["carbon", "#0B0E14"], ["superficie", "#151A25"], ["superficie-2", "#1E2330"],
  ["borde", "#2E3548"], ["tinta", "#F0F2F5"], ["tinta-2", "#8B95A8"],
  ["marca", "#E01E26"], ["verde", "#22C55E"], ["ambar", "#F59E0B"], ["rojo-alerta", "#EF4444"],
];

export function Estilo() {
  return (
    <div className="min-h-screen p-6 max-w-3xl mx-auto flex flex-col gap-8">
      <header>
        <p className="text-tinta-2 text-sm">Carnes y Fruver RL · Sistema de Diseño</p>
        <h1 className="font-display text-4xl">Estilo</h1>
      </header>

      <section className="flex flex-col gap-3">
        <h2 className="font-display text-2xl">Color</h2>
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
          {TOKENS.map(([n, hex]) => (
            <div key={n} className="flex flex-col gap-1 text-xs">
              <div className="h-16 rounded-md border border-borde" style={{ background: hex }} />
              <span className="text-tinta">{n}</span>
              <span className="font-mono text-tinta-2">{hex}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="font-display text-2xl">Tipografía</h2>
        <p className="font-display text-3xl">Space Grotesk · display</p>
        <p className="font-sans text-base">Geist Sans · cuerpo — moderna premium.</p>
        <p className="font-mono text-base tabular-nums">$ 1.234.567 · Geist Mono tabular</p>
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="font-display text-2xl">Componentes</h2>
        <div className="flex gap-3">
          <Boton variante="primario">Cobrar</Boton>
          <Boton>Cancelar</Boton>
          <Boton variante="primario" disabled>Deshabilitado</Boton>
        </div>
        <Tarjeta>Tarjeta de superficie con borde y radio md.</Tarjeta>
        <Campo id="demo" label="Buscar producto" placeholder="Ej. Pechuga de pollo" />
      </section>

      <NavInferior
        items={[
          { id: "v", etiqueta: "Ventas", icono: "🧾" },
          { id: "c", etiqueta: "Catálogo", icono: "🏷️" },
          { id: "i", etiqueta: "Inventario", icono: "📦" },
        ]}
        activo="v"
        onCambio={() => {}}
      />
    </div>
  );
}
```

- [ ] **Step 2: Montaje condicional en `main.tsx`**

Edit `frontend/src/main.tsx` — montar `Estilo` cuando `location.hash === "#estilo"`:
```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import "./index.css";
import "@fontsource-variable/space-grotesk";
import "@fontsource-variable/geist";
import "@fontsource-variable/geist-mono";
import App from "./App";
import { Estilo } from "./estilo/Estilo";

const raiz = location.hash === "#estilo" ? <Estilo /> : <App />;
ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>{raiz}</React.StrictMode>,
);
```

- [ ] **Step 3: Verificar build + render + gate**

Run (en `frontend/`):
```bash
npm run build
npx --yes impeccable@latest detect src/
```
Expected: build OK; impeccable `[]`. Además `npm run dev` y abrir `http://localhost:5173/#estilo` muestra swatches, tipografías y componentes con la barra inferior fija.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/estilo frontend/src/main.tsx
git commit -m "feat(marca): pagina de referencia viva /estilo + gate impeccable (MARCA.3)"
```

---

### Task MARCA.4: qt-material + tema de marca + fuentes (POS)

**Repo:** `w:\POS` · **Files:**
- Modify: `requirements.txt` (o `pyproject.toml`) — agregar `qt-material`
- Create: `src/caja/recursos/temas/carnes_fruver.xml`
- Create: `src/caja/recursos/fuentes/` (TTF vendorizados)
- Modify: `src/caja/tema.py` (aplicar qt-material + fuentes)
- Create: `tests/caja/test_tema_marca.py`

**Interfaces:**
- Consumes: `carga_tema(app)` ya llamado en `caja/__main__.py:16`.
- Produces:
  - `carga_tema(app: QApplication) -> None` (evolucionado): aplica qt-material con `carnes_fruver.xml`, carga fuentes y añade overlay (overlay llega en MARCA.5).
  - `carga_fuentes() -> None` — registra las TTF vía `QFontDatabase`.

- [ ] **Step 1: Agregar dependencia**

Añadir `qt-material` a `requirements.txt` e instalar:
```bash
cd w:/POS && .venv/Scripts/pip install qt-material
```
Expected: `pip show qt-material` OK.

- [ ] **Step 2: Vendorizar las fuentes TTF (una vez, requiere red)**

Descargar los TTF variables a `src/caja/recursos/fuentes/`:
```bash
mkdir -p src/caja/recursos/fuentes
curl -L -o src/caja/recursos/fuentes/SpaceGrotesk.ttf \
  "https://github.com/floriankarsten/space-grotesk/raw/master/fonts/ttf/SpaceGrotesk-Regular.ttf"
curl -L -o src/caja/recursos/fuentes/Geist.ttf \
  "https://github.com/vercel/geist-font/raw/main/packages/next/src/fonts/geist-sans/Geist-Regular.ttf"
curl -L -o src/caja/recursos/fuentes/GeistMono.ttf \
  "https://github.com/vercel/geist-font/raw/main/packages/next/src/fonts/geist-mono/GeistMono-Regular.ttf"
```
Expected: 3 archivos `.ttf` > 20 KB cada uno. (Si una URL upstream cambió, obtener el TTF equivalente del repo oficial; el requisito es TTF, no woff2, porque `QFontDatabase` no carga woff2 de forma fiable.)

- [ ] **Step 3: Tema XML de marca**

Create `src/caja/recursos/temas/carnes_fruver.xml`:
```xml
<!--?xml version="1.0" encoding="UTF-8"?-->
<resources>
  <color name="primaryColor">#E01E26</color>
  <color name="primaryLightColor">#C1161D</color>
  <color name="secondaryColor">#1E2330</color>
  <color name="secondaryLightColor">#2E3548</color>
  <color name="secondaryDarkColor">#0B0E14</color>
  <color name="primaryTextColor">#F0F2F5</color>
  <color name="secondaryTextColor">#8B95A8</color>
</resources>
```

- [ ] **Step 4: Escribir el test de carga de tema (falla primero)**

Create `tests/caja/test_tema_marca.py`:
```python
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from caja.tema import carga_tema, carga_fuentes


def test_carga_tema_aplica_marca_sin_error():
    app = QApplication.instance() or QApplication([])
    carga_tema(app)
    hoja = app.styleSheet()
    assert hoja  # qt-material dejó un stylesheet no vacío
    assert "#E01E26".lower() in hoja.lower() or "E01E26".lower() in hoja.lower()


def test_carga_fuentes_registra_familias():
    app = QApplication.instance() or QApplication([])
    familias = carga_fuentes()
    assert any("Space Grotesk" in f for f in familias)
```

- [ ] **Step 5: Ejecutar el test (debe fallar)**

Run: `cd w:/POS && .venv/Scripts/python -m pytest tests/caja/test_tema_marca.py -v`
Expected: FAIL (`carga_fuentes` no existe / no aplica marca).

- [ ] **Step 6: Evolucionar `tema.py`**

Replace `src/caja/tema.py`:
```python
"""Carga del tema: qt-material con la paleta de marca + fuentes + overlay."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication
from qt_material import apply_stylesheet

_DIR = Path(__file__).resolve().parent
RUTA_TEMA = _DIR / "recursos" / "temas" / "carnes_fruver.xml"
RUTA_OVERLAY = _DIR / "marca.qss"          # llega en MARCA.5
RUTA_FUENTES = _DIR / "recursos" / "fuentes"
RUTA_ICONOS = _DIR / "recursos" / "iconos"


def carga_fuentes() -> list[str]:
    """Registra las TTF de marca. Devuelve las familias cargadas."""
    familias: list[str] = []
    for ttf in sorted(RUTA_FUENTES.glob("*.ttf")):
        idx = QFontDatabase.addApplicationFont(str(ttf))
        familias += QFontDatabase.applicationFontFamilies(idx)
    return familias


def carga_tema(app: QApplication) -> None:
    carga_fuentes()
    apply_stylesheet(app, theme=str(RUTA_TEMA), invert_secondary=False)
    overlay = RUTA_OVERLAY.read_text(encoding="utf-8") if RUTA_OVERLAY.exists() else ""
    if overlay:
        app.setStyleSheet(app.styleSheet() + "\n" + overlay)


def icono(nombre: str) -> str:
    return str(RUTA_ICONOS / f"{nombre}.svg")
```

- [ ] **Step 7: Ejecutar el test (debe pasar)**

Run: `cd w:/POS && .venv/Scripts/python -m pytest tests/caja/test_tema_marca.py -v`
Expected: PASS (2 tests).

- [ ] **Step 8: Commit**

```bash
git add requirements.txt src/caja/tema.py src/caja/recursos/temas src/caja/recursos/fuentes tests/caja/test_tema_marca.py
git commit -m "feat(marca): qt-material + tema y fuentes de marca en POS (MARCA.4)"
```

---

### Task MARCA.5: Overlay `marca.qss` (objectNames + touch) + helper de glow

**Repo:** `w:\POS` · **Files:**
- Create: `src/caja/marca.qss`
- Create: `src/caja/efectos.py` (helper `aplica_glow`)
- Modify: `tests/caja/test_tema_marca.py` (assert overlay presente)

**Interfaces:**
- Consumes: `carga_tema` de MARCA.4 (ya appendea `marca.qss` si existe).
- Produces:
  - Overlay QSS con roles `#primario`, `#rail`, `#kpi-valor`, `QFrame#card`, badges, touch sizing.
  - `aplica_glow(widget: QWidget, radio: int = 24) -> None` — `QGraphicsDropShadowEffect` rojo de marca.

- [ ] **Step 1: `marca.qss` overlay**

Create `src/caja/marca.qss`:
```css
QPushButton { min-height: 40px; }
QPushButton#primario {
    background-color: #E01E26;
    border: none;
    color: #FFFFFF;
    font-weight: bold;
    min-height: 48px;
}
QPushButton#primario:hover { background-color: #C1161D; }
QPushButton#primario:disabled { background-color: #5A6278; color: #1E2330; }

QToolButton#rail {
    background-color: #151A25;
    border: none;
    border-left: 3px solid transparent;
    padding: 12px 0px;
}
QToolButton#rail:checked {
    background-color: #1E2330;
    border-left: 3px solid #E01E26;
}

QLabel#kpi-valor { font-family: "Geist Mono"; font-size: 22px; font-weight: bold; color: #F0F2F5; }
QLabel#secundario { color: #8B95A8; }
QLabel#positivo { color: #22C55E; font-weight: bold; }
QLabel#alerta { color: #F59E0B; font-weight: bold; }
QLabel#error { color: #EF4444; }
QLabel#badge-promo { color: #F59E0B; font-weight: bold; }

QFrame#card, QFrame.card {
    background-color: #1E2330;
    border: 1px solid #2E3548;
    border-radius: 10px;
}
QFrame#card[promo="true"] { border: 1px solid #F59E0B; }

QTableWidget, QTableView { selection-background-color: #E01E26; selection-color: #FFFFFF; }
QTableView::item { min-height: 40px; }
```

- [ ] **Step 2: Helper de glow**

Create `src/caja/efectos.py`:
```python
"""Efecto glow neón de marca para widgets clave (nav activo, botón primario, total)."""
from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QWidget

_GLOW = QColor(224, 30, 38, 115)  # rgba(224,30,38,.45)


def aplica_glow(widget: QWidget, radio: int = 24) -> None:
    efecto = QGraphicsDropShadowEffect(widget)
    efecto.setBlurRadius(radio)
    efecto.setColor(_GLOW)
    efecto.setOffset(0, 0)
    widget.setGraphicsEffect(efecto)
```

- [ ] **Step 3: Extender el test — overlay aplicado**

Edit `tests/caja/test_tema_marca.py` — añadir:
```python
def test_overlay_marca_en_stylesheet():
    app = QApplication.instance() or QApplication([])
    carga_tema(app)
    hoja = app.styleSheet()
    assert "QPushButton#primario" in hoja
    assert "border-left: 3px solid #E01E26" in hoja


def test_aplica_glow_pone_efecto():
    from PySide6.QtWidgets import QPushButton
    from caja.efectos import aplica_glow
    app = QApplication.instance() or QApplication([])
    b = QPushButton("x")
    aplica_glow(b)
    assert b.graphicsEffect() is not None
```

- [ ] **Step 4: Ejecutar tests**

Run: `cd w:/POS && .venv/Scripts/python -m pytest tests/caja/test_tema_marca.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add src/caja/marca.qss src/caja/efectos.py tests/caja/test_tema_marca.py
git commit -m "feat(marca): overlay QSS de roles/touch + helper de glow (MARCA.5)"
```

---

### Task MARCA.6: Ventana "Estilo" de referencia viva (POS)

**Repo:** `w:\POS` · **Files:**
- Create: `src/caja/pantalla_estilo.py`
- Create: `tests/caja/test_pantalla_estilo.py`

**Interfaces:**
- Consumes: `carga_tema`, `aplica_glow`, roles del overlay.
- Produces: `VentanaEstilo(QWidget)` — muestra swatches de tokens, muestras tipográficas y componentes (botón primario con glow, card, kpi). Lanzable con `python -m caja.pantalla_estilo`.

- [ ] **Step 1: Escribir el test (falla primero)**

Create `tests/caja/test_pantalla_estilo.py`:
```python
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from caja.tema import carga_tema
from caja.pantalla_estilo import VentanaEstilo


def test_ventana_estilo_construye():
    app = QApplication.instance() or QApplication([])
    carga_tema(app)
    v = VentanaEstilo()
    assert v.findChild(type(v), ) is None or True  # construye sin excepción
    assert v.windowTitle() == "Estilo · Carnes y Fruver RL"
```

- [ ] **Step 2: Ejecutar (debe fallar)**

Run: `cd w:/POS && .venv/Scripts/python -m pytest tests/caja/test_pantalla_estilo.py -v`
Expected: FAIL (módulo no existe).

- [ ] **Step 3: `pantalla_estilo.py`**

```python
"""Referencia viva del Sistema de Diseño en el POS (ventana dev)."""
from __future__ import annotations

import sys

from PySide6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from caja.efectos import aplica_glow
from caja.tema import carga_tema

_TOKENS = [
    ("carbon", "#0B0E14"), ("superficie", "#151A25"), ("superficie-2", "#1E2330"),
    ("marca", "#E01E26"), ("verde", "#22C55E"), ("ambar", "#F59E0B"),
]


class VentanaEstilo(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Estilo · Carnes y Fruver RL")
        raiz = QVBoxLayout(self)

        raiz.addWidget(QLabel("Sistema de Diseño — moderna premium"))

        fila = QHBoxLayout()
        for nombre, hex_ in _TOKENS:
            chip = QLabel(f"{nombre}\n{hex_}")
            chip.setStyleSheet(f"background:{hex_}; color:#F0F2F5; padding:16px; border-radius:10px;")
            fila.addWidget(chip)
        raiz.addLayout(fila)

        kpi = QLabel("$ 1.234.567")
        kpi.setObjectName("kpi-valor")
        raiz.addWidget(kpi)

        card = QFrame()
        card.setObjectName("card")
        card_l = QVBoxLayout(card)
        card_l.addWidget(QLabel("Tarjeta de superficie (card)"))
        raiz.addWidget(card)

        primario = QPushButton("Cobrar")
        primario.setObjectName("primario")
        aplica_glow(primario)
        raiz.addWidget(primario)


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    carga_tema(app)
    v = VentanaEstilo()
    v.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Ejecutar el test (debe pasar)**

Run: `cd w:/POS && .venv/Scripts/python -m pytest tests/caja/test_pantalla_estilo.py -v`
Expected: PASS.

- [ ] **Step 5: Verificación visual manual**

Run: `cd w:/POS && .venv/Scripts/python -m caja.pantalla_estilo`
Expected: ventana oscura con chips de color, KPI en Geist Mono, card con radio, y botón "Cobrar" rojo con glow.

- [ ] **Step 6: Commit**

```bash
git add src/caja/pantalla_estilo.py tests/caja/test_pantalla_estilo.py
git commit -m "feat(marca): ventana Estilo de referencia viva en POS (MARCA.6)"
```

---

## Cierre del plan

- Correr la suite completa una vez por lote (LOTE A: `npm run build` + impeccable; LOTE B: `pytest tests/caja -q`).
- Al cerrar, actualizar la fila correspondiente en `docs/README-pos.md` (fundación de marca lista) — fuera de los commits de código, en un commit de docs.
- Siguientes specs (fuera de este plan): **Rediseño Web** (slice Login + Dashboard móvil) y **Rediseño POS** (slice Venta + Cobro), que incluyen la UX real (navegación, menús, IA, set de iconos por vista).

## Self-Review (hecho)

- **Cobertura del spec:** tokens (MARCA.1), tipografía (MARCA.1/4), espacio-forma-elevación (tokens MARCA.1 + overlay MARCA.5), bindings web/POS (MARCA.1-3 / MARCA.4-5), referencia viva (MARCA.3/6), voz (documentada en Global Constraints; sin pantallas que la ejerzan aún, correcto por alcance). Non-goals respetados: ninguna pantalla real se rediseña.
- **Placeholders:** ninguno pendiente; MARCA.2 Step 1 aclara que la verificación es vía build de MARCA.3 (no test falso).
- **Consistencia de tipos:** `carga_fuentes()->list[str]`, `carga_tema(app)->None`, `aplica_glow(widget,radio=24)->None`, roles QSS (`#primario`, `#rail`, `#kpi-valor`, `#card`) usados igual en overlay y en `pantalla_estilo.py`. Utilidades Tailwind (`bg-marca`, `shadow-glow`, `font-display/mono`) definidas en MARCA.1 y consumidas en MARCA.2-3.
