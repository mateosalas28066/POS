# Diseño: pos-siesa-remake

> Spec de arquitectura y organización del workspace para un POS autónomo que reemplaza
> el POS de Siesa sobre Linux Debian, orientado a un negocio de carnes y frutas.
> Fecha: 2026-06-25 · Estado: aprobado para materializar.

## 1. Objetivo y alcance

Construir un Punto de Venta (POS) autónomo (sin dependencia de Siesa) con:

- **Hoy–mañana (MVP local, una caja):** venta + cobro, inventario básico, cierre de caja
  con arqueo, y venta por peso (carnes/frutas).
- **Costuras para crecer sin reescribir:** facturación electrónica DIAN (interfaz lista,
  implementación diferida) y sincronización multi-local (patrón outbox definido, no
  implementado a fondo hoy).

### Decisiones congeladas

| Tema | Decisión |
|---|---|
| Lenguaje / UI | Python 3.11+ con **PySide6 (Qt6)** |
| Persistencia | **SQLite** local (offline-first); ruta a PostgreSQL para multi-local |
| Alcance | POS **autónomo**, no integra con Siesa |
| DIAN | **Diferido** tras interfaz `EmisorDIAN`; stub interno hoy, proveedor tecnológico después |
| Topología | Una caja local hoy; costura `sync_pdv` para multi-local mañana |
| Peso | **Dos** métodos: balanza serial (fruver) + código GS1 peso/precio (carne) + ingreso manual (fallback) |

### Principio rector (Ponytail)

Generar el **mínimo código necesario**. Antes de escribir: ¿hace falta?, ¿lo resuelve la
stdlib?, ¿es nativo?, ¿se puede en una línea? No construir lo que aún no se usa (YAGNI).

## 2. Arquitectura (hexagonal / puertos y adaptadores)

**Regla de oro:** `src/core/` no conoce Qt ni SQLite. Contiene entidades, reglas de negocio
y **puertos** (interfaces). Las implementaciones concretas (SQLite, balanza, DIAN) son
adaptadores que viven fuera del núcleo y se enchufan por inyección de dependencias.

**Aislamiento estricto (no negociable):** `inventario/`, `caja/` y `sync_pdv/` acceden a
datos **solo** a través de puertos `RepositorioX` definidos en `core`. Está prohibido
ejecutar SQL fuera de los adaptadores de repositorio. Esto permite cambiar
SQLite→PostgreSQL sin tocar reglas de negocio.

### Módulos `src/`

| Carpeta | Responsabilidad | Conoce Qt/DB |
|---|---|---|
| `core/` | Entidades, reglas de negocio, puertos (`RepositorioX`, `EmisorDIAN`, `LectorPeso`), cálculo de impuestos / precio×peso / arqueo, **y armado de datos de factura DIAN** | No (Python puro) |
| `core/perifericos/` | Puerto `LectorPeso` + adaptadores `BalanzaSerial`, `CodigoPesoGS1`, `IngresoManual` | Solo pyserial |
| `inventario/` | Productos, stock, movimientos. Adaptadores `Repositorio*` sobre SQLite | SQLite |
| `caja/` | UI Qt: pantalla de venta, cobro, devoluciones, cierre/arqueo | Qt |
| `facturacion_dian/` | **Solo** puerto `EmisorDIAN` + adaptadores: `EmisorStub` (comprobante interno sin valor fiscal) y, futuro, `EmisorProveedor` | — |
| `sync_pdv/` | Patrón **outbox**: tabla `outbox_eventos` + procesos export/import hacia servidor central. Diseñado, no implementado a fondo hoy | SQLite |

**Frontera DIAN clave:** el armado de la factura (construir el documento a partir de
`Venta` + `Cliente` + `Impuesto` y las reglas fiscales) es **lógica de dominio en `core`**.
`facturacion_dian/` solo transporta/firma/transmite. Nunca poner reglas fiscales en el adapter.

## 3. Modelo de datos mínimo (SQLite)

Tablas del MVP (acceso solo vía repositorios):

- `usuarios` (id, nombre, rol, hash_password)
- `categorias` (id, nombre)
- `impuestos` (id, nombre, tarifa, **codigo_dian** _reservado_)
- `medios_pago` (id, nombre)
- `productos` (id, codigo_barras, nombre, categoria_id, precio, costo, impuesto_id,
  **vendido_por_peso** BOOL, unidad)
- `clientes` (id, identificacion, nombre, contacto, **bloqueado_edicion** BOOL,
  **tipo_documento**, **regimen**, **tipo_responsabilidad** _reservados DIAN_)
- `caja_sesiones` (id, usuario_id, apertura_fecha, monto_inicial, cierre_fecha,
  monto_contado, estado)
- `ventas` (id, fecha, usuario_id, caja_sesion_id, cliente_id, total, total_impuestos, estado)
- `venta_lineas` (id, venta_id, producto_id, cantidad_o_peso, precio_unit, impuesto, subtotal)
- `pagos` (id, venta_id, medio_pago_id, monto, referencia)
- `inventario_movimientos` (id, producto_id, **lote_id** NULLABLE, tipo, cantidad, fecha, ref)
- `outbox_eventos` (id, tipo_evento, payload_json, fecha, estado_sync)

### Definidas en el modelo, código diferido

- `lotes` (id, producto_id, lote, fecha_vencimiento, cantidad) — relación con `productos`
  y `inventario_movimientos.lote_id`. **Se define ahora** porque en carnicería/fruver saldrá
  sí o sí; evita que alguien parchee fuera del modelo más tarde.
- Maestros DIAN (`param_dian_*` o columnas reservadas arriba): **minimalistas** — espacio
  reservado y documentado, sin modelar reglas fiscales todavía (Ponytail).

## 4. Venta por peso

Un único puerto `LectorPeso` en `core/perifericos/` con tres adaptadores intercambiables:

- **`BalanzaSerial`** (pyserial): lee peso por serial/USB → fruver.
- **`CodigoPesoGS1`**: decodifica EAN-13 con prefijo de peso/precio (`2…`, estilo Chromis) → carne.
- **`IngresoManual`**: fallback sin hardware para probar el dominio hoy.

`producto.vendido_por_peso == true` dispara la solicitud de peso por cualquiera de los tres.
Cambiar de balanza o estándar = cambiar solo el adapter.

## 5. Organización del workspace

Claude Code moderno usa `CLAUDE.md` + directorio `.claude/` (no "un archivo `.claude`").

```
CLAUDE.md                     guía del proyecto + reglas Ponytail (se carga siempre)
.claude/
  settings.json               modelo por defecto, permisos de herramientas
  skills/                     pos-dominio, facturacion-dian, db-design-pos, testing-pos
  agents/                     arquitecto-pos, auditor-dian, refactor-deadcode
docs/                         funcional + técnico + plan
src/{core,caja,inventario,facturacion_dian,sync_pdv}/
scripts/                      migraciones, seed, utilidades CLI
tests/{core,inventario,caja,...}/
```

### Skills (`.claude/skills/<nombre>/SKILL.md`)

- **pos-dominio** — mapa funcional de Siesa + referencias OSPOS/uniCenta/Chromis.
  Indica explícitamente: *cargar al tocar código de negocio del POS*.
- **facturacion-dian** — mini-índice de resoluciones/anexos a cumplir + campos UBL clave
  (para que el subagente Auditor DIAN tenga estructura, no solo texto).
- **db-design-pos** — modelo de datos, tablas y relaciones del POS.
- **testing-pos** — convenciones (`test_*.py`, estructura por módulo) + lista fija de
  flujos críticos con test obligatorio.

### Subagentes (`.claude/agents/<nombre>.md`) — esto es "ECC" con lo nativo

- **arquitecto-pos** — revisa arquitectura global, organiza módulos, evalúa cambios grandes.
- **auditor-dian** — audita facturación electrónica y cumplimiento DIAN.
- **refactor-deadcode** — limpia código muerto, simplifica, aplica Ponytail.

### Ponytail y ECC (realidad del entorno)

- **Ponytail** no está instalado como plugin aquí. Se aplica como *filosofía* documentada en
  `CLAUDE.md` + `docs/ponytail.md`; `docs/ponytail-instalar.md` deja instrucciones por si
  existe en algún marketplace del usuario.
- **ECC** no es un framework instalado, pero su idea (skills + subagentes) se cubre con lo
  nativo de Claude Code. Se documenta en `docs/ecc-plan.md`.

## 6. Testing

`pytest`. El skill `testing-pos` fija:

- Convenciones: `test_*.py`, estructura espejo por módulo (`tests/core/`, etc.).
- **Flujos críticos** que siempre deben tener test: venta simple, venta por peso, devolución,
  cierre de caja con arqueo, sincronización offline→online, emisión de documento DIAN.
- Unitarios del núcleo (impuestos, precio×peso, arqueo) sin DB; integración de repositorios
  contra SQLite temporal.

## 7. Plan inicial (epics) y dependencias

| Epic | Descripción | Depende de |
|---|---|---|
| E1 | Caja / Venta (UI cobro, recibo) | E2, E4 |
| E2 | Inventario (productos, stock, movimientos) | — |
| E3 | Cierre de caja / arqueo | E1 |
| E4 | Venta por peso (`LectorPeso` + adaptadores) | E2 |
| E5 | DIAN (interfaz `EmisorDIAN` + stub) | E1, E2, modelo BD |
| E6 | Sync multi-local (outbox) | E2 |
| E7 | Reportes | E1, E3 |
| E8 | Usuarios / seguridad | — (transversal) |

**Orden de arranque:** E2 (modelo de productos/inventario) + E4 (LectorPeso) **antes** de la
UI de caja, para que la pantalla de ventas nazca sobre un dominio estable. E5–E8 quedan como
costuras diseñadas.

## 8. Fuera de alcance (hoy)

- Emisor DIAN autorizado propio (habilitación, set de pruebas).
- Sincronización multi-local en producción.
- Integración de hardware de balanza real más allá del adapter (se valida con `IngresoManual`).
- Cualquier integración con Siesa.
