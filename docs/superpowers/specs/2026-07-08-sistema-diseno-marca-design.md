# Spec de diseño — Sistema de Diseño de marca "Carnes y Fruver RL" (fundación visual)

> Fecha: 2026-07-08
> Estado: propuesto (brainstorm aprobado, pendiente revisión del usuario)
> Epic prefix reservado para el plan: `MARCA.*`
> Gobierna dos repos: `w:\POS` (POS PySide6) y `w:\pos-plataforma-web` (web React).
> Logo fuente: `D:\Descargas\Logo_RL.png` (recomendado versionar en `docs/brand/`).

## 1. Contexto y objetivo

El objetivo de negocio es **poder vender/desplegar el producto**: ambas interfaces deben
verse profesionales y de fácil manejo. Hoy:

- **Web** (`pos-plataforma-web/frontend`): React + Vite + Supabase, **estilos inline** sobre
  una paleta clara de `dataviz`. Diagnóstico con `impeccable detect src/` → `[]` (cero
  anti-patrones): el problema **no es "slop", es ausencia de diseño**. No adapta a móvil
  (`max-width:1100px`, nav de tabs superior).
- **POS** (`src/caja/tema.qss`): tema oscuro competente, acento rojo coral `#EF4444`.
  Genérico, ~70 % alineado a la marca ya por ser oscuro+rojo.

La marca **"Carnes y Fruver RL"** ya existe: cabeza de toro con efecto **neón/glow rojo**
sobre carbón; wordmark blanco con contorno rojo. Negocio real: carnicería-fruver con
**4 sedes**. Personalidad declarada: **moderna premium**.

Este spec define **la fundación visual** que ambos productos importan, para que no diverjan.

## 2. Non-goals (límite explícito)

Este spec es **solo lo visual** ("el look"). **NO** incluye UX real, que va en los specs
por-producto siguientes:

- **NO** rediseña navegación, control de menús ni estructura de secciones.
- **NO** define arquitectura de información ni flujos de pantalla.
- **NO** define el *set* de iconos por vista (qué icono representa cada sección) — eso es
  wayfinding y es decisión de UX. Aquí solo se fija el **estilo** de icono (grosor de
  trazo, grilla), no el mapeo icono→vista.
- **NO** toca lógica de negocio, `core/`, ni el aislamiento hexagonal.

Regla de oro respetada: `core/` no se toca; esto vive en adaptadores UI (`caja/` QSS y el
frontend web). Filosofía Ponytail: mínimo código y, del lado web, mínimas dependencias.

## 3. Sistema de color (dark-first)

Tokens **semánticos** (las pantallas nunca hardcodean hex). Oscuro es el modo primario en
ambos productos.

| Token | Hex | Rol |
|---|---|---|
| `marca` | `#E01E26` | Rojo de marca — acción primaria, estado activo, el único color audaz |
| `marca-hover` | `#C1161D` | Rojo pressed/hover |
| `glow` | `rgba(224,30,38,.45)` | **Firma** neón (focus ring, nav activo, hero) — uso racionado |
| `carbon` | `#0B0E14` | Fondo de app |
| `superficie` | `#151A25` | Paneles / rail |
| `superficie-2` | `#1E2330` | Cards / inputs |
| `borde` | `#2E3548` | Hairlines |
| `tinta` | `#F0F2F5` | Texto primario |
| `tinta-2` | `#8B95A8` | Texto secundario |
| `verde` | `#22C55E` | Fruver / positivo / stock-ok (funcional) |
| `ambar` | `#F59E0B` | Advertencias / promo |
| `rojo-alerta` | `#EF4444` | Errores (distinto del rojo de marca: "peligro" ≠ "primario") |

Dos reglas deliberadas:

1. **El rojo de marca es solo para intención primaria**, nunca decoración. Un botón rojo
   siempre significa "la acción principal de esta pantalla".
2. **El glow neón es la firma memorable pero racionada** a focus/activo/hero; si se abusa,
   deja de sentirse premium.

Accesibilidad: todo texto cumple WCAG AA sobre `carbon` (a verificar en build;
`tinta-2` sobre `carbon` ≈ 5.9:1). `rojo-alerta` se reserva para error y se diferencia del
rojo de marca para no confundir "peligro" con "acción principal".

## 4. Tipografía ("moderna premium")

`frontend-design` e `impeccable` **prohíben Inter/Roboto** (el tell por defecto de IA). Se
eligen fuentes con carácter pero legibles, **todas libres y auto-hospedables** (requisito:
el POS es offline y auto-hospedar mantiene el CSP web limpio):

- **Display / títulos → Space Grotesk.** Moderna, ligeramente técnica, confiada. Uso con
  restricción (títulos, KPIs, hero).
- **Cuerpo / UI → Geist Sans.** Limpia, contemporánea, buena en tamaños chicos (tablas
  densas del POS, móvil).
- **Dinero / numéricos → Geist Mono, tabular figures.** Precios, totales, KPIs alinean
  dígito a dígito: lee preciso y premium (crítico en caja y en el dashboard).

Escala (rem, razón 1.25): `12 / 14 / 16 / 20 / 25 / 31 / 39`.
Pesos: 400 cuerpo, 500 labels UI, 600 títulos, 700 display/KPIs.

Wiring de fuentes:
- **Web:** `@font-face` woff2 auto-hospedados en `frontend/public/fonts/`.
- **POS:** TTF empacados + `QFontDatabase.addApplicationFont(...)` en el arranque de la app.

## 5. Espacio, forma y elevación

- **Escala de espaciado (px):** `4 / 8 / 12 / 16 / 24 / 32 / 48` — un solo ritmo. Corregir
  el apretujamiento actual es el upgrade "premium" más barato.
- **Radio:** `sm 6 · md 10 · lg 16 · pill 999`. Cards/inputs/botones `md`; chips/nav-pills
  `pill`. (El lettering del logo es redondeado → radio suave, sin brutalismo de radio 0.)
- **Elevación = oscuridad + un glow, no sopa de sombras.** Las superficies suben por
  luminosidad (`carbon → superficie → superficie-2`); la **única** sombra del sistema es el
  glow rojo sobre el elemento activo/primario.
- **Touch targets:** mínimo **44×44px** (web, teléfono) / **48px de alto de fila** (POS,
  estación). Las acciones de venta primarias del POS reciben targets sobredimensionados.
  Es la mayor ganancia de usabilidad según la investigación de POS.

## 6. Cómo consume cada producto los tokens (una fuente de verdad, dos bindings)

### 6.1 Web — Tailwind

- Tokens → variables CSS en `:root` **y** `tailwind.config` `theme.extend`
  (colors/spacing/radius/fontFamily/boxShadow). Utilidades reales: `bg-carbon`,
  `text-marca`, `shadow-glow`. **Prohibido hex arbitrario en el markup.**
- **impeccable** como gate anti-slop (`npx impeccable detect src/`, exit 2 = falla).
- **taste-skill** (`redesign-existing-projects`, `imagegen-frontend-mobile`) guía la
  composición. Instalado en `frontend/.agents/skills/` (ver §9).

### 6.2 POS — qt-material + overlay de marca

Decisión del usuario: **adoptar qt-material** (cobertura instantánea de todos los widgets).
Para conservar la identidad:

- **Tema XML custom** `carnes_fruver.xml` con `primaryColor = #E01E26` y base oscura,
  aplicado con `qt_material.apply_stylesheet(app, theme='carnes_fruver.xml', extra=…)`.
- **Overlay `marca.qss`** (append tras qt-material) que reintroduce los `objectName` ya
  usados (`#primario`, `#rail`, `#kpi-valor`, `#card`, badges) + touch sizing.
- **Glow:** `QGraphicsDropShadowEffect` (rojo, blur) sobre pocos widgets clave (nav activo,
  botón primario, total), ya que **QSS no soporta `box-shadow` real**.
- Referencia de cobertura: usar el tema `dark_red` de qt-material como checklist de widgets
  para no olvidar ninguno (QMenu, QSlider, QProgressBar, tooltips, checkboxes, date pickers).
- Nueva dependencia aceptada: `qt-material` (se documenta en el arranque `bootstrap.py`).

### 6.3 Referencia viva

Una página/ventana "Estilo" por producto que **muestra** tokens y componentes (no un doc
abstracto), testeable:
- Web: ruta `/estilo`.
- POS: ventana dev "Estilo".

## 7. Voz y microcopy

Español, sentence case, voz activa. La acción mantiene la misma palabra en todo el flujo
(botón "Cobrar" → toast "Cobrado"). Los errores dicen qué pasó + cómo arreglarlo, en la voz
de la interfaz, sin disculparse. Los estados vacíos invitan a la siguiente acción ("Aún no
hay ventas hoy — registra la primera"). Se nombra por lo que el usuario controla, nunca por
internos del sistema.

## 8. Alcance de ESTE spec y qué sigue

**Dentro:** el sistema de tokens, setup tipográfico (fuentes auto-hospedadas cableadas en
ambos), los dos bindings (tema Tailwind + tema qt-material + overlay), y la página de
referencia viva por producto.

**Fuera (a propósito):** rediseñar pantallas reales y **toda la UX** (navegación, menús,
secciones, IA, set de iconos por vista). Eso son los dos specs siguientes:

1. **Rediseño Web** — empieza por el slice vertical: Login + Dashboard en móvil.
2. **Rediseño POS** — empieza por el flujo hero: Venta + Cobro.

Cada uno consume esta fundación y arranca por su slice para validar el look antes del
rollout masivo (~25 pantallas).

## 9. Notas de tooling (ya ejecutado en el brainstorm)

- `impeccable detect src/` sobre la web → `[]` (limpio). Se adopta como gate de CI.
- `taste-skill` instalado (13 variantes) en `frontend/.agents/skills/` + `skills-lock.json`,
  **untracked** en `pos-plataforma-web`. Recomendación: agregar `.agents/` y
  `skills-lock.json` al `.gitignore` de ese repo (tooling, no fuente).
- `wondelai/skills --all --global`: **descartado** (50 frameworks de negocio, poca relevancia
  UI, bloat global). Alternativas más pertinentes si se quieren: Vercel
  `web-design-guidelines`, skills de `shadcn/ui`.

## 10. Criterios de aceptación de la fundación

- Existe un único set de tokens semánticos, consumido por Web (Tailwind) y POS (qt-material
  + overlay) sin hex duplicados divergentes.
- Space Grotesk / Geist Sans / Geist Mono cargan en ambos productos (offline en POS).
- Página de referencia viva navegable en ambos productos.
- `impeccable detect src/` sigue en `[]` tras introducir la fundación web.
- Ninguna pantalla real fue rediseñada (eso es fuera de alcance): la fundación se valida en
  la página de referencia, no repintando flujos.
