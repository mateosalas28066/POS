---
name: testing-pos
description: Use when writing or reorganizing tests for pos-siesa-remake. Defines pytest conventions, mirror structure per module, and the fixed list of critical POS flows that must always have tests.
---

# Testing del POS (pos-siesa-remake)

Cargar al escribir o reorganizar pruebas. Framework: **pytest**.

## Convenciones

- Archivos `test_*.py`; estructura **espejo** por módulo: `tests/core/`, `tests/inventario/`,
  `tests/caja/`, etc.
- Unitarios del núcleo **sin DB** (lógica pura: impuestos, precio×peso, arqueo).
- Integración de repositorios contra **SQLite temporal** (`:memory:` o tmp_path), no la BD real.
- La UI Qt se prueba lo mínimo: extraer la lógica a `core`/servicios y testear eso; la ventana
  solo como smoke test si aporta.

## Flujos críticos con test obligatorio

Estos flujos **siempre** deben tener prueba (no se mergea sin ellos):

1. **Venta simple** — agregar ítems, calcular total con impuestos, cobrar.
2. **Venta por peso** — precio×peso por los tres adaptadores `LectorPeso` (manual, GS1, balanza simulada).
3. **Devolución** — reversa de una venta y su efecto en inventario.
4. **Cierre de caja con arqueo** — cuadre de efectivo y medios de pago.
5. **Sincronización offline→online** — encolar en `outbox_eventos` y procesar (cuando exista E6).
6. **Emisión de documento DIAN** — el `EmisorStub` recibe el documento bien armado por `core`.

## Principios

- Tests primero donde tenga sentido (TDD para reglas de negocio del núcleo).
- Dobles de prueba para puertos: `LectorPeso`, `RepositorioX`, `EmisorDIAN` se sustituyen por fakes.
- Un test = un comportamiento; nombres descriptivos en español del dominio.
