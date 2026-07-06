# Diseño — Plataforma web + POS multi-local (nube, bodegas, dashboard)

> Fecha: 2026-07-06 · Estado: **aprobado para planificar** · Autor: brainstorming con el dueño del negocio.
> Contexto previo: [../../estado-actual-y-brechas.md](../../estado-actual-y-brechas.md) (auditoría del POS local).
> Reemplaza el enfoque mono-local del POS actual por un modelo **nube = cerebro / POS = caja registradora**.

## 1. Objetivo

Construir una **plataforma web** (revisable desde PC o celular) con **sincronización entre locales**,
que centralice la gestión (catálogo, inventario multi-bodega, compras, cuentas, reportes) y un
**dashboard con gráficas**. El POS local se convierte en una **terminal de ventas offline-first** que
empuja sus operaciones a la nube y baja una réplica de solo lectura del catálogo.

**Fuera de alcance** (se resuelven con proveedor externo): facturación electrónica DIAN y la
**liquidación completa de nómina**. De nómina, aquí solo se maneja el **adelanto desde caja**.

## 2. Decisiones tomadas (brainstorming)

| Tema | Decisión |
|---|---|
| Rol de la nube | **Híbrido por dominio**: la web escribe lo compartido (catálogo, precios, inventario/bodegas); las ventas/caja/adelantos solo suben para consultarse. |
| Estrategia | **B→A incremental**: montar la nube alimentada por el push del POS; primer dominio movido de verdad = catálogo + inventario multi-bodega. El POS se adelgaza por fases. |
| Conectividad | **Offline-first**: el POS debe vender sin internet por horas y sincronizar al reconectar. |
| Stack | **React (Vercel) + FastAPI que reusa `core/` (Render/Railway/Fly) + Supabase (Postgres + Auth)**. Portable; free tier para la prueba, misma arquitectura en producción. |
| `core/` | Se extrae a un **paquete Python compartido** que consumen el POS y el backend nube (no monorepo). |
| Inventario | **Gestión pura, sin cálculos de costo.** Se elimina el despiece/costeo actual del POS. |
| Bodegas | Entrada/salida/conversión/traslado se operan **solo desde la web**. |
| Pagos (CxC/CxP) | Gestionables **desde la web y desde el POS**. |

## 3. Arquitectura en 3 capas

```
┌─────────────────────────┐        ┌──────────────────────────────┐
│  POS LOCAL (por local)  │  push  │        NUBE (backend)         │
│  Python + PySide6       │ eventos│  FastAPI (reusa core/)        │
│  SQLite local           │──────► │  Supabase Postgres + Auth     │
│  · Venta/cobro/peso/caja│        │  Fuente de verdad de:         │
│  · Devoluciones         │◄────── │  catálogo, precios, bodegas,  │
│  · Adelanto nómina      │  pull  │  compras, cuentas, reportes   │
│  · Pagos CxC/CxP        │catálogo└──────────────┬───────────────┘
│  · Réplica local (RO)   │                       │ REST
│  · Outbox (cola)        │        ┌──────────────▼───────────────┐
└─────────────────────────┘        │  WEB (React en Vercel)        │
                                   │  Dashboard + gráficas         │
                                   │  Gestión bodegas/compras/     │
                                   │  cuentas/CRM/catálogo         │
                                   └───────────────────────────────┘
```

- **POS local**: SQLite con (a) datos propios (ventas, caja, devoluciones, adelantos, pagos) y (b)
  **réplica RO** del catálogo/precios/clientes/promos/usuarios. **Outbox** encola eventos y los sube al
  reconectar.
- **Backend nube (FastAPI)**: reusa `core/`. Cuatro grupos de API: *ingest* (push del POS), *pull*
  (réplica hacia el POS), *dashboard* (lectura web) y *gestión* (escritura web).
- **Web (React/Vercel)**: dashboard + pantallas de gestión. Auth con Supabase.

## 4. Sincronización (offline-first)

La **partición por dominio** hace el sync casi sin conflictos:

| Dirección | Datos | Naturaleza | Conflictos |
|---|---|---|---|
| **POS → nube** (append-only) | ventas, pagos, movimientos de caja, arqueos, devoluciones, adelantos, abonos/pagos CxC-CxP | cada local es dueño de lo suyo | ninguno |
| **Nube → POS** (réplica RO) | productos, precios, impuestos, categorías, clientes, promociones, usuarios | nube es maestro | ninguno (nube gana) |

- **Outbox**: cada evento lleva `uuid + local_id + timestamp`. El backend hace *upsert* por `uuid` →
  reenviar es idempotente. `/sync/push` recibe lotes; `/sync/pull?cursor=…` entrega cambios del catálogo.
- **Identidad**: cada local tiene `local_id` + token de servicio.
- **Pagos desde ambos lados**: tanto el POS (offline, vía outbox) como la web (online) generan eventos
  de abono/pago; al ser append-only con UUID, no chocan.

## 5. Modelo de datos nuevo (nube, Postgres) y migraciones locales

**`almacen_id` es transversal.** Nuevas tablas/campos respecto a la auditoría:

- `almacenes` (bodegas): id, nombre, local_id, activo.
- `almacen_id` en: `inventario_movimientos`, `ventas`, `caja_sesiones`, `compras`, `gastos`,
  `promociones` (si aplica por local).
- Stock por bodega: se **reconstruye desde `inventario_movimientos`** filtrando por `almacen_id`
  (el `stock_de` actual ya se calcula desde movimientos, no es un contador mutable → encaja directo).
- `empleados` (o reuso de `usuarios`) + `adelantos_nomina` (empleado, monto, fecha, caja_sesion).
- `eventos_sync` / outbox en el POS: cola local de eventos pendientes de subir.

## 6. Inventario multi-bodega — **gestión pura, sin costeo**

Se **elimina** del POS el despiece con prorrateo (`ServicioDespiece`, `prorratear_costeo_despiece`,
`PantallaDespiece`). En la web se reemplaza por operaciones simples (cuadros de texto), todas
composiciones de `MovimientoInventario` con `almacen_id`:

1. **Entrada**: producto + cantidad + bodega. Ej.: "entraron 200 kg de res en canal".
2. **Salida**: producto + cantidad + bodega.
3. **Conversión**: un producto origen (ej. *canal 200 kg*) → varios productos destino (cortes: lomo,
   costilla, …) en la **misma bodega**. Internamente: 1 salida del origen + N entradas de los destinos.
   **Sin prorrateo de costo**; solo cantidades. La suma de destinos no tiene que igualar el origen
   (merma permitida) — es gestión, no balance contable.
4. **Traslado entre bodegas**: salida en bodega origen + entrada en bodega destino, con **paso de
   confirmación**: el destino confirma la recepción (estados: `enviado` → `confirmado`). Requisito
   explícito del cliente. Aplica a producto en bruto (canal) y a cortes por igual.

Permiso nuevo: `ACCION_GESTIONAR_INVENTARIO` (y/o `ACCION_CONFIRMAR_TRASLADO`) para operar bodegas.

## 7. Nómina — adelantos

- **POS local**: diálogo "Adelanto" en caja → **egreso de caja** (mismo patrón que gastos/pagos que ya
  pasa por `ServicioCaja.registrar_movimiento`), con `empleado_id`. Sube como evento.
- **Web**: consolida el **saldo de adelantos por empleado** y su reporte.
- **Liquidación de nómina completa**: fuera de alcance (proveedor externo).

## 8. Dashboard y reportes (web)

Reportes **total**, **por almacén/bodega**, y dentro de almacén por **cajero** y **categoría** (como el
POS ya calcula, ahora con dimensión bodega). Gráficas: ventas por día y por local, comparativo entre
locales, top productos, saldos CxC/CxP, gastos, adelantos. Reusa la lógica de `ServicioReportes`
llevada al backend con `almacen_id`.

## 9. Repos y código compartido

- **Repo actual (POS)**: conserva venta/caja/devoluciones/adelantos/pagos + cliente de sync (outbox).
  Se le **quita** despiece/costeo y, por fases, los módulos de gestión migrados a la nube.
- **Repo nuevo (plataforma web)**: backend FastAPI + frontend React.
- **`core` compartido**: paquete Python instalable (pip privado o git submodule) con entidades + reglas
  puras; lo consumen ambos repos. La misma regla corre en el POS y en la nube sin duplicar.

## 10. Roadmap por fases (cada fase = su propio spec + plan)

| Fase | Entrega | Nota |
|---|---|---|
| **0** | Extraer `core` compartido; backend FastAPI + Supabase (esquema con `almacen_id`); shell React + auth; identidad de locales | Cimientos |
| **1** | Ingest de eventos del POS (push/outbox) + **dashboard de reportes multi-bodega** | ⭐ Primera demo para el cliente |
| **2** | Catálogo + inventario multi-bodega en la nube (entrada/salida/conversión/traslado + confirmación); POS baja réplica RO; precios/productos editables desde la web | Requisito núcleo |
| **3** | Compras/proveedores/cuentas (CxC-CxP desde web y POS)/CRM + adelantos de nómina consolidados | Gestión completa |
| **4** | Adelgazar el POS (quitar módulos migrados, incl. despiece/costeo) + endurecer sync/conflictos | Modelo "A" limpio |

**Este documento es el diseño de arquitectura global.** La primera implementación (writing-plans)
apunta a **Fase 0 + 1**: backend + Supabase + dashboard alimentado por el push del POS.

## 11. Riesgos y decisiones abiertas

1. **Sync offline-first** es la pieza de mayor riesgo: el POS no puede dejar de vender. Se mitiga con
   outbox idempotente (UUID) y réplica RO del catálogo.
2. **`almacen_id` transversal**: introducirlo temprano en el esquema Postgres evita re-migraciones.
3. **Free tier de backend** (Render/Railway/Fly) duerme o limita horas — aceptable para demo, a revisar
   si el cliente confirma.
4. **Alcance de "CRM"**: por ahora = clientes/proveedores + historial de compras/saldos; ampliar
   (notas, seguimiento) solo si el negocio lo pide (YAGNI).
5. **Merma en conversión**: se permite que destinos ≠ origen; si el negocio quiere control de merma,
   es una fase posterior.
