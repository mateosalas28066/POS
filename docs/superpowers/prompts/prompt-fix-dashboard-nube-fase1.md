# Prompt handoff — corregir 2 bugs del dashboard nube (post Fase 0+1) y seguir el roadmap

Copia todo lo que sigue como primer mensaje de la nueva sesión.

---

Vas a **corregir 2 bugs reales** encontrados al usar en vivo el dashboard de la plataforma web
multi-local (repo `w:\pos-plataforma-web`, hermano de `w:\POS`), y luego decidir con el usuario
si sigues con el roadmap (Fase 2) o cierras aquí.

## Contexto (para no repreguntar)

- **Fase 0 + Fase 1 ya están implementadas y verificadas end-to-end** (commits en
  `w:\POS` rama `feature/plataforma-web-fase-0-1` y en `w:\pos-plataforma-web`, ambos repos con
  git propio, sin merge/push todavía — no lo hagas sin preguntar).
- Plan ejecutado: [docs/superpowers/plans/2026-07-06-plataforma-web-fase-0-1.md](../plans/2026-07-06-plataforma-web-fase-0-1.md).
  Spec: [docs/superpowers/specs/2026-07-06-plataforma-web-multi-local-design.md](../specs/2026-07-06-plataforma-web-multi-local-design.md).
- **Verificado real** (no solo tests con mocks): POS local → outbox → `HiloSincronizacion`
  (background, `src/sync_pdv/hilo_sincronizacion.py`) → `/sync/push` → Postgres real (Supabase,
  MCP conectado) → `/dashboard/*` → dashboard React. Durante esa verificación se encontraron y
  corrigieron 4 bugs reales (CORS, JWT sin tolerancia de reloj, hilo de sync sin cablear,
  `sqlite3.ProgrammingError` por conexión cross-thread) — ver commits recientes en ambos repos
  para el detalle de cada uno; sirven de referencia de "qué tipo de bug aparece solo probando en
  vivo" para los 2 de abajo.
- Backend corre con `SUPABASE_DB_URL` al **Session Pooler** de Supabase (IPv4,
  `aws-0-us-east-1.pooler.supabase.com:5432`), no la conexión directa (esa red tiene IPv6
  intermitente). Ver `backend/.env` (no versionado).
- El usuario ya usa el POS real con `w:\POS\iniciar_pos.ps1` (no versionado, tiene el
  `LOCAL_TOKEN`) apuntando al backend local en `:8000`.

## Los 2 bugs a corregir

### NUBE1.6 — "Ventas por categoría" muestra "Cat. #10" en vez del nombre real

**Sintoma:** el gráfico de barras "Por categoría" (`frontend/src/dashboard/components/PorCategoria.tsx`)
etiqueta cada barra como `Cat. #10`, `Cat. #20`, etc. en vez de "Carnes", "Frutas", "Verduras"...

**Causa raíz:** el dominio (`core.ServicioReportes.por_categoria` → `ReporteCategoria`) solo carga
`categoria_id` — correcto, `core` no conoce nombres de catálogo. Pero el adaptador de la nube nunca
enriquece con el nombre: `backend/app/dashboard.py::por_categoria` (línea ~61) devuelve
`{"categoria_id": r.categoria_id, "total": ..., "neto": ...}` sin `nombre`, a diferencia de
`resumen()` (línea ~35-42) que sí hace `JOIN` con `almacenes` para traer `nombre`.

**Fix sugerido:**
1. En `backend/app/dashboard.py::por_categoria`, antes de construir la respuesta, consultar
   `SELECT id, nombre FROM categorias` (o filtrado por los ids presentes en `rs`) y armar un dict
   `id -> nombre`; incluir `"nombre": nombre_por_id.get(r.categoria_id)` en cada item.
2. En `frontend/src/dashboard/components/PorCategoria.tsx`, actualizar el tipo `Categoria` con
   `nombre: string | null` y usar `f.nombre ?? \`Cat. #${f.categoria_id ?? "—"}\`` como label del
   eje X en vez de solo el id.
3. Test backend: extender `backend/tests/test_dashboard.py` (unitario con conexión fake, agregar
   `categorias` a las filas devueltas por `_ConnFake.execute` para `FROM categorias`) + el test de
   integración sembrado (`sembrada` fixture ya inserta `categorias VALUES (10,'Carnes')`) para
   confirmar que el endpoint devuelve `"nombre": "Carnes"`.
4. Verificar en el navegador real (no solo build): recargar el dashboard, clic en un almacén, ver
   nombres reales en "Por categoría".

### NUBE1.7 — "Ventas por almacén" (KPIs + gráfico principal) no se actualiza con ventas nuevas, aunque "por cajero" y "por categoría" sí

**Síntoma reportado por el usuario:** tras registrar una venta nueva en el POS y esperar el sync
automático, el gráfico "Ventas por almacén" y los KPIs de arriba (total, nº ventas) **se quedan
con los números viejos**; en cambio, al hacer clic en una barra, "Por cajero" y "Por categoría" sí
muestran los números correctos y actualizados.

**Hipótesis de causa raíz (a confirmar, no asumir sin verificar):** `frontend/src/dashboard/Dashboard.tsx`
hace `useEffect(() => { apiGet<Resumen>(...).then(setData); }, [])` — **array de dependencias
vacío**: el fetch de `/dashboard/resumen` corre **una sola vez**, al montar el componente, y nunca
se repite. `PorCajero`/`PorCategoria` (`frontend/src/dashboard/components/PorCajero.tsx`,
`PorCategoria.tsx`) son componentes hijos que **solo se montan** cuando el usuario hace clic en una
barra (`{almacen !== null && (<PorCajero .../>)}` en `Dashboard.tsx`) — su primer fetch ocurre en
ese momento, que puede ser *después* de que el sync ya subió la venta nueva, dando la ilusión de que
"funcionan bien" cuando en realidad **tampoco tienen mecanismo de refresco**: si el usuario ya tenía
un almacén seleccionado y llega una venta nueva, es de esperar que "por cajero"/"por categoría"
también se queden con datos viejos, por el mismo motivo. **Verifica esta hipótesis con una prueba
real** (deja el dashboard abierto con un almacén ya seleccionado, registra una venta, espera el
intervalo de sync, confirma si cajero/categoría de verdad se actualizan solos o no) antes de fijar
el alcance del fix — el reporte original del usuario no cubrió ese caso específico.

**Fix sugerido (ajusta según lo que confirme la verificación de arriba):**
- Agregar un mecanismo de refresco periódico a los 3 fetches (resumen en `Dashboard.tsx`,
  cajero/categoría en sus componentes) — por ejemplo un `setInterval` dentro de `useEffect` que
  vuelva a llamar `apiGet` cada N segundos (consistente con el modelo de sync periódico ya usado
  en el POS: `SYNC_INTERVALO_SEGUNDOS`), limpiando el interval en el cleanup del efecto.
  Alternativa más simple (Ponytail): un botón "Actualizar" manual en vez de polling automático —
  decide con el usuario cuál prefiere antes de implementar (pregunta si no está claro).
- Mantén el `RANGO` fijo como está (`TODO selector de fechas` ya diferido a post-demo,
  documentado en el propio `Dashboard.tsx`) — no lo toques a menos que el usuario lo pida.
- Test: si agregas polling, verifica con un test de frontend si el proyecto tiene infra para eso
  (revisa si hay algo en `frontend/` más allá de `npm run build`; si no hay test runner de
  frontend montado, la verificación puede quedar manual en el navegador — sé explícito sobre eso,
  no reclames cobertura de test que no existe).
- Verificación real obligatoria (no solo build): con backend+frontend corriendo y el POS real
  (`w:\POS\iniciar_pos.ps1`) empujando una venta, confirmar en el navegador que los 3 paneles
  (total/almacén, por cajero, por categoría) reflejan la venta nueva sin recargar la página.

## Reglas de trabajo

- **TDD donde aplique** (backend sí tiene pytest; frontend probablemente no — no inventes
  infraestructura de test nueva para esto, sería sobre-ingeniería para 2 fixes puntuales, salvo que
  el usuario la pida).
- **Ponytail**: mínimo código, reutiliza el patrón que ya existe (`resumen()` ya hace el join de
  nombres para almacenes; sigue el mismo patrón para categorías en vez de inventar uno nuevo).
- **No re-abras el alcance de Fase 0+1** ni empieces Fase 2 (catálogo/inventario multi-bodega) sin
  que el usuario lo pida explícitamente después de cerrar estos 2 bugs.
- **Git:** ambos repos ya tienen rama de trabajo activa (`feature/plataforma-web-fase-0-1` en
  `w:\POS`; rama por defecto en `w:\pos-plataforma-web`, revisa con `git status`). Commits pequeños
  en español seguidos del estilo ya usado (`fix(backend): ...`, `fix(frontend): ...`). **No hagas
  merge ni push sin preguntar.**
- Antes de tocar código, corre las suites como baseline: `cd w:\POS && python -m pytest -q` (hoy
  **420 passed**) y `cd w:\pos-plataforma-web\backend && .venv\Scripts\python -m pytest -q` (hoy
  **18 passed, 4 skipped** sin `TEST_DB_URL`; con `TEST_DB_URL` al pooler de Supabase, deberían
  pasar los 22).

## Al terminar

- Los 2 bugs verificados **en el navegador real** (backend + frontend corriendo, no solo
  `npm run build`), no solo por inspección de código.
- Suites en verde (backend pytest; POS pytest si tocaste algo ahí, cosa que no deberías necesitar
  para estos 2 bugs).
- Reporta qué se corrigió y cómo se verificó cada uno. **Pregunta antes de cualquier merge/push.**
- Si el usuario quiere seguir con el roadmap después: **Fase 2** (catálogo + inventario
  multi-bodega en la nube, réplica RO en el POS, precios/productos editables desde la web) necesita
  su propio spec+plan — no la empieces sin ese paso (`superpowers:writing-plans` primero).

## Skills a cargar

`superpowers:using-superpowers` al arrancar. `superpowers:systematic-debugging` para confirmar la
hipótesis de NUBE1.7 antes de fijar el fix. `pos-dominio`/`db-design-pos` no aplican (estos bugs son
de adaptador nube + frontend, no de dominio). `frontend-design`/`dataviz` si el fix de NUBE1.7 toca
la UI del gráfico más allá del refresco de datos (no debería). `testing-pos` no aplica a este repo
(es de `w:\POS`); para tests del backend nube sigue el patrón ya existente en
`backend/tests/test_dashboard.py` sin necesidad de un skill nuevo.
