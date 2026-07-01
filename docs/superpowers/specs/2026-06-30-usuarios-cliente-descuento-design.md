# Diseño: Usuarios/roles + Cliente y descuento en la venta

> Epic **"Usuarios+Cliente"** del [mapa del proyecto](../../README-pos.md) (slug: `usuarios-cliente-descuento`).
> Deriva del [spec maestro](2026-06-25-pos-siesa-remake-design.md).
> Fecha: 2026-06-30 · Estado: aprobado para materializar (implementación pendiente).

## 1. Problema

Dos huecos del POS que ya tienen "costura" en el modelo pero no están cableados:

- **Usuarios — no existe nada hoy.** El campo `usuario_id` viaja en `Venta`, `CajaSesion` y
  `Devolucion`, y la tabla `usuarios` existe (migración `002`), pero no hay entidad `Usuario`,
  ni autenticación, ni roles, ni pantalla. Toda operación queda con `usuario_id = None` y
  cualquiera puede hacer cualquier cosa.
- **Cliente en la venta — el maestro existe, no se usa al vender.** `ServicioClientes` y el
  seed "Consumidor final" existen, y `Venta.cliente_id` / `ServicioVenta.confirmar(cliente_id=…)`
  lo aceptan, pero `pantalla_venta.py` nunca selecciona cliente. No hay ningún concepto de
  descuento.

Este epic autentica al operador, traza quién hace cada operación, restringe unas pocas acciones
sensibles, y permite vender a un cliente con descuento porcentual.

## 2. Alcance

### Dentro

**Usuarios / seguridad**
- Login usuario + contraseña al iniciar la app; `hash` con `hashlib.pbkdf2_hmac` + sal por
  usuario (stdlib, sin dependencias nuevas).
- Dos roles: `admin` y `cajero`.
- Permisos: tres acciones **solo admin** — gestionar usuarios, editar productos/precios y
  aplicar descuento manual. El cajero puede vender, cobrar, abrir/cerrar caja, anular y devolver.
- `usuario_actual` vive en `ContextoApp`; `usuario_id` se cablea en venta, cierre y devolución.
- CRUD de usuarios (pantalla admin-only).

**Cliente / descuento**
- Selección de cliente en la pantalla de venta, con **default consumidor final**.
- Descuento **porcentual por cliente** (campo `descuento_pct` en `Cliente`), aplicado **por línea**
  recalculando el IVA incluido, con redondeo `ROUND_HALF_UP` a peso entero (igual que el dominio hoy).
- Descuento manual (porcentual) en la venta, que sobreescribe el del cliente; solo admin.
- Persistencia: se guarda el `descuento_pct` aplicado en `ventas`; el `subtotal` de cada línea ya
  es el neto (no se agregan columnas a `venta_lineas`).
- Enforce de `bloqueado_edicion` al actualizar un cliente.

### Fuera (YAGNI)

- Descuento por línea individual, por producto o por grupo/categoría.
- Descuento por monto fijo (solo porcentual).
- Enforcement de permisos en la capa de servicios (hoy: login + gating de UI).
- Recuperación / expiración de contraseña, cambio de contraseña autoservicio.
- Múltiples cajas o turnos simultáneos, auditoría detallada de descuentos manuales.
- Nuevas agregaciones en reportes (el descuento total por venta es derivable, ver §5).

## 3. Modelo de datos

Migración nueva `scripts/migraciones/005_usuarios_descuento.sql` (idempotente):

```sql
-- Unicidad de nombre de usuario (login).
CREATE UNIQUE INDEX IF NOT EXISTS idx_usuarios_nombre ON usuarios(nombre);

-- Descuento porcentual del cliente (fracción 0..1; 0 = sin descuento).
ALTER TABLE clientes ADD COLUMN descuento_pct DECIMAL NOT NULL DEFAULT '0';

-- Descuento porcentual aplicado a la venta (cliente o manual). Para recibo/reportes.
ALTER TABLE ventas ADD COLUMN descuento_pct DECIMAL NOT NULL DEFAULT '0';
```

Notas:
- La tabla `usuarios (id, nombre, rol, hash_password)` ya existe (`002_ventas.sql`); solo se
  agrega el índice único. `hash_password` almacena todo en una columna con formato
  `pbkdf2_sha256$<iteraciones>$<sal_hex>$<hash_hex>`.
- No se tocan `venta_lineas`: el `subtotal` guardado ya es el neto con descuento aplicado. El
  bruto por línea es derivable de `precio_unit × cantidad_o_peso` (ambos ya persistidos).
- `ALTER TABLE … ADD COLUMN` con `DEFAULT` es compatible SQLite→PostgreSQL.

### Seed del admin por defecto (bootstrap, no SQL)

El hash no puede generarse en SQL. Al iniciar, si la tabla `usuarios` está vacía, el bootstrap
crea un admin por defecto (`nombre="admin"`, contraseña inicial documentada, `rol="admin"`) para
poder entrar la primera vez. Es idempotente (solo si no hay usuarios).

## 4. Entidades y puertos (`core/`, Python puro)

### Entidades (`core/entidades.py`)

- **Nueva** `Usuario`:
  ```python
  @dataclass(frozen=True)
  class Usuario:
      nombre: str
      rol: str = "cajero"          # ROLES = ("admin", "cajero")
      id: int | None = None
      # __post_init__: rol ∈ ROLES; nombre no vacío
  ```
  La credencial (hash) **no** vive en la entidad; es una preocupación de persistencia/auth.

- `Cliente` gana `descuento_pct: Decimal = CERO` (valida `0 ≤ pct < 1`).
- `Venta` gana `descuento_pct: Decimal = CERO` (valida `0 ≤ pct < 1`). `LineaVenta` **sin cambios**.

### Seguridad (`core/seguridad.py`, nuevo)

Funciones puras stdlib (`hashlib`, `secrets`, `hmac`):
- `hash_password(pwd: str) -> str` — genera sal y devuelve el string codificado.
- `verificar(pwd: str, codificado: str) -> bool` — comparación en tiempo constante (`hmac.compare_digest`).

### Permisos (`core/permisos.py`, nuevo)

```python
ACCION_GESTIONAR_USUARIOS = "gestionar_usuarios"
ACCION_EDITAR_PRODUCTOS   = "editar_productos"
ACCION_DESCUENTO_MANUAL   = "aplicar_descuento_manual"
PERMISOS_ADMIN = frozenset({ACCION_GESTIONAR_USUARIOS, ACCION_EDITAR_PRODUCTOS,
                            ACCION_DESCUENTO_MANUAL})

def puede(rol: str, accion: str) -> bool:
    return rol == "admin" or accion not in PERMISOS_ADMIN
```

### Puerto (`core/puertos.py`)

```python
class RepositorioUsuarios(Protocol):
    def guardar(self, usuario: Usuario, hash_password: str) -> Usuario: ...
    def por_id(self, id: int) -> Usuario | None: ...
    def por_nombre(self, nombre: str) -> Usuario | None: ...
    def credencial(self, nombre: str) -> tuple[Usuario, str] | None: ...  # (usuario, hash)
    def listar(self) -> list[Usuario]: ...
```

`RepositorioClientes` gana `descuento_pct` de forma transparente (mismo `guardar/actualizar`,
solo cambia el SQL del adaptador). No cambia su firma.

### Servicios (`core/`)

- **`ServicioUsuarios`** (`core/servicio_usuarios.py`, nuevo):
  - `crear(nombre, password, rol="cajero") -> Usuario` — valida, hashea, rechaza nombre duplicado.
  - `autenticar(nombre, password) -> Usuario | None`.
  - `listar() -> list[Usuario]`.
- **`ServicioVenta`** (`core/servicio_venta.py`):
  - Nuevo atributo `descuento_pct` (default `CERO`) y `establecer_descuento(pct)` que valida y
    **recomputa** las líneas existentes (mismo patrón de reconstrucción que usa hoy la UI al
    quitar una línea).
  - `agregar(...)`: `subtotal_bruto` como hoy; `subtotal_neto = (subtotal_bruto * (1 - pct))`
    cuantizado a peso con `ROUND_HALF_UP`; `impuesto = impuesto_incluido(subtotal_neto, tarifa)`.
  - `confirmar(...)` incluye `descuento_pct=self.descuento_pct` en la `Venta`.
- **`ServicioClientes.actualizar`**: lanza `ClienteBloqueado(ValueError)` si el cliente destino
  tiene `bloqueado_edicion`.

### Cálculo (`core/calculos.py`)

Helper mínimo reutilizable y testeable sin DB:
```python
def aplicar_descuento(subtotal_bruto: Decimal, pct: Decimal) -> Decimal:
    """Subtotal neto tras descuento porcentual, redondeado a peso entero (ROUND_HALF_UP)."""
```

## 5. Reglas de dominio y casos límite

**Descuento por línea con IVA incluido**
- El precio es IVA incluido; el descuento reduce proporcionalmente base e IVA. Por eso el IVA se
  **recalcula** sobre el subtotal neto: `impuesto_incluido(neto, tarifa)`. Total venta = Σ netos.
- **Redondeo:** primero se aplica el descuento, luego se cuantiza a peso entero por línea
  (`ROUND_HALF_UP`), consistente con `subtotal_por_unidad/peso` actuales. El total es la suma de
  líneas ya redondeadas (no se redondea dos veces).
- `pct = 0` (consumidor final / sin cliente): comportamiento idéntico al actual.
- `pct` alto que lleve un `subtotal_neto` a 0: permitido (`LineaVenta.subtotal ≥ 0`), `impuesto = 0`.
- Validación: `0 ≤ pct < 1` en `Cliente`, `Venta` y `establecer_descuento` (100% no permitido).

**Descuento manual vs cliente**
- Al seleccionar cliente se aplica su `descuento_pct`. El descuento manual (solo admin)
  **sobreescribe** el valor de la venta; no se acumulan.

**Persistencia y recibo**
- Se guarda `ventas.descuento_pct`. El recibo puede mostrar `Subtotal`, `Descuento (X%)` y `Total`:
  el monto descontado = `Σ round(precio_unit × cantidad_o_peso) − total` (derivado de datos ya
  persistidos). No se requieren columnas en `venta_lineas`.

**Cliente bloqueado**
- `bloqueado_edicion` bloquea **editar el maestro** (`actualizar` lanza), no vender a ese cliente.

**Permisos**
- `puede(rol, accion)` es la única fuente de verdad. El cajero no puede: gestionar usuarios,
  editar productos/precios, aplicar descuento manual. Admin puede todo.

**Autenticación**
- `autenticar` devuelve `None` si el usuario no existe o la contraseña no verifica (sin distinguir
  cuál, para no filtrar existencia). Comparación en tiempo constante.

## 6. Impacto en UI (`caja/`)

- **`DialogoLogin`** (nuevo): se muestra antes de construir `VentanaPrincipal`; en `__main__`.
  Autentica contra `ServicioUsuarios`; al éxito setea `ContextoApp.usuario_actual`.
- **`ContextoApp`**: gana `repo_usuarios`, `svc_usuarios` y `usuario_actual: Usuario | None`.
- **`pantalla_venta.py`**:
  - Selector de cliente (default consumidor final); al elegir, `establecer_descuento(cliente.descuento_pct)`
    y refresco del carrito.
  - Campo de descuento manual visible solo si `puede(rol, ACCION_DESCUENTO_MANUAL)`.
  - `confirmar(..., cliente_id=<cliente>.id, usuario_id=ctx.usuario_actual.id)`.
- **`pantalla_cierre.py`** / **`pantalla_devoluciones.py`**: pasar `usuario_id=ctx.usuario_actual.id`
  a `svc_caja.abrir/cerrar` y `svc_devolucion.devolver` (los servicios ya lo aceptan).
- **`PantallaUsuarios`** (nueva, admin-only): CRUD estilo `PantallaClientes`.
- **`ventana_principal.py`**: el rail oculta/inhabilita las pantallas admin-only según
  `puede(rol, …)` (Usuarios; edición en Inventario).
- **Enforcement:** el login es el gate real; `puede()` gatea controles/pantallas en la UI. El
  enforcement dentro de servicios queda como endurecimiento futuro (Ponytail: no se construye hoy).

## 7. Tests (flujos críticos)

- **`core` (sin DB):** `hash_password`/`verificar` (incl. contraseña incorrecta); `puede()` por
  rol×acción; `ServicioUsuarios.autenticar` (ok / usuario inexistente / clave mala) y `crear`
  (duplicado); `aplicar_descuento` y descuento por línea con IVA incluido + redondeo (pct=0,
  pct normal, pct→neto 0); `ServicioClientes.actualizar` con `bloqueado_edicion`.
- **`ventas` (SQLite temporal):** `RepositorioUsuariosSQLite` (guardar/credencial/por_nombre,
  unicidad de nombre); `clientes.descuento_pct` y `ventas.descuento_pct` persisten y releen;
  bootstrap del admin por defecto solo cuando no hay usuarios.
- **`caja` (offscreen + `importorskip`):** `DialogoLogin` (éxito/fallo); gating por rol en el rail;
  seleccionar cliente aplica descuento y recomputa; `PantallaUsuarios` crea usuario.

## 8. Orden de construcción (resumen; detalle en el plan)

Dominio → persistencia → UI, TDD test-first:
seguridad/permisos → entidad `Usuario` + `ServicioUsuarios` → puerto/adaptador `RepositorioUsuarios`
→ `Cliente/Venta.descuento_pct` + `aplicar_descuento` + `ServicioVenta` → migración `005` + adaptadores
→ `ContextoApp` + `DialogoLogin` → cableado `usuario_id` → cliente/descuento en `pantalla_venta`
→ `PantallaUsuarios` + gating del rail → README.
