# pos-siesa-remake

POS autónomo (Python + PySide6 + SQLite) que reemplaza el POS de Siesa sobre Linux Debian,
para un negocio de **carnes y frutas**. Offline-first, una caja hoy; costuras para multi-local
y facturación electrónica DIAN mañana.

> Spec de referencia: [docs/superpowers/specs/2026-06-25-pos-siesa-remake-design.md](docs/superpowers/specs/2026-06-25-pos-siesa-remake-design.md)
> Mapa del proyecto: [docs/README-pos.md](docs/README-pos.md)

## Stack

- **Python 3.11+** — toda la lógica (negocio, DIAN, sync) en un solo lenguaje.
- **PySide6 (Qt6)** — interfaz de caja: liviana en hardware viejo, moderna con temas QSS.
- **SQLite** — persistencia local offline; ruta a PostgreSQL para multi-local.
- **pytest** — pruebas.

## Arquitectura (hexagonal / puertos y adaptadores)

**Regla de oro:** `src/core/` NO conoce Qt ni SQLite. Solo entidades, reglas de negocio y
puertos (interfaces). Los adaptadores concretos (SQLite, balanza, DIAN) se enchufan por
inyección de dependencias.

**Aislamiento estricto (no negociable):** `inventario/`, `caja/` y `sync_pdv/` acceden a datos
**solo** vía puertos `RepositorioX` de `core`. Prohibido SQL fuera de los adaptadores de
repositorio. Las reglas fiscales DIAN viven en `core`; `facturacion_dian/` solo transporta/firma.

| Módulo | Responsabilidad |
|---|---|
| `src/core/` | Entidades, reglas (impuestos, precio×peso, arqueo), puertos, armado de factura DIAN |
| `src/core/perifericos/` | Puerto `LectorPeso` + adaptadores `BalanzaSerial`, `CodigoPesoGS1`, `IngresoManual` |
| `src/inventario/` | Productos, stock, movimientos (adaptadores SQLite) |
| `src/caja/` | UI Qt: venta, cobro, devoluciones, cierre/arqueo |
| `src/facturacion_dian/` | Puerto `EmisorDIAN` + adaptadores (stub hoy, proveedor después) |
| `src/sync_pdv/` | Patrón outbox para multi-local (diseñado, no implementado a fondo) |

## Reglas Ponytail (filosofía: mínimo código necesario)

Antes de escribir cualquier código, en orden:

1. **¿Hace falta de verdad?** Si no resuelve un requisito real y presente, no se escribe (YAGNI).
2. **¿Lo resuelve la stdlib?** Preferir biblioteca estándar antes que dependencias nuevas.
3. **¿Es nativo / ya existe?** Reutilizar lo que el framework (Qt, sqlite3) ya ofrece.
4. **¿Se puede más simple / en menos líneas?** Sin sacrificar legibilidad.

Detalle: [docs/ponytail.md](docs/ponytail.md).

## Skills y subagentes (esto es "ECC" con lo nativo de Claude Code)

**Cargar el skill correspondiente según la tarea:**

- `pos-dominio` — al tocar **cualquier código de negocio del POS** (mapa funcional de Siesa + referencias open source).
- `facturacion-dian` — al trabajar en facturación electrónica / cumplimiento DIAN.
- `db-design-pos` — al diseñar o modificar el modelo de datos / tablas.
- `testing-pos` — al escribir o reorganizar pruebas.

**Subagentes** (`.claude/agents/`):

- `arquitecto-pos` — revisar arquitectura global y cambios grandes.
- `auditor-dian` — auditar facturación electrónica y cumplimiento DIAN.
- `refactor-deadcode` — limpiar código muerto, simplificar, aplicar Ponytail.

Plan de uso: [docs/ecc-plan.md](docs/ecc-plan.md).

## Convenciones

- Nombres de dominio en español (coinciden con el negocio: `Producto`, `Venta`, `Caja`).
- Tests: `test_*.py`, estructura espejo por módulo en `tests/`.
- No acceder a SQL fuera de los adaptadores de repositorio.
