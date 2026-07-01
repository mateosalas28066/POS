# Plan inicial — epics y primeras tareas

> **Documento histórico (2026-06-25).** Es el roadmap original con el que arrancó el proyecto;
> su numeración de epics (E1–E8) difiere de la implementación real. Para el **estado actual**
> (qué está implementado, en diseño o pendiente) consulta la tabla de
> [README-pos.md](README-pos.md#estado-actual). Se conserva como registro de la planeación inicial.

Roadmap de `pos-siesa-remake`. El **MVP local** son E1–E4; E5–E8 quedan como costuras diseñadas.

## Grafo de dependencias

```
E2 Inventario ─┬─> E4 Venta por peso ─┐
               │                       ├─> E1 Caja/Venta ─┬─> E3 Cierre de caja ─> E7 Reportes
               └───────────────────────┘                  │
E8 Usuarios/seguridad (transversal) ───────────────────────┘
E2 ─> E6 Sync multi-local (outbox)
E1 + E2 + modelo BD ─> E5 DIAN (interfaz)
```

**Orden de arranque:** primero **E2** y **E4** (dominio estable), luego **E1** (UI de caja sobre
ese dominio), después **E3**. E5–E8 después.

## Epics y primeras tareas

### E2 — Inventario *(arrancar aquí)*
- Definir entidades de dominio `Producto`, `Categoria`, `Impuesto` en `core` (sin DB).
- Definir el puerto `RepositorioProductos` en `core`.
- Diseñar tablas `productos`, `categorias`, `impuestos`, `inventario_movimientos` (skill `db-design-pos`).
- Implementar adaptador SQLite del repositorio + migración inicial en `scripts/`.
- Tests: alta de producto, consulta, descuento de stock (`tests/inventario/`).

### E4 — Venta por peso
- Definir el puerto `LectorPeso` en `core/perifericos/`.
- Implementar `IngresoManual` (para probar hoy sin hardware).
- Implementar `CodigoPesoGS1` (decodificar EAN-13 peso/precio) — referencia Chromis.
- Implementar `BalanzaSerial` (pyserial) — fruver.
- Regla de dominio `precio × peso` en `core`.
- Tests: precio×peso por los tres adaptadores (`tests/core/`).

### E1 — Caja / Venta
- Entidades `Venta`, `LineaVenta`, `Pago`, `MedioPago` en `core`.
- Servicio de venta: agregar línea (peso o unidad), calcular total con impuestos.
- Puertos `RepositorioVentas`, `RepositorioClientes`.
- Prototipo de pantalla de caja en Qt (PySide6): buscar producto, agregar, cobrar, recibo.
- Tests: venta simple, venta por peso, devolución.

### E3 — Cierre de caja / arqueo
- Entidad `CajaSesion`; regla de arqueo (cuadre efectivo + medios de pago) en `core`.
- Flujo apertura/cierre en la UI; informe del día.
- Tests: cierre con cuadre correcto e incorrecto.

### E5 — DIAN (interfaz)
- Puerto `EmisorDIAN` en `facturacion_dian/`.
- Armado del documento (de `Venta`+`Cliente`+`Impuesto`) en `core` (reglas fiscales aquí).
- Adaptador `EmisorStub` (comprobante interno sin valor fiscal).
- Reservar maestros `param_dian_*`. Auditar con subagente `auditor-dian`.

### E6 — Sync multi-local (outbox)
- Tabla `outbox_eventos`; escribir evento en cada venta/movimiento.
- Proceso export/import (cuando se defina la conexión entre locales).

### E7 — Reportes
- Ventas por caja/cajero/día; detalle por producto/cliente; cierres.

### E8 — Usuarios / seguridad *(transversal)*
- `usuarios`, roles y permisos por operación.
- Bloqueo/restricción de edición de clientes (como Siesa).

## Siguiente paso

Aprobar este plan y crear el **plan de implementación detallado** (skill writing-plans) para
**E2 + E4**, que es donde empieza el código.
