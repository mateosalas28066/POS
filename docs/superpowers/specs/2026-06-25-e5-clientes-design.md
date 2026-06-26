# E5 — Clientes (diseño)

> Spec maestro: [2026-06-25-pos-siesa-remake-design.md](2026-06-25-pos-siesa-remake-design.md)
> Mapa: [../../README-pos.md](../../README-pos.md)
> Fecha: 2026-06-25

## Objetivo

Completar el **maestro de clientes** como dominio con reglas de negocio y exponer
la **primera pantalla CRUD** de gestión de clientes, reutilizando la infraestructura
que ya existe (entidad, puerto, adaptador SQLite, `cliente_id` en ventas) y siguiendo
el patrón Qt ya establecido por `PantallaVenta`.

No inaugura la UI: ya existe UI Qt (`src/caja/pantalla_venta.py` + launcher
`scripts/caja.py` + test offscreen). E5 se suma a ese patrón.

## Estado de partida (ya implementado)

- Entidad `Cliente` con campos reservados DIAN (`tipo_documento`, `regimen`,
  `tipo_responsabilidad`) y flag `bloqueado_edicion`.
- Puerto `RepositorioClientes` (`guardar`, `por_id`, `por_identificacion`, `listar`).
- Adaptador `RepositorioClientesSQLite` + tabla `clientes`
  (`identificacion TEXT NOT NULL UNIQUE`).
- Las ventas ya referencian `cliente_id` (NULLABLE).

## Decisiones de alcance

| Tema | Decisión |
|---|---|
| Alcance | Backend/dominio **+ UI Qt mínima** (ventana CRUD ejecutable). |
| `bloqueado_edicion` | **Solo flag informativo, sin enforcement.** La restricción por permisos se difiere a E8 (usuarios/seguridad). Costura documentada. |
| Consumidor final | Cliente sembrado (`222222222222`), expuesto por `ServicioClientes.consumidor_final()`. |
| Forma de la UI | Ventana CRUD ejecutable por su cuenta vía launcher de demo. |
| Pruebas de UI | Widget delgado, **sin `pytest-qt`**. Lógica en `ServicioClientes` (pytest puro); widget probado con el patrón offscreen + `importorskip` que ya usa `test_pantalla_venta.py`. |

## Componentes

### 1. Dominio — `src/core/servicio_clientes.py` (nuevo)

`ServicioClientes(repo: RepositorioClientes)`. Reglas que hoy faltan:

- `crear(identificacion, nombre, contacto=None, *, tipo_documento=None, regimen=None, tipo_responsabilidad=None) -> Cliente`
  - Valida `identificacion` y `nombre` no vacíos (`ValueError`).
  - Traduce el duplicado (`sqlite3.IntegrityError` por el `UNIQUE`) a un error de
    dominio limpio: `ValueError("ya existe cliente con identificación …")`.
- `actualizar(cliente: Cliente) -> Cliente`
  - Exige `cliente.id is not None` (`ValueError` si falta).
  - Persiste vía puerto. **No** comprueba `bloqueado_edicion` (costura E8).
- `buscar(identificacion) -> Cliente | None`
- `listar() -> list[Cliente]`
- `consumidor_final() -> Cliente`
  - Busca el cliente bien-conocido por la constante de módulo
    `IDENTIFICACION_CONSUMIDOR_FINAL = "222222222222"`.

El servicio no conoce Qt ni SQLite (regla de oro hexagonal).

### 2. Puerto — `src/core/puertos.py`

Añadir al `Protocol RepositorioClientes`:

```python
def actualizar(self, cliente: Cliente) -> Cliente: ...
```

### 3. Adaptador — `src/ventas/repositorio_sqlite.py`

Implementar `RepositorioClientesSQLite.actualizar`:

- `UPDATE clientes SET … WHERE id = ?` sobre las mismas columnas que `guardar`.
- **Lección de E3.b:** si `cur.rowcount == 0`, lanzar `LookupError`
  (no repetir el no-op silencioso diferido de `anular`).
- `commit()` y devolver el cliente.

### 4. Seed — `scripts/migraciones/003_consumidor_final.sql` (nuevo)

```sql
INSERT OR IGNORE INTO clientes (identificacion, nombre)
VALUES ('222222222222', 'Consumidor final');
```

Idempotente gracias al `UNIQUE` sobre `identificacion`. Se aplica con el resto de
migraciones (no fuerza un `id` fijo; `consumidor_final()` resuelve por identificación).

### 5. UI — `src/caja/pantalla_clientes.py` (nuevo) + `scripts/clientes.py` (launcher)

`PantallaClientes(QWidget)` — vista delgada al estilo `PantallaVenta`:

- Tabla con el listado (`listar()`), refrescada tras cada operación.
- Form: identificación, nombre, contacto.
- Botones **Crear** y **Guardar** (editar el seleccionado), campo de **búsqueda**
  por identificación.
- Solo cablea señales → `ServicioClientes`. Los `ValueError` de dominio se muestran
  en un label de estado propio (`_estado`), siguiendo el patrón de `PantallaVenta`
  (que reutiliza su label `_total` con `setText(f"Error: {exc}")`).

`scripts/clientes.py` — launcher espejo de `scripts/caja.py`: conecta la BD, aplica
migraciones, construye `ServicioClientes(RepositorioClientesSQLite(conn))`, muestra
la ventana.

### 6. Pruebas

- `tests/core/test_servicio_clientes.py` — repo fake; cubre: crear, duplicado
  rechazado, `actualizar` (incl. exigir `id`), `buscar`, `consumidor_final`.
- `tests/ventas/test_repositorio_clientes.py` — adaptador real sobre SQLite en
  memoria; cubre `actualizar` (incl. `LookupError` si el id no existe) y que el seed
  del consumidor final queda disponible.
- `tests/caja/test_pantalla_clientes.py` — patrón offscreen + `importorskip("PySide6")`;
  cubre crear → la tabla se refresca con la nueva fila.

## Flujo de datos

```
UI (PantallaClientes) → ServicioClientes → RepositorioClientes (SQLite) → tabla clientes
```

El core permanece sin Qt. Las validaciones de dominio lanzan `ValueError`; la UI las
captura y muestra en su label de estado.

## Fuera de alcance

- Enforcement de `bloqueado_edicion` por permisos → E8.
- Descuentos por cliente/grupo → futuro.
- Asignar cliente a la venta desde la pantalla de venta (integración UI venta↔cliente)
  → futuro; E5 solo entrega el maestro y el consumidor final como costura.

## Cierre (housekeeping)

- Actualizar `docs/README-pos.md`: marcar E5 como implementado y corregir la fila E1
  (la UI Qt ya existe como prototipo, no está "pendiente").
- Actualizar el conteo de la suite tras añadir las pruebas de E5.
