# Rediseño Web — migrar pantallas reales al sistema de marca — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrar las pantallas reales del frontend web (App shell, Login, Dashboard+charts, Inventario, Catálogo) al Sistema de Diseño de marca "Carnes y Fruver RL" — restaurando legibilidad, jerarquía y las barras de Recharts (hoy negras) — sin tocar lógica de datos, auth ni endpoints.

**Architecture:** Rediseño directo (opción B): cada pantalla se reescribe sobre los primitivos de `src/ui` (`Boton`, `Tarjeta`, `Campo`) y utilidades Tailwind de marca, borrando a medida las clases/vars muertas que MARCA.1 dejó huérfanas (`.tarjeta`, `.eyebrow`, `.kpi-valor`, `--series-*`, `--grid`, `--baseline`, `--surface`, `--ink`, `--muted`). Una capa base mínima en `index.css` estiliza los controles nativos (`input`/`select`/`textarea`/`table`) y define dos utilidades de primera clase (`.eyebrow`, `.kpi`) contra los tokens de marca, para no envolver ~40 campos crudos uno por uno. `charts.ts` recibe una escala categórica derivada de la marca (rojo `#E01E26` racionado). Cero cambios de datos: todo `apiGet`/`apiPost`, hook de estado y prop queda idéntico.

**Tech Stack:** React 19, Vite 8, Tailwind v4 (`@theme` de MARCA.1), Recharts 3, `@supabase/supabase-js`. Sin Vitest configurado → verificación por `npx tsc -b` + `npm run build` + `npx impeccable detect src/` + revisión visual en `npm run dev`. Skill `dataviz` se carga en WEBUI.4 para validar la paleta de charts.

## Global Constraints

- **Repo del código:** `w:\pos-plataforma-web` (frontend). Trabajar en su rama actual (la misma que usaron las tasks web de MARCA); **no push ni merge sin preguntar**. El plan y el update de README-pos viven en `w:\POS`.
- Personalidad: **moderna premium**, **dark-first**.
- Rojo de marca **exacto `#E01E26`**: solo intención primaria / selección / atención. **Nunca "todo rojo"**, nunca decoración.
- Glow `rgba(224,30,38,.45)` (`shadow-glow`) racionado a focus/activo.
- Fuentes: **Space Grotesk** (display, ya aplicada a `h1/h2/h3` vía capa base), **Geist Sans** (cuerpo), **Geist Mono** tabular (dinero/KPI). **Prohibido Inter/Roboto.**
- Touch targets ≥ **44×44px** en todo control interactivo.
- Ponytail: mínimo código, YAGNI, mínimas dependencias (no se añade ninguna). `core/` intocable.
- **Fuera de alcance (YAGNI):** selector de rango de fechas (sigue hardcodeado julio 2026), cambios de datos/auth/endpoints, rutas nuevas, el primitivo `NavInferior` (es bottom-nav de POS; esta web admin conserva nav **superior**).
- Copy: español, sentence case, voz activa.
- Epic prefix de tracking: **`WEBUI.*`** (usar el ID con prefijo en TodoWrite, nunca número pelado).

**Lotes sugeridos (ejecución batched inline; gate completo 1 vez por fase):**
- **FASE 1 (slice 1):** WEBUI.1 → WEBUI.2 → WEBUI.3 → WEBUI.4 → WEBUI.5
- **FASE 2:** WEBUI.6 → WEBUI.7 → WEBUI.8

Dentro de cada task se corre `npx tsc -b` (type-check rápido). El gate pesado (`npm run build` + `npx impeccable detect src/` + revisión visual) se corre al cerrar cada fase (WEBUI.5 y WEBUI.8).

---

### Task WEBUI.1: Capa base de marca + utilidades `.eyebrow`/`.kpi` (frontend/src/index.css)

**Repo:** `w:\pos-plataforma-web` · **Files:**
- Modify: `frontend/src/index.css`

**Interfaces:**
- Consumes: tokens `@theme` de MARCA.1 (`--color-*`, `--radius-*`, `--font-*`).
- Produces: estilos base para `input`/`select`/`textarea`/`table`/`th`/`td`/`h1`/`h2`/`h3`; utilidades `.eyebrow` (kicker mayúsculas `tinta-2`) y `.kpi` (número grande Geist Mono tabular). Consumidas por todas las tasks siguientes.

- [ ] **Step 1: Añadir la capa base + componentes al final de `index.css`**

Append a `frontend/src/index.css` (después de la regla `:focus-visible` existente; no tocar `@theme`):
```css
@layer base {
  input:not([type="checkbox"]):not([type="radio"]), select, textarea {
    min-height: 44px;
    padding: 0 0.75rem;
    background: var(--color-superficie);
    border: 1px solid var(--color-borde);
    border-radius: var(--radius-md);
    color: var(--color-tinta);
    font: inherit;
  }
  textarea { padding: 0.5rem 0.75rem; }
  select { padding-right: 2rem; }
  input::placeholder, textarea::placeholder { color: var(--color-tinta-2); }

  table { width: 100%; border-collapse: collapse; }
  th, td { padding: 0.5rem 0.75rem; text-align: left; }
  th { color: var(--color-tinta-2); font-weight: 600; font-size: 0.8125rem; }
  td { border-top: 1px solid var(--color-borde); }

  h1, h2, h3 { font-family: var(--font-display); font-weight: 600; }
}

@layer components {
  .eyebrow {
    margin: 0;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--color-tinta-2);
  }
  .kpi {
    margin: 0.25rem 0 0;
    font-family: var(--font-mono);
    font-size: 1.75rem;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
    color: var(--color-tinta);
  }
}
```

- [ ] **Step 2: Type-check**

Run (en `frontend/`): `npx tsc -b`
Expected: sin errores (el CSS no afecta tipos; confirma que el proyecto compila).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/index.css
git commit -m "feat(webui): capa base de controles + utilidades eyebrow/kpi (WEBUI.1)"
```

---

### Task WEBUI.2: App shell — header + nav chip-tabs + logout (frontend/src/App.tsx)

**Repo:** `w:\pos-plataforma-web` · **Files:**
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `Boton` de `src/ui`; utilidades de marca + `.eyebrow` de WEBUI.1.
- Produces: shell con header de marca y navegación superior en **chips** (activo = `bg-marca` blanco, inactivo = `superficie-2`/`tinta-2`). Ruteo por estado `vista` intacto.

- [ ] **Step 1: Reemplazar `App.tsx` completo**

```tsx
import { useEffect, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import { supabase } from "./supabase";
import { Boton } from "./ui";
import { Login } from "./auth/Login";
import { Dashboard } from "./dashboard/Dashboard";
import { Catalogo } from "./catalogo/Catalogo";
import { Inventario } from "./inventario/Inventario";

type Vista = "ventas" | "catalogo" | "inventario";
const TABS: { id: Vista; etiqueta: string }[] = [
  { id: "ventas", etiqueta: "Ventas" },
  { id: "catalogo", etiqueta: "Catálogo" },
  { id: "inventario", etiqueta: "Inventario" },
];
const TITULOS: Record<Vista, string> = { ventas: "Ventas", catalogo: "Catálogo", inventario: "Inventario" };

export default function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [vista, setVista] = useState<Vista>("ventas");

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => setSession(data.session));
    const { data: sub } = supabase.auth.onAuthStateChange((_e, s) => setSession(s));
    return () => sub.subscription.unsubscribe();
  }, []);

  if (!session) return <Login />;
  return (
    <div className="max-w-[1100px] mx-auto p-6 flex flex-col gap-6">
      <header className="flex items-start justify-between gap-4">
        <div>
          <p className="eyebrow">Plataforma POS · multi-local</p>
          <h1 className="text-3xl">{TITULOS[vista]}</h1>
        </div>
        <div className="flex items-center gap-3">
          <span className="eyebrow hidden sm:block">{session.user.email}</span>
          <Boton onClick={() => supabase.auth.signOut()}>Salir</Boton>
        </div>
      </header>
      <nav className="flex gap-2">
        {TABS.map((t) => {
          const on = vista === t.id;
          return (
            <button
              key={t.id}
              onClick={() => setVista(t.id)}
              className={`min-h-[44px] px-4 rounded-pill font-medium transition-colors outline-none focus-visible:shadow-glow
                ${on ? "bg-marca text-white" : "bg-superficie-2 border border-borde text-tinta-2 hover:border-tinta-2"}`}
            >
              {t.etiqueta}
            </button>
          );
        })}
      </nav>
      {vista === "ventas" && <Dashboard />}
      {vista === "catalogo" && <Catalogo />}
      {vista === "inventario" && <Inventario />}
    </div>
  );
}
```

- [ ] **Step 2: Type-check**

Run (en `frontend/`): `npx tsc -b`
Expected: sin errores.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat(webui): shell con header de marca y nav chip-tabs (WEBUI.2)"
```

---

### Task WEBUI.3: Login de marca (frontend/src/auth/Login.tsx)

**Repo:** `w:\pos-plataforma-web` · **Files:**
- Modify: `frontend/src/auth/Login.tsx`

**Interfaces:**
- Consumes: `Tarjeta`, `Campo`, `Boton` de `src/ui`; `.eyebrow`; `text-rojo-alerta`.
- Produces: pantalla de login centrada en `Tarjeta`, sin cambios de auth.

- [ ] **Step 1: Reemplazar `Login.tsx` completo**

```tsx
import { useState } from "react";
import { supabase } from "../supabase";
import { Tarjeta, Campo, Boton } from "../ui";

export function Login() {
  const [email, setEmail] = useState("");
  const [pass, setPass] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function entrar(e: React.FormEvent) {
    e.preventDefault();
    const { error } = await supabase.auth.signInWithPassword({ email, password: pass });
    if (error) setError(error.message);
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <Tarjeta className="w-full max-w-sm">
        <form onSubmit={entrar} className="flex flex-col gap-4">
          <div>
            <p className="eyebrow">Plataforma POS · multi-local</p>
            <h1 className="text-3xl">Entrar</h1>
          </div>
          <Campo id="email" label="Correo" type="email" value={email} autoComplete="email"
                 onChange={(e) => setEmail(e.target.value)} />
          <Campo id="pass" label="Contraseña" type="password" value={pass} autoComplete="current-password"
                 onChange={(e) => setPass(e.target.value)} />
          <Boton variante="primario" type="submit">Entrar</Boton>
          {error && <p className="text-rojo-alerta text-sm m-0">{error}</p>}
        </form>
      </Tarjeta>
    </div>
  );
}
```

- [ ] **Step 2: Type-check**

Run (en `frontend/`): `npx tsc -b`
Expected: sin errores.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/auth/Login.tsx
git commit -m "feat(webui): login sobre primitivos de marca (WEBUI.3)"
```

---

### Task WEBUI.4: Paleta de charts derivada de marca (frontend/src/dashboard/charts.ts)

**Repo:** `w:\pos-plataforma-web` · **Files:**
- Modify: `frontend/src/dashboard/charts.ts`

**Interfaces:**
- Consumes: variables CSS de marca (`--color-borde`, `--color-tinta-2`, `--color-superficie-2`, `--color-tinta`) que `@theme` expone en `:root`.
- Produces: `fmt`, `COP` (sin cambios); `SERIES: string[]` (escala categórica, rojo en el último slot); `MARCA: string` (`#E01E26`, resaltado de selección); `ejeTick`, `tooltipEstilo` con cromo de marca. Consumidos por WEBUI.5.

- [ ] **Step 1: Cargar el skill `dataviz`**

Invocar el skill `dataviz` antes de fijar los hexes: validar contraste de la escala en fondo `#0B0E14` (dark) y confirmar que el rojo queda racionado (no por-barra). Si algún hex no pasa contraste, ajustarlo conservando separación categórica.

- [ ] **Step 2: Reemplazar `charts.ts` completo**

```ts
export const COP = new Intl.NumberFormat("es-CO", {
  style: "currency", currency: "COP", maximumFractionDigits: 0,
});
export const fmt = (s: string | number) => COP.format(Number(s));

// Escala categórica derivada de la marca, accesible en dark. El rojo de marca
// #E01E26 queda en el último slot (atención) y se usa aparte como MARCA para la
// barra seleccionada — nunca "todo rojo".
export const SERIES = ["#38BDF8", "#22C55E", "#F59E0B", "#A78BFA", "#E01E26"];
export const MARCA = "#E01E26"; // resaltado de selección / intención primaria

// Cromo del chart con variables de marca (@theme las expone como --color-*).
export const ejeTick = { fill: "var(--color-tinta-2)", fontSize: 12 };
export const tooltipEstilo = {
  background: "var(--color-superficie-2)",
  border: "1px solid var(--color-borde)",
  borderRadius: 8,
  color: "var(--color-tinta)",
};
```

- [ ] **Step 3: Type-check**

Run (en `frontend/`): `npx tsc -b`
Expected: falla en `Dashboard.tsx`/`PorCajero.tsx`/`PorCategoria.tsx` **solo si** aún importan `SERIES` de forma incompatible — se corrige en WEBUI.5. Si WEBUI.5 aún no corrió, este type-check puede reportar el uso viejo de `SERIES`; es esperado y lo resuelve WEBUI.5. Confirmar que el error es únicamente por los consumidores, no por `charts.ts` en sí.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/dashboard/charts.ts
git commit -m "feat(webui): paleta de charts de marca, rojo racionado (WEBUI.4)"
```

---

### Task WEBUI.5: Dashboard + KPI/charts de marca (frontend/src/dashboard/*) — cierre FASE 1

**Repo:** `w:\pos-plataforma-web` · **Files:**
- Modify: `frontend/src/dashboard/Dashboard.tsx`
- Modify: `frontend/src/dashboard/components/KpiCard.tsx`
- Modify: `frontend/src/dashboard/components/PorCajero.tsx`
- Modify: `frontend/src/dashboard/components/PorCategoria.tsx`

**Interfaces:**
- Consumes: `Tarjeta`, `Boton`; `.eyebrow`, `.kpi`; `SERIES`, `MARCA`, `ejeTick`, `tooltipEstilo` de WEBUI.4.
- Produces: dashboard con KPIs en `Tarjeta`, barras con paleta de marca (sin negro), barra seleccionada en rojo.

- [ ] **Step 1: Reemplazar `components/KpiCard.tsx`**

```tsx
import { Tarjeta } from "../../ui";

export function KpiCard({ titulo, valor }: { titulo: string; valor: string }) {
  return (
    <Tarjeta className="min-w-[200px] flex-1">
      <p className="eyebrow">{titulo}</p>
      <p className="kpi">{valor}</p>
    </Tarjeta>
  );
}
```

- [ ] **Step 2: Reemplazar `components/PorCajero.tsx`**

```tsx
import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { apiGet } from "../../api";
import { ejeTick, fmt, SERIES, tooltipEstilo } from "../charts";
import { Tarjeta } from "../../ui";

type Cajero = { usuario_id: number | null; num_ventas: number; total: string; neto: string };

export function PorCajero({ almacenId, rango, refresco }: { almacenId: number; rango: string; refresco: number }) {
  const [filas, setFilas] = useState<Cajero[]>([]);
  useEffect(() => {
    apiGet<Cajero[]>(`/dashboard/almacen/${almacenId}/cajeros?${rango}`).then(setFilas);
  }, [almacenId, rango, refresco]);
  return (
    <Tarjeta>
      <h3 className="mt-0 mb-3 text-lg">Ventas por cajero</h3>
      <div className="overflow-x-auto">
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={filas.map((f) => ({ cajero: `Cajero #${f.usuario_id ?? "—"}`, total: Number(f.total) }))}>
            <CartesianGrid vertical={false} stroke="var(--color-borde)" />
            <XAxis dataKey="cajero" tick={ejeTick} stroke="var(--color-borde)" />
            <YAxis tick={ejeTick} stroke="var(--color-borde)" tickFormatter={(v) => fmt(v)} width={90} />
            <Tooltip formatter={(v) => fmt(String(v))} contentStyle={tooltipEstilo} cursor={{ fill: "var(--color-borde)", opacity: 0.3 }} />
            <Bar dataKey="total" name="Total" fill={SERIES[1]} radius={[4, 4, 0, 0]} maxBarSize={48} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Tarjeta>
  );
}
```

- [ ] **Step 3: Reemplazar `components/PorCategoria.tsx`**

```tsx
import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { apiGet } from "../../api";
import { ejeTick, fmt, SERIES, tooltipEstilo } from "../charts";
import { Tarjeta } from "../../ui";

type Categoria = { categoria_id: number | null; nombre: string | null; total: string; neto: string };

export function PorCategoria({ almacenId, rango, refresco }: { almacenId: number; rango: string; refresco: number }) {
  const [filas, setFilas] = useState<Categoria[]>([]);
  useEffect(() => {
    apiGet<Categoria[]>(`/dashboard/almacen/${almacenId}/categorias?${rango}`).then(setFilas);
  }, [almacenId, rango, refresco]);
  return (
    <Tarjeta>
      <h3 className="mt-0 mb-3 text-lg">Ventas por categoría</h3>
      <div className="overflow-x-auto">
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={filas.map((f) => ({ cat: f.nombre ?? `Cat. #${f.categoria_id ?? "—"}`, total: Number(f.total) }))}>
            <CartesianGrid vertical={false} stroke="var(--color-borde)" />
            <XAxis dataKey="cat" tick={ejeTick} stroke="var(--color-borde)" />
            <YAxis tick={ejeTick} stroke="var(--color-borde)" tickFormatter={(v) => fmt(v)} width={90} />
            <Tooltip formatter={(v) => fmt(String(v))} contentStyle={tooltipEstilo} cursor={{ fill: "var(--color-borde)", opacity: 0.3 }} />
            <Bar dataKey="total" name="Total" fill={SERIES[2]} radius={[4, 4, 0, 0]} maxBarSize={48} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Tarjeta>
  );
}
```

- [ ] **Step 4: Reemplazar `Dashboard.tsx`**

```tsx
import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { apiGet } from "../api";
import { ejeTick, fmt, MARCA, SERIES, tooltipEstilo } from "./charts";
import { Tarjeta, Boton } from "../ui";
import { KpiCard } from "./components/KpiCard";
import { PorCajero } from "./components/PorCajero";
import { PorCategoria } from "./components/PorCategoria";

type Ventas = { num_ventas: number; total: string; total_impuestos: string; neto: string };
type PorAlmacen = Ventas & { almacen_id: number; nombre: string };
type Resumen = { total: Ventas; por_almacen: PorAlmacen[] };

const RANGO = "desde=2026-07-01T00:00:00&hasta=2026-07-31T00:00:00"; // TODO selector de fechas (post-demo)
const REFRESCO_MS = 15000; // auto-refresco periódico (consistente con el sync del POS)

export function Dashboard() {
  const [data, setData] = useState<Resumen | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [almacen, setAlmacen] = useState<number | null>(null);
  const [refresco, setRefresco] = useState(0);

  useEffect(() => {
    apiGet<Resumen>(`/dashboard/resumen?${RANGO}`).then((d) => { setData(d); setError(null); }).catch((e) => setError(String(e)));
  }, [refresco]);

  useEffect(() => {
    const id = setInterval(() => setRefresco((n) => n + 1), REFRESCO_MS);
    return () => clearInterval(id);
  }, []);
  if (error) return <Tarjeta>No se pudo cargar el resumen ({error}). Verifica que el backend esté arriba y vuelve a intentar.</Tarjeta>;
  if (!data) return <p className="eyebrow">Cargando…</p>;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex justify-end">
        <Boton onClick={() => setRefresco((n) => n + 1)}>Actualizar</Boton>
      </div>
      <div className="flex gap-4 flex-wrap">
        <KpiCard titulo="Ventas del mes" valor={fmt(data.total.total)} />
        <KpiCard titulo="Nº de ventas" valor={String(data.total.num_ventas)} />
        <KpiCard titulo="Impuestos" valor={fmt(data.total.total_impuestos)} />
      </div>

      <Tarjeta>
        <h2 className="mt-0 mb-3 text-xl">Ventas por almacén</h2>
        <div className="overflow-x-auto">
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={data.por_almacen.map((a) => ({ ...a, total: Number(a.total) }))}>
              <CartesianGrid vertical={false} stroke="var(--color-borde)" />
              <XAxis dataKey="nombre" tick={ejeTick} stroke="var(--color-borde)" />
              <YAxis tick={ejeTick} stroke="var(--color-borde)" tickFormatter={(v) => fmt(v)} width={90} />
              <Tooltip formatter={(v) => fmt(String(v))} contentStyle={tooltipEstilo} cursor={{ fill: "var(--color-borde)", opacity: 0.3 }} />
              <Bar dataKey="total" name="Total" radius={[4, 4, 0, 0]} maxBarSize={64}
                   onClick={(_, i) => setAlmacen(data.por_almacen[i].almacen_id)}>
                {data.por_almacen.map((a) => (
                  <Cell key={a.almacen_id} fill={a.almacen_id === almacen ? MARCA : SERIES[0]} cursor="pointer" />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        <p className="eyebrow mt-2">Clic en una barra para ver cajeros y categorías del almacén.</p>
      </Tarjeta>

      {almacen !== null && (
        <div className="grid gap-6 [grid-template-columns:repeat(auto-fit,minmax(320px,1fr))]">
          <PorCajero almacenId={almacen} rango={RANGO} refresco={refresco} />
          <PorCategoria almacenId={almacen} rango={RANGO} refresco={refresco} />
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 5: Gate de cierre FASE 1 (build + slop + visual)**

Run (en `frontend/`):
```bash
npm run build
npx --yes impeccable@latest detect src/
```
Expected: build OK (sin errores TS/Vite); impeccable `[]` (exit 0). Además `npm run dev` y verificar:
- Login (cerrar sesión si hace falta) con tarjeta de marca, campos y botón rojo.
- Dashboard (`Ventas`): KPIs en tarjetas, **barras en color (no negras)**, tooltip/ejes legibles, barra seleccionada en rojo al hacer clic.
- `http://localhost:5173/#estilo` sigue intacto.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/dashboard
git commit -m "feat(webui): dashboard, KPIs y charts de marca — cierre fase 1 (WEBUI.5)"
```

---

### Task WEBUI.6: Inventario de marca (frontend/src/inventario/*)

**Repo:** `w:\pos-plataforma-web` · **Files:**
- Modify: `frontend/src/inventario/Inventario.tsx`
- Modify: `frontend/src/inventario/BandejaPendientes.tsx`

**Interfaces:**
- Consumes: `Tarjeta`, `Boton`; capa base (controles/tabla); `.eyebrow`.
- Produces: pantalla de inventario de marca; chips de operación con activo en rojo; sin cambios de datos.

- [ ] **Step 1: Reemplazar `Inventario.tsx` completo**

```tsx
import { useEffect, useMemo, useState } from "react";
import { apiGet, apiPost } from "../api";
import { Tarjeta, Boton } from "../ui";
import { BandejaPendientes } from "./BandejaPendientes";

type Ubicacion = { id: number; nombre: string; local_id: string | null; tipo: string };
type Producto = { id: number; nombre: string };
type Stock = { producto_id: number; stock: string };

// Operaciones "simples" (un producto, un movimiento). Conversión va aparte (multi-línea).
type OpSimple = "entrada" | "salida" | "ajuste" | "traslado";
const OPS: { id: OpSimple; etiqueta: string }[] = [
  { id: "entrada", etiqueta: "Entrada" },
  { id: "salida", etiqueta: "Salida" },
  { id: "ajuste", etiqueta: "Ajuste" },
  { id: "traslado", etiqueta: "Traslado" },
];

// Chip de marca (activo en rojo) — mismo tratamiento que la nav superior.
const chip = (on: boolean) =>
  `min-h-[44px] px-4 rounded-pill font-medium transition-colors outline-none focus-visible:shadow-glow ${
    on ? "bg-marca text-white" : "bg-superficie-2 border border-borde text-tinta-2 hover:border-tinta-2"
  }`;

function etiquetaUbic(u: Ubicacion): string {
  const sufijo = u.local_id ? ` · ${u.local_id}` : " · compartida";
  return `${u.nombre} (${u.tipo}${sufijo})`;
}

// Gestión web de inventario multi-ubicación (admin): operaciones, stock por ubicación
// y bandeja de traslados pendientes. Reusa /inventario/* (B.4-B.6).
export function Inventario() {
  const [ubicaciones, setUbicaciones] = useState<Ubicacion[]>([]);
  const [productos, setProductos] = useState<Producto[]>([]);
  const [ubicacion, setUbicacion] = useState<number | "">("");
  const [error, setError] = useState<string | null>(null);
  const [refresco, setRefresco] = useState(0); // fuerza recarga de stock + bandeja tras una operación

  useEffect(() => {
    Promise.all([
      apiGet<Ubicacion[]>("/inventario/ubicaciones"),
      apiGet<Producto[]>("/catalogo/productos"),
    ])
      .then(([us, ps]) => {
        setUbicaciones(us);
        setProductos(ps);
        if (us.length && ubicacion === "") setUbicacion(us[0].id);
        setError(null);
      })
      .catch((e) => setError(String(e)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const nombreProducto = useMemo(() => {
    const m = new Map(productos.map((p) => [p.id, p.nombre]));
    return (id: number) => m.get(id) ?? `#${id}`;
  }, [productos]);

  if (error) return <Tarjeta>No se pudo cargar inventario ({error}).</Tarjeta>;
  if (!ubicaciones.length) return <Tarjeta>No hay ubicaciones. Siembra locales/bodegas primero.</Tarjeta>;

  return (
    <div className="flex flex-col gap-6">
      <Tarjeta>
        <label className="flex gap-3 items-center">
          <span className="eyebrow">Ubicación</span>
          <select value={ubicacion} onChange={(e) => setUbicacion(Number(e.target.value))} className="flex-1">
            {ubicaciones.map((u) => (
              <option key={u.id} value={u.id}>{etiquetaUbic(u)}</option>
            ))}
          </select>
        </label>
      </Tarjeta>

      <div className="grid gap-6 [grid-template-columns:repeat(auto-fit,minmax(320px,1fr))]">
        <OperacionSimple ubicaciones={ubicaciones} productos={productos}
                         ubicacionActual={ubicacion} onHecho={() => setRefresco((n) => n + 1)} />
        <Conversion ubicaciones={ubicaciones} productos={productos}
                    ubicacionActual={ubicacion} onHecho={() => setRefresco((n) => n + 1)} />
      </div>

      {ubicacion !== "" && (
        <>
          <StockUbicacion ubicacionId={ubicacion} nombreProducto={nombreProducto} refresco={refresco} />
          <BandejaPendientes ubicacionId={ubicacion} nombreProducto={nombreProducto}
                             refresco={refresco} onConfirmado={() => setRefresco((n) => n + 1)} />
        </>
      )}
    </div>
  );
}

// --- Entrada/Salida/Ajuste/Traslado ------------------------------------------

function OperacionSimple({ ubicaciones, productos, ubicacionActual, onHecho }: {
  ubicaciones: Ubicacion[]; productos: Producto[]; ubicacionActual: number | ""; onHecho: () => void;
}) {
  const [op, setOp] = useState<OpSimple>("entrada");
  const [producto, setProducto] = useState<number | "">("");
  const [cantidad, setCantidad] = useState("");
  const [origen, setOrigen] = useState<number | "">("");
  const [destino, setDestino] = useState<number | "">("");
  const [estado, setEstado] = useState<string | null>(null);

  // ajuste va sobre el destino con cantidad con signo (+ suma, − merma), igual que el backend
  const usaDestino = op === "entrada" || op === "traslado" || op === "ajuste";
  const usaOrigen = op === "salida" || op === "traslado";

  async function enviar(e: React.FormEvent) {
    e.preventDefault();
    setEstado("Enviando…");
    const body: Record<string, unknown> = { producto_id: producto, cantidad: cantidad.trim() };
    if (usaOrigen) body.origen_id = origen === "" ? ubicacionActual : origen;
    if (usaDestino) body.destino_id = destino === "" ? ubicacionActual : destino;
    try {
      await apiPost(`/inventario/${op}`, body);
      setEstado(`${op} registrada.`);
      setCantidad("");
      onHecho();
    } catch (err) {
      setEstado(`Error: ${String(err)}`);
    }
  }

  return (
    <Tarjeta>
      <form onSubmit={enviar} className="flex flex-col gap-3">
        <h2 className="m-0 text-xl">Operación</h2>
        <div className="flex gap-2 flex-wrap">
          {OPS.map((o) => (
            <button key={o.id} type="button" onClick={() => setOp(o.id)} className={chip(op === o.id)}>
              {o.etiqueta}
            </button>
          ))}
        </div>
        <label className="flex flex-col gap-1">
          <span className="eyebrow">Producto</span>
          <select value={producto} required onChange={(e) => setProducto(Number(e.target.value))}>
            <option value="" disabled>Elige un producto…</option>
            {productos.map((p) => <option key={p.id} value={p.id}>{p.nombre}</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className="eyebrow">Cantidad{op === "ajuste" ? " (negativa = merma)" : ""}</span>
          <input value={cantidad} onChange={(e) => setCantidad(e.target.value)} inputMode="decimal"
                 required placeholder={op === "ajuste" ? "-3" : "10"} />
        </label>
        {usaOrigen && (
          <label className="flex flex-col gap-1">
            <span className="eyebrow">Origen</span>
            <select value={origen === "" ? ubicacionActual : origen} onChange={(e) => setOrigen(Number(e.target.value))}>
              {ubicaciones.map((u) => <option key={u.id} value={u.id}>{etiquetaUbic(u)}</option>)}
            </select>
          </label>
        )}
        {usaDestino && (
          <label className="flex flex-col gap-1">
            <span className="eyebrow">{op === "ajuste" ? "Ubicación a ajustar" : op === "traslado" ? "Destino (entra pendiente de confirmar)" : "Destino"}</span>
            <select value={destino === "" ? ubicacionActual : destino} onChange={(e) => setDestino(Number(e.target.value))}>
              {ubicaciones.map((u) => <option key={u.id} value={u.id}>{etiquetaUbic(u)}</option>)}
            </select>
          </label>
        )}
        <Boton variante="primario" type="submit">Registrar {op}</Boton>
        {estado && <p className="eyebrow m-0">{estado}</p>}
      </form>
    </Tarjeta>
  );
}

// --- Conversión (1 origen → N salidas → N entradas, solo cantidades) ----------

type Linea = { producto: number | ""; cantidad: string };
const LINEA_VACIA: Linea = { producto: "", cantidad: "" };

function Conversion({ ubicaciones, productos, ubicacionActual, onHecho }: {
  ubicaciones: Ubicacion[]; productos: Producto[]; ubicacionActual: number | ""; onHecho: () => void;
}) {
  const [origen, setOrigen] = useState<number | "">("");
  const [salidas, setSalidas] = useState<Linea[]>([{ ...LINEA_VACIA }]);
  const [entradas, setEntradas] = useState<Linea[]>([{ ...LINEA_VACIA }]);
  const [estado, setEstado] = useState<string | null>(null);

  function pares(ls: Linea[]): [number, string][] {
    return ls.filter((l) => l.producto !== "" && l.cantidad.trim() !== "")
             .map((l) => [l.producto as number, l.cantidad.trim()]);
  }

  async function enviar(e: React.FormEvent) {
    e.preventDefault();
    setEstado("Enviando…");
    try {
      await apiPost("/inventario/conversion", {
        origen_id: origen === "" ? ubicacionActual : origen,
        salidas: pares(salidas),
        entradas: pares(entradas),
      });
      setEstado("Conversión registrada.");
      setSalidas([{ ...LINEA_VACIA }]);
      setEntradas([{ ...LINEA_VACIA }]);
      onHecho();
    } catch (err) {
      setEstado(`Error: ${String(err)}`);
    }
  }

  return (
    <Tarjeta>
      <form onSubmit={enviar} className="flex flex-col gap-3">
        <h2 className="m-0 text-xl">Conversión</h2>
        <label className="flex flex-col gap-1">
          <span className="eyebrow">Ubicación</span>
          <select value={origen === "" ? ubicacionActual : origen} onChange={(e) => setOrigen(Number(e.target.value))}>
            {ubicaciones.map((u) => <option key={u.id} value={u.id}>{etiquetaUbic(u)}</option>)}
          </select>
        </label>
        <LineasEditor titulo="Consume (salidas)" lineas={salidas} setLineas={setSalidas} productos={productos} />
        <LineasEditor titulo="Produce (entradas)" lineas={entradas} setLineas={setEntradas} productos={productos} />
        <p className="eyebrow m-0">La merma es la diferencia entre lo que consume y lo que produce.</p>
        <Boton variante="primario" type="submit">Registrar conversión</Boton>
        {estado && <p className="eyebrow m-0">{estado}</p>}
      </form>
    </Tarjeta>
  );
}

function LineasEditor({ titulo, lineas, setLineas, productos }: {
  titulo: string; lineas: Linea[]; setLineas: (l: Linea[]) => void; productos: Producto[];
}) {
  function set(i: number, campo: keyof Linea, valor: string | number) {
    setLineas(lineas.map((l, j) => (j === i ? { ...l, [campo]: valor } : l)));
  }
  return (
    <fieldset className="border border-borde rounded-md p-3 flex flex-col gap-2">
      <legend className="eyebrow px-1">{titulo}</legend>
      {lineas.map((l, i) => (
        <div key={i} className="flex gap-2 flex-wrap">
          <select value={l.producto} onChange={(e) => set(i, "producto", Number(e.target.value))} className="flex-1 min-w-[140px]">
            <option value="" disabled>Producto…</option>
            {productos.map((p) => <option key={p.id} value={p.id}>{p.nombre}</option>)}
          </select>
          <input value={l.cantidad} onChange={(e) => set(i, "cantidad", e.target.value)}
                 inputMode="decimal" placeholder="cantidad" className="w-[110px]" />
          {lineas.length > 1 && (
            <Boton type="button" onClick={() => setLineas(lineas.filter((_, j) => j !== i))}>−</Boton>
          )}
        </div>
      ))}
      <Boton type="button" onClick={() => setLineas([...lineas, { ...LINEA_VACIA }])} className="self-start">
        + línea
      </Boton>
    </fieldset>
  );
}

// --- Stock por ubicación ------------------------------------------------------

function StockUbicacion({ ubicacionId, nombreProducto, refresco }: {
  ubicacionId: number; nombreProducto: (id: number) => string; refresco: number;
}) {
  const [stock, setStock] = useState<Stock[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiGet<Stock[]>(`/inventario/stock?ubicacion_id=${ubicacionId}`)
      .then((d) => { setStock(d); setError(null); })
      .catch((e) => setError(String(e)));
  }, [ubicacionId, refresco]);

  return (
    <Tarjeta>
      <h2 className="mt-0 mb-3 text-xl">Stock por ubicación</h2>
      {error && <p className="eyebrow">No se pudo cargar ({error}).</p>}
      {stock.length === 0 ? (
        <p className="eyebrow m-0">Sin existencias confirmadas en esta ubicación.</p>
      ) : (
        <div className="overflow-x-auto">
          <table>
            <thead><tr><th>Producto</th><th>Stock</th></tr></thead>
            <tbody>
              {stock.map((s) => (
                <tr key={s.producto_id}>
                  <td>{nombreProducto(s.producto_id)}</td>
                  <td>{s.stock}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Tarjeta>
  );
}
```

- [ ] **Step 2: Reemplazar `BandejaPendientes.tsx` completo**

```tsx
import { useCallback, useEffect, useState } from "react";
import { apiGet, apiPost } from "../api";
import { Tarjeta, Boton } from "../ui";

type Pendiente = {
  grupo_uuid: string | null;
  producto_id: number;
  cantidad: string;
  origen_id: number | null;
  fecha: string;
};

type Props = {
  ubicacionId: number;
  nombreProducto: (id: number) => string;
  refresco: number;      // cambia para forzar recarga desde el padre
  onConfirmado: () => void;
};

// Bandeja de traslados entrantes pendientes de una ubicación + botón Confirmar (flip).
export function BandejaPendientes({ ubicacionId, nombreProducto, refresco, onConfirmado }: Props) {
  const [pendientes, setPendientes] = useState<Pendiente[]>([]);
  const [error, setError] = useState<string | null>(null);

  const cargar = useCallback(() => {
    apiGet<Pendiente[]>(`/inventario/pendientes?ubicacion_id=${ubicacionId}`)
      .then((d) => { setPendientes(d); setError(null); })
      .catch((e) => setError(String(e)));
  }, [ubicacionId]);
  useEffect(cargar, [cargar, refresco]);

  async function confirmar(grupo_uuid: string) {
    try {
      await apiPost("/inventario/confirmar", { grupo_uuid });
      cargar();
      onConfirmado();
    } catch (e) {
      setError(String(e));
    }
  }

  return (
    <Tarjeta>
      <h2 className="mt-0 mb-3 text-xl">Traslados pendientes</h2>
      {error && <p className="eyebrow">No se pudo cargar ({error}).</p>}
      {pendientes.length === 0 ? (
        <p className="eyebrow m-0">Sin traslados pendientes en esta ubicación.</p>
      ) : (
        <div className="overflow-x-auto">
          <table>
            <thead>
              <tr><th>Producto</th><th>Cantidad</th><th>Origen</th><th>Fecha</th><th></th></tr>
            </thead>
            <tbody>
              {pendientes.map((p) => (
                <tr key={p.grupo_uuid ?? `${p.producto_id}-${p.fecha}`}>
                  <td>{nombreProducto(p.producto_id)}</td>
                  <td>{p.cantidad}</td>
                  <td>{p.origen_id ?? "—"}</td>
                  <td>{p.fecha?.slice(0, 16).replace("T", " ")}</td>
                  <td>
                    {p.grupo_uuid && (
                      <Boton type="button" onClick={() => confirmar(p.grupo_uuid!)}>Confirmar</Boton>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Tarjeta>
  );
}
```

- [ ] **Step 3: Type-check**

Run (en `frontend/`): `npx tsc -b`
Expected: sin errores.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/inventario
git commit -m "feat(webui): inventario y bandeja sobre primitivos de marca (WEBUI.6)"
```

---

### Task WEBUI.7: Catálogo + EditorOverlay de marca (frontend/src/catalogo/*)

**Repo:** `w:\pos-plataforma-web` · **Files:**
- Modify: `frontend/src/catalogo/Catalogo.tsx`
- Modify: `frontend/src/catalogo/EditorOverlay.tsx`

**Interfaces:**
- Consumes: `Tarjeta`, `Boton`; capa base (controles/tabla); `.eyebrow`.
- Produces: catálogo de marca; sin cambios de datos.

- [ ] **Step 1: Reemplazar `Catalogo.tsx` completo**

```tsx
import { useEffect, useState } from "react";
import { apiGet, apiPost } from "../api";
import { Tarjeta, Boton } from "../ui";
import { EditorOverlay } from "./EditorOverlay";

type Producto = {
  id: number;
  codigo_barras: string | null;
  nombre: string;
  unidad: string;
  vendido_por_peso: boolean;
  categoria_id: number | null;
  impuesto_id: number | null;
  costo: string;
};

const VACIO = {
  id: "" as number | "",
  codigo_barras: "",
  nombre: "",
  unidad: "und",
  vendido_por_peso: false,
  costo: "",
};

// Gestión web del catálogo: maestro (alta/edición) + editor de overlay por local.
export function Catalogo() {
  const [productos, setProductos] = useState<Producto[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({ ...VACIO });
  const [overlay, setOverlay] = useState<Producto | null>(null);

  function cargar() {
    apiGet<Producto[]>("/catalogo/productos")
      .then((d) => { setProductos(d); setError(null); })
      .catch((e) => setError(String(e)));
  }
  useEffect(cargar, []);

  function editar(p: Producto) {
    setForm({
      id: p.id,
      codigo_barras: p.codigo_barras ?? "",
      nombre: p.nombre,
      unidad: p.unidad,
      vendido_por_peso: p.vendido_por_peso,
      costo: p.costo,
    });
  }

  async function guardar(e: React.FormEvent) {
    e.preventDefault();
    try {
      await apiPost<{ id: number }>("/catalogo/productos", {
        id: form.id === "" ? null : form.id,
        codigo_barras: form.codigo_barras.trim() || null,
        nombre: form.nombre.trim(),
        unidad: form.unidad.trim() || "und",
        vendido_por_peso: form.vendido_por_peso,
        costo: form.costo.trim() || "0",
      });
      setForm({ ...VACIO });
      cargar();
    } catch (err) {
      setError(String(err));
    }
  }

  if (error) return <Tarjeta>No se pudo cargar el catálogo ({error}).</Tarjeta>;

  return (
    <div className="flex flex-col gap-6">
      <Tarjeta>
        <form onSubmit={guardar} className="flex flex-col gap-3">
          <h2 className="m-0 text-xl">{form.id === "" ? "Nuevo producto" : `Editando #${form.id}`}</h2>
          <div className="flex gap-3 flex-wrap">
            <input placeholder="Nombre" value={form.nombre} required className="flex-1 min-w-[160px]"
                   onChange={(e) => setForm({ ...form, nombre: e.target.value })} />
            <input placeholder="Código de barras" value={form.codigo_barras} className="flex-1 min-w-[160px]"
                   onChange={(e) => setForm({ ...form, codigo_barras: e.target.value })} />
            <input placeholder="Unidad (und/kg)" value={form.unidad} className="w-[120px]"
                   onChange={(e) => setForm({ ...form, unidad: e.target.value })} />
            <input placeholder="Costo" value={form.costo} inputMode="decimal" className="w-[120px]"
                   onChange={(e) => setForm({ ...form, costo: e.target.value })} />
            <label className="flex gap-2 items-center text-sm text-tinta-2">
              <input type="checkbox" checked={form.vendido_por_peso}
                     onChange={(e) => setForm({ ...form, vendido_por_peso: e.target.checked })} />
              <span>Por peso</span>
            </label>
          </div>
          <div className="flex gap-3">
            <Boton variante="primario" type="submit">Guardar</Boton>
            {form.id !== "" && <Boton type="button" onClick={() => setForm({ ...VACIO })}>Cancelar</Boton>}
          </div>
        </form>
      </Tarjeta>

      <Tarjeta>
        <h2 className="mt-0 mb-3 text-xl">Maestro de productos</h2>
        <div className="overflow-x-auto">
          <table>
            <thead>
              <tr><th>#</th><th>Nombre</th><th>Código</th><th>Unidad</th><th>Costo</th><th></th></tr>
            </thead>
            <tbody>
              {productos.map((p) => (
                <tr key={p.id}>
                  <td>{p.id}</td>
                  <td>{p.nombre}</td>
                  <td>{p.codigo_barras ?? "—"}</td>
                  <td>{p.unidad}</td>
                  <td>{p.costo}</td>
                  <td>
                    <div className="flex gap-2">
                      <Boton type="button" onClick={() => editar(p)}>Editar</Boton>
                      <Boton type="button" onClick={() => setOverlay(p)}>Overlay</Boton>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Tarjeta>

      {overlay && (
        <EditorOverlay productoId={overlay.id} nombre={overlay.nombre} onCerrar={() => setOverlay(null)} />
      )}
    </div>
  );
}
```

- [ ] **Step 2: Reemplazar `EditorOverlay.tsx` completo**

```tsx
import { useState } from "react";
import { apiPost } from "../api";
import { Tarjeta, Boton } from "../ui";

type Props = { productoId: number; nombre: string; onCerrar: () => void };

// Editor del overlay (precio/costo/activo por local) de un producto del maestro.
// "Aplicar a": todos los locales activos, o una lista específica de local_id.
export function EditorOverlay({ productoId, nombre, onCerrar }: Props) {
  const [precio, setPrecio] = useState("");
  const [costo, setCosto] = useState("");
  const [activo, setActivo] = useState(true);
  const [alcance, setAlcance] = useState<"todos" | "especificos">("todos");
  const [locales, setLocales] = useState("");
  const [estado, setEstado] = useState<string | null>(null);

  async function guardar(e: React.FormEvent) {
    e.preventDefault();
    setEstado("Guardando…");
    const destino =
      alcance === "todos"
        ? "todos"
        : locales.split(",").map((s) => s.trim()).filter(Boolean);
    try {
      const r = await apiPost<{ afectados: number }>("/catalogo/overlay", {
        producto_id: productoId,
        precio: precio.trim() === "" ? null : precio.trim(),
        costo: costo.trim() === "" ? null : costo.trim(),
        activo,
        locales: destino,
      });
      setEstado(`Aplicado a ${r.afectados} local(es).`);
    } catch (err) {
      setEstado(`Error: ${String(err)}`);
    }
  }

  return (
    <Tarjeta>
      <form onSubmit={guardar} className="flex flex-col gap-3">
        <div className="flex justify-between items-baseline">
          <h3 className="m-0 text-lg">Overlay · {nombre}</h3>
          <Boton type="button" onClick={onCerrar}>Cerrar</Boton>
        </div>

        <label className="flex flex-col gap-1">
          <span className="eyebrow">Precio local (vacío = no cambia)</span>
          <input value={precio} onChange={(e) => setPrecio(e.target.value)} inputMode="decimal" placeholder="20000" />
        </label>

        <label className="flex flex-col gap-1">
          <span className="eyebrow">Costo local (vacío = siembra del maestro al importar)</span>
          <input value={costo} onChange={(e) => setCosto(e.target.value)} inputMode="decimal" placeholder="12000" />
        </label>

        <label className="flex gap-2 items-center text-sm text-tinta-2">
          <input type="checkbox" checked={activo} onChange={(e) => setActivo(e.target.checked)} />
          <span>Activo (el local vende este producto)</span>
        </label>

        <fieldset className="border border-borde rounded-md p-3 flex flex-col gap-2">
          <legend className="eyebrow px-1">Aplicar a</legend>
          <label className="flex gap-2 items-center text-sm">
            <input type="radio" name="alcance" checked={alcance === "todos"} onChange={() => setAlcance("todos")} />
            <span>Todos los locales activos</span>
          </label>
          <label className="flex gap-2 items-center text-sm">
            <input type="radio" name="alcance" checked={alcance === "especificos"} onChange={() => setAlcance("especificos")} />
            <span>Locales específicos</span>
          </label>
          {alcance === "especificos" && (
            <input value={locales} onChange={(e) => setLocales(e.target.value)} placeholder="local-01, local-02" />
          )}
        </fieldset>

        <Boton variante="primario" type="submit">Aplicar overlay</Boton>
        {estado && <p className="eyebrow m-0">{estado}</p>}
      </form>
    </Tarjeta>
  );
}
```

- [ ] **Step 3: Type-check**

Run (en `frontend/`): `npx tsc -b`
Expected: sin errores.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/catalogo
git commit -m "feat(webui): catálogo y editor de overlay de marca (WEBUI.7)"
```

---

### Task WEBUI.8: Barrido de referencias muertas + gate final + README-pos

**Repo:** `w:\pos-plataforma-web` (código) y `w:\POS` (docs) · **Files:**
- Verify/Modify: cualquier residuo en `frontend/src/**`
- Modify: `docs/README-pos.md` (en `w:\POS`)

**Interfaces:**
- Consumes: todo lo anterior.
- Produces: cero referencias a clases/vars muertas; fila de estado actualizada.

- [ ] **Step 1: Grep de referencias muertas (deben dar 0 resultados)**

Run (en `w:/pos-plataforma-web/frontend`):
```bash
grep -rnE "--series-|--grid|--baseline|--surface|var\(--ink|--muted|kpi-valor|className=\"tarjeta\"|class=\"tarjeta\"" src/ || echo "LIMPIO"
```
Expected: imprime `LIMPIO` (ninguna coincidencia). Si algo aparece, corregirlo en su archivo (migrar a `<Tarjeta>`/`.eyebrow`/`.kpi`/vars `--color-*`) antes de seguir.
Nota: `.eyebrow` y `.kpi` son utilidades **vivas** de WEBUI.1 — no se buscan aquí.

- [ ] **Step 2: Gate final completo**

Run (en `frontend/`):
```bash
npm run build
npx --yes impeccable@latest detect src/
```
Expected: build OK; impeccable `[]`. Con `npm run dev`, verificar visualmente las 4 vistas + `#estilo`:
- **Login**: tarjeta de marca, botón rojo, error en rojo-alerta.
- **Dashboard**: KPIs, **barras a color (no negras)**, selección en rojo.
- **Inventario**: chips de operación (activo rojo), tarjetas, tablas y selects estilizados.
- **Catálogo**: formularios en tarjeta, tabla del maestro, overlay de marca.

- [ ] **Step 3: Actualizar `README-pos.md` (repo w:\POS)**

Edit `docs/README-pos.md` (tabla "Estado actual"): añadir/ajustar la fila del Rediseño Web indicando que las pantallas reales (App, Login, Dashboard+charts, Inventario, Catálogo) quedaron migradas al sistema de marca (WEBUI, fase 1 + fase 2). Seguir el formato de las filas existentes.

- [ ] **Step 4: Commits**

En `w:\pos-plataforma-web` (si hubo correcciones del Step 1):
```bash
git add frontend/src
git commit -m "chore(webui): barrido de referencias muertas + gate final (WEBUI.8)"
```
En `w:\POS`:
```bash
git add docs/README-pos.md docs/superpowers/plans/2026-07-08-rediseno-web-slice-1.md
git commit -m "docs(webui): rediseño web de pantallas reales implementado (WEBUI.8)"
```

---

## Cierre del plan

- Gate por fase, no por task, para bajo overhead: `npm run build` + `npx impeccable detect src/` + revisión visual al cerrar FASE 1 (WEBUI.5) y FASE 2 (WEBUI.8).
- **No push ni merge sin preguntar** en ninguno de los dos repos.
- Siguientes specs (fuera de este plan): selector de rango de fechas del dashboard; rediseño de la app POS (PySide6) si se desea paridad visual.

## Self-Review (hecho)

- **Cobertura del brief:** puente vs rediseño → se eligió B (Architecture); charts negras → WEBUI.4 (paleta de marca, rojo racionado) + WEBUI.5 (consumo); `.tarjeta`/`.eyebrow`/`.kpi-valor` → `<Tarjeta>` + utilidades `.eyebrow`/`.kpi` (WEBUI.1) migradas en WEBUI.2/3/5/6/7; nav superior → chip-tabs de marca (WEBUI.2), reutilizado en chips de Inventario (WEBUI.6); gate build+impeccable+visual (WEBUI.5, WEBUI.8). Non-goals respetados: sin cambios de datos/auth/endpoints, sin selector de fechas, sin `NavInferior`.
- **Placeholders:** ninguno; cada task trae el archivo completo o el bloque exacto. WEBUI.4 Step 3 aclara que un error de type-check en los consumidores es esperado hasta WEBUI.5.
- **Consistencia de tipos/nombres:** `SERIES: string[]` y `MARCA: string` definidos en WEBUI.4 y consumidos igual en Dashboard (`SERIES[0]`/`MARCA`), PorCajero (`SERIES[1]`), PorCategoria (`SERIES[2]`); `ejeTick`/`tooltipEstilo` sin cambio de forma. Primitivos `Tarjeta({children,className})`, `Boton({variante})`, `Campo({id,label})` usados según sus firmas de MARCA.2. Utilidad `chip(on: boolean)` local a Inventario, con el mismo tratamiento visual que la nav de App (no compartida por YAGNI; 2 usos).
