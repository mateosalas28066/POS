# Prompt handoff — armar plan e implementar Plataforma web multi-local (Fase 0 + 1)

Copia todo lo que está debajo de la línea en una sesión nueva de Claude Code en `w:\POS`:

---

Vas a arrancar un **proyecto nuevo**: una **plataforma web multi-local en la nube** para el POS
**pos-siesa-remake** (`w:\POS`). El diseño ya está aprobado; tu primer trabajo es **armar el plan de
implementación** de la **Fase 0 + Fase 1** y luego ejecutarlo.

## Fuente de verdad (léela completa antes de nada)

**[docs/superpowers/specs/2026-07-06-plataforma-web-multi-local-design.md](../specs/2026-07-06-plataforma-web-multi-local-design.md)** — arquitectura global, decisiones y roadmap.
Complemento: [docs/estado-actual-y-brechas.md](../../estado-actual-y-brechas.md) (auditoría del POS actual).
No reinterpretes el spec; si algo falta, pregunta.

## Qué construir en esta entrega (Fase 0 + 1)

- **Fase 0 — cimientos:** extraer `src/core/` a un **paquete Python compartido** (POS + backend lo
  consumen); esqueleto del **backend FastAPI** que reusa ese `core`; **Supabase** (Postgres + Auth) con
  esquema que incluya **`almacen_id` transversal**; **shell React** (Vercel) con auth; identidad de
  locales (`local_id` + token).
- **Fase 1 — primera demo:** *ingest* de eventos del POS (**outbox** en el POS → `/sync/push`
  idempotente por `uuid`) + **dashboard de reportes multi-bodega** con gráficas (total, por almacén, y
  dentro de almacén por cajero y categoría). Esta es la pantalla que se le muestra al cliente.

Fases 2-4 (bodegas/conversión/traslado, compras/cuentas/CRM, adelgazar el POS) son **posteriores** —
cada una tendrá su propio spec+plan. No las implementes ahora.

## Decisiones ya tomadas (NO re-preguntar)

1. **Nube = cerebro, POS = caja registradora.** Híbrido por dominio: la web escribe lo compartido
   (catálogo, precios, bodegas); ventas/caja/adelantos/pagos solo suben para consultarse.
2. **Offline-first:** el POS debe vender sin internet por horas y sincronizar al reconectar (outbox
   idempotente con `uuid + local_id + timestamp`; réplica RO del catálogo en el POS).
3. **Stack:** React (Vercel) + **FastAPI que reusa `core/`** (Render/Railway/Fly) + **Supabase**
   (Postgres + Auth). Free tier para la prueba, misma arquitectura en producción. Portable.
4. **`core` como paquete compartido**, no monorepo (despliegues distintos: POS-escritorio vs nube).
5. **Inventario = gestión pura, sin costeo.** Se elimina el despiece/prorrateo del POS (Fase 4). En la
   nube: entrada/salida/conversión/traslado con confirmación, **solo desde la web**. (No en Fase 0-1.)
6. **Pagos CxC/CxP** gestionables desde web y POS (relevante en Fase 3).
7. **Fuera de alcance:** DIAN y liquidación de nómina completa (proveedor externo). De nómina solo el
   **adelanto desde caja** (Fase 3).

## Repos

- **`w:\POS`** (repo actual): aquí se **extrae el paquete `core` compartido** y vive el POS local.
- **Repo nuevo** para la plataforma web (backend FastAPI + frontend React). Decide con el usuario el
  nombre/ubicación antes de crearlo; propón `pos-plataforma-web`.

## Cómo trabajar

- **Primero el plan, luego el código.** Carga `superpowers:writing-plans` y redacta el plan de Fase 0+1
  con IDs de task únicos según `planes-pos`. Guárdalo en `docs/superpowers/plans/`. Pide revisión antes
  de ejecutar.
- **Ponytail** (mínimo código, YAGNI, stdlib/nativo primero). Reusa `ServicioReportes` para el dashboard
  (llevándolo al backend con `almacen_id`); reusa el `MovimientoInventario` reconstruible por almacén.
- **Migraciones** versionadas; el esquema Postgres nace con `almacen_id` para no re-migrar.
- **Git:** rama nueva (`feature/plataforma-web-fase-0-1`). Commits pequeños en español. **No merge ni
  push sin preguntar.** Si el spec no está commiteado aún, commitéalo primero (`docs: spec plataforma
  web multi-local`).

## Al cerrar

- Backend levanta y responde `/sync/push` (idempotente) + endpoints de dashboard.
- Dashboard React muestra reportes multi-bodega con datos empujados por el POS.
- Suite del POS (`python -m pytest -q`) sigue en verde tras extraer `core`.
- Reporta qué se implementó y cómo se verificó; pregunta antes de integrar/desplegar.

## Skills a cargar

`superpowers:writing-plans` (armar el plan) → `planes-pos` (IDs de task) → `pos-dominio` (lógica de
negocio), `db-design-pos` (esquema/migraciones), `testing-pos` (pruebas). Al ejecutar:
`superpowers:executing-plans`. Para el front, `frontend-design` y `dataviz` (dashboard con gráficas).
