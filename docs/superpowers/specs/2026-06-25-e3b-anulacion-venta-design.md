# E3.b — Anulación de venta (sin dinero) — Diseño

> Estado: aprobado (2026-06-25). Siguiente paso: plan de implementación (skill `writing-plans`).
> Contexto: cierra parcialmente el **flujo crítico #3** (devolución/anulación) del POS, diferido en
> [E3](../plans/2026-06-25-e3-cierre-caja-arqueo.md).

## Objetivo

Permitir **anular una venta `pagada`**: revertir el inventario que la venta descontó y marcar la
venta como `anulada`. **No mueve dinero**: no hay reembolso, no toca `pagos` ni el arqueo.

Alcance explícitamente acotado (decisiones del usuario, 2026-06-25):

- **Solo anulación total**, no devolución parcial por línea.
- **Sin reembolso** ni registro de medios de pago de salida.
- **Solo dominio + persistencia + tests.** Sin UI Qt (coherente con E3, que dejó `PantallaCierre`
  diferida).

## Principio de diseño

Anular es la operación **inversa** de registrar. `ServicioRegistroVenta` hace `salida` de stock y
deja la venta `pagada`; `ServicioAnulacion` hace `entrada` de stock y deja la venta `anulada`.
Simétrico, mínimo código (Ponytail), reutiliza lo existente.

## Componentes

### 1. Dominio (`src/core/`) — sin entidad nueva

`Venta.estado` ya admite `("pagada", "anulada")` con validación en `__post_init__`; no se crea
entidad ni se modifica el modelo de datos.

**Función pura** en [`src/core/servicio_venta.py`](../../../src/core/servicio_venta.py), espejo de
`salidas_de_venta`:

```python
def entradas_de_anulacion(venta: Venta) -> list[MovimientoInventario]:
    return [
        MovimientoInventario(
            producto_id=linea.producto_id,
            tipo="entrada",
            cantidad=linea.cantidad_o_peso,   # sirve para unidad y para peso
            fecha=venta.fecha,
            ref=f"anulacion:{venta.id}",
        )
        for linea in venta.lineas
    ]
```

**Servicio** `ServicioAnulacion(ventas, inventario)` (mismo patrón que `ServicioRegistroVenta`):

```python
class ServicioAnulacion:
    def __init__(self, ventas: RepositorioVentas, inventario: RepositorioInventario) -> None: ...

    def anular(self, venta_id: int) -> Venta:
        venta = self._ventas.por_id(venta_id)
        if venta is None:
            raise VentaNoEncontrada(...)
        if venta.estado == "anulada":
            raise VentaYaAnulada(...)          # evita doble reposición de stock
        self._ventas.anular(venta_id)
        for movimiento in entradas_de_anulacion(venta):
            self._inventario.registrar(movimiento)
        return replace(venta, estado="anulada")
```

Excepciones nuevas (subclases de `ValueError`, como `ProductoNoEncontrado`/`PesoRequerido`):
`VentaNoEncontrada`, `VentaYaAnulada`.

### 2. Puerto `RepositorioVentas` (`src/core/puertos.py`)

Un método nuevo:

```python
def anular(self, venta_id: int) -> None: ...
```

### 3. Persistencia (`src/ventas/repositorio_sqlite.py`)

Implementa `anular` (único lugar con SQL):

```python
def anular(self, venta_id: int) -> None:
    self._conn.execute("UPDATE ventas SET estado = 'anulada' WHERE id = ?", (venta_id,))
    self._conn.commit()
```

**No requiere migración:** la columna `ventas.estado` ya existe (migración `002_ventas.sql`).

### 4. Inventario — sin cambios

`ServicioAnulacion` usa el `RepositorioInventario.registrar` existente.

## Efecto sobre el arqueo (clave: "sin dinero")

`RepositorioVentas.totales_por_medio` ya filtra `v.estado = 'pagada'`. Por lo tanto, una venta
anulada **desaparece automáticamente** del cuadre por medio, sin tocar la tabla `pagos`. No se
necesita lógica adicional de dinero.

## Decisión registrada

**Se permite anular una venta aunque su sesión de caja ya esté cerrada.** El arqueo de una sesión
cerrada quedó congelado en `monto_contado`; anular después solo repone inventario y no reescribe un
cuadre ya firmado. Es el comportamiento más simple y no rompe invariantes. (Si el negocio luego
exige bloquearlo, se añade un guard que compare contra la sesión abierta.)

## Atomicidad

`anular` (UPDATE) y los movimientos de `entrada` comparten la `conn` pero hacen `commit()` propio,
igual que `ServicioRegistroVenta`. Aceptable para una caja offline de un solo cajón; el envoltorio
transaccional único es el mismo refinamiento futuro ya anotado en E3.

## Tests

**Flujo crítico #3 (integración, `tests/ventas/`):**
vender (descuenta stock) → anular → afirmar:
- `venta.estado == "anulada"`,
- stock del producto **vuelto al valor previo a la venta**,
- la venta **ya no aparece** en `totales_por_medio` de su sesión.

**Dominio (`tests/core/`):**
- doble anulación lanza `VentaYaAnulada` (no repone stock dos veces),
- anular venta inexistente lanza `VentaNoEncontrada`,
- `entradas_de_anulacion` produce una `entrada` por línea con `ref="anulacion:<id>"`.

## Fuera de alcance (costura, YAGNI)

- Devolución parcial por línea y documento `Devolucion` independiente.
- Reembolsos por medio de pago y su reflejo en el arqueo.
- UI Qt de anulación/devolución.
- Nota crédito DIAN (cuando llegue E5, `ServicioAnulacion` se generaliza a devolución parcial).
- Auditoría extendida (quién/cuándo anuló): hoy el rastro es el `MovimientoInventario` con
  `ref="anulacion:<id>"` y su `fecha`.
