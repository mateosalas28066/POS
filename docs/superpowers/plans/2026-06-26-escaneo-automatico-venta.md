# Escaneo automático en la pantalla de venta — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que al escanear un código en la pantalla de venta la línea aparezca sola en el carrito, sin diálogos ni opciones, soportando etiquetas GS1 de peso variable (balanza CAS CL3000) y EAN normal.

**Architecture:** La lógica vive en `core` (puro, testeable sin Qt/SQLite): el decodificador GS1 se extiende para distinguir peso vs precio embebido, y `ServicioVenta` gana un método `agregar_escaneado` que decide qué agregar. La UI (`pantalla_venta.py`) solo orquesta: un `QLineEdit` auto-enfocado captura el escaneo y llama al servicio.

**Tech Stack:** Python 3.11+, PySide6 (Qt6), SQLite, pytest. Decimal para todo lo monetario.

## Global Constraints

- `src/core/` NO conoce Qt ni SQLite. La lógica de escaneo/decodificación va en `core`.
- Acceso a datos solo por puertos `RepositorioX`; nada de SQL en `core`/`caja`.
- Ponytail: mínimo código, stdlib primero, YAGNI. No cablear `BalanzaSerial` (fuera de alcance).
- Todo monto en `Decimal`, redondeo a peso entero con `ROUND_HALF_UP` (ya es la convención).
- Tests `test_*.py`, estructura espejo por módulo en `tests/`.
- Spec de referencia: `docs/superpowers/specs/2026-06-26-escaneo-automatico-venta-design.md`.

---

## Mapa de archivos

| Archivo | Cambio |
|---|---|
| `src/core/perifericos/gs1.py` | `FormatoGS1.valor_es_precio`; `ResultadoGS1.valor_crudo`; función `es_peso_variable` |
| `src/core/servicio_venta.py` | `agregar(..., importe=None)`; helper puro `peso_e_importe_gs1`; método `ServicioVenta.agregar_escaneado` |
| `src/caja/contexto.py` | Campo `formato_gs1: FormatoGS1` en `ContextoApp` (default peso embebido) |
| `src/caja/pantalla_venta.py` | Campo `QLineEdit` de escaneo auto-enfocado + `_procesar_escaneo` |
| `tests/core/perifericos/test_gs1.py` | Tests de `valor_crudo`, `es_peso_variable`, default de formato |
| `tests/core/test_servicio_venta.py` | Tests de `importe`, `agregar_escaneado` (peso, precio, normal, inexistente) |
| `tests/caja/test_contexto.py` | Test del campo `formato_gs1` |
| `tests/caja/test_pantalla_venta.py` | Test del escaneo que agrega al carrito |

---

### Task 1: Extender el decodificador GS1 (peso vs precio, valor crudo, detección)

**Files:**
- Modify: `src/core/perifericos/gs1.py`
- Test: `tests/core/perifericos/test_gs1.py`

**Interfaces:**
- Consumes: nada nuevo.
- Produces:
  - `FormatoGS1` con campo extra `valor_es_precio: bool = False`.
  - `ResultadoGS1` con campo extra `valor_crudo: int` (entero de los dígitos de valor, sin escalar).
  - `decodificar_gs1(codigo: str, formato=FORMATO_PESO_DEFECTO) -> ResultadoGS1` (sin cambio de firma; ahora rellena `valor_crudo`).
  - `es_peso_variable(codigo: str, formato=FORMATO_PESO_DEFECTO) -> bool`.

- [ ] **Step 1: Escribir los tests que fallan**

Agregar al final de `tests/core/perifericos/test_gs1.py` (y extender el import de la línea 6):

```python
from core.perifericos.gs1 import (
    FORMATO_PESO_DEFECTO, CodigoPesoGS1, FormatoGS1, decodificar_gs1, es_peso_variable,
)


def test_decodifica_expone_valor_crudo():
    r = decodificar_gs1("2012340012344")
    assert r.valor_crudo == 1234  # dígitos de valor "01234" como entero, sin escalar


def test_formato_por_defecto_es_peso():
    assert FORMATO_PESO_DEFECTO.valor_es_precio is False


def test_es_peso_variable_detecta_prefijo_y_longitud():
    assert es_peso_variable("2012340012344") is True
    assert es_peso_variable("7700006") is False        # longitud != 13
    assert es_peso_variable("3012340012344") is False  # prefijo no es "2"
    assert es_peso_variable("20123A0012344") is False   # no son solo dígitos
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `cd w:/POS && python -m pytest tests/core/perifericos/test_gs1.py -v`
Expected: FAIL — `ImportError` de `es_peso_variable` / `AttributeError` de `valor_crudo`.

- [ ] **Step 3: Implementar el cambio mínimo**

En `src/core/perifericos/gs1.py`, reemplazar `FormatoGS1`, `ResultadoGS1`, `decodificar_gs1` y agregar `es_peso_variable`:

```python
@dataclass(frozen=True)
class FormatoGS1:
    prefijos: tuple[str, ...] = ("2",)  # primer dígito que marca peso variable
    ini_codigo: int = 1
    fin_codigo: int = 6   # codigo = ean[ini_codigo:fin_codigo] (5 dígitos)
    ini_valor: int = 7
    fin_valor: int = 12   # valor embebido = ean[ini_valor:fin_valor] (5 dígitos)
    decimales_valor: int = 3  # gramos -> kg (solo aplica en modo peso)
    valor_es_precio: bool = False  # True: el valor embebido es el precio total, no el peso


FORMATO_PESO_DEFECTO = FormatoGS1()


@dataclass(frozen=True)
class ResultadoGS1:
    codigo_producto: str
    peso_kg: Decimal     # interpretación como peso (valor / 10**decimales_valor)
    valor_crudo: int     # los dígitos de valor como entero, sin escalar (sirve para modo precio)


def _digito_control_ean13(doce: str) -> int:
    suma = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(doce))
    return (10 - suma % 10) % 10


def es_peso_variable(codigo: str, formato: FormatoGS1 = FORMATO_PESO_DEFECTO) -> bool:
    """¿El código escaneado es un EAN-13 de peso variable (etiqueta de balanza)?"""
    return len(codigo) == 13 and codigo.isdigit() and codigo[0] in formato.prefijos


def decodificar_gs1(codigo: str, formato: FormatoGS1 = FORMATO_PESO_DEFECTO) -> ResultadoGS1:
    if len(codigo) != 13 or not codigo.isdigit():
        raise ValueError(f"EAN-13 inválido: {codigo!r}")
    if codigo[0] not in formato.prefijos:
        raise ValueError(f"prefijo {codigo[0]!r} no es de peso variable")
    if _digito_control_ean13(codigo[:12]) != int(codigo[12]):
        raise ValueError("dígito de control EAN-13 incorrecto")
    crudo = codigo[formato.ini_valor:formato.fin_valor]
    peso_kg = Decimal(crudo) / (Decimal(10) ** formato.decimales_valor)
    return ResultadoGS1(codigo[formato.ini_codigo:formato.fin_codigo], peso_kg, int(crudo))
```

(El bloque `CodigoPesoGS1` queda igual; sigue usando `self._resultado.peso_kg`.)

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `cd w:/POS && python -m pytest tests/core/perifericos/test_gs1.py -v`
Expected: PASS (incluye los 5 tests previos sin cambios).

- [ ] **Step 5: Commit**

```bash
git add src/core/perifericos/gs1.py tests/core/perifericos/test_gs1.py
git commit -F <archivo-mensaje>
```
Mensaje: `feat(perifericos): GS1 distingue peso/precio embebido y expone es_peso_variable`
(Escribir el mensaje a un archivo y usar `git commit -F`; el heredoc corrompe contenido estructurado en este entorno.)

---

### Task 2: `ServicioVenta.agregar_escaneado` + soporte de importe embebido

**Files:**
- Modify: `src/core/servicio_venta.py`
- Test: `tests/core/test_servicio_venta.py`

**Interfaces:**
- Consumes: `decodificar_gs1`, `es_peso_variable`, `FormatoGS1`, `FORMATO_PESO_DEFECTO`, `ResultadoGS1` de `core.perifericos.gs1`.
- Produces:
  - `ServicioVenta.agregar(codigo_barras, *, cantidad=1, peso_kg=None, importe: Decimal | None = None) -> LineaVenta` — si el producto es por peso e `importe` no es None, usa `importe` como `subtotal`.
  - `peso_e_importe_gs1(resultado: ResultadoGS1, producto: Producto, valor_es_precio: bool) -> tuple[Decimal, Decimal | None]` (función pura a nivel de módulo).
  - `ServicioVenta.agregar_escaneado(codigo: str, formato: FormatoGS1 = FORMATO_PESO_DEFECTO) -> LineaVenta`.

- [ ] **Step 1: Escribir los tests que fallan**

Extender imports al inicio de `tests/core/test_servicio_venta.py`:

```python
from core.entidades import Impuesto, Producto
from core.perifericos.gs1 import FormatoGS1
from core.servicio_venta import ProductoNoEncontrado, PesoRequerido, ServicioVenta
```

Agregar el producto de balanza a los fixtures (junto a `GASEOSA`/`MANZANA`, ~línea 32):

```python
# PLU de balanza: codigo_barras de 5 dígitos que coincide con el embebido en la etiqueta GS1
PESAJE = Producto(codigo_barras="01234", nombre="Carne", precio=Decimal("4000"),
                  vendido_por_peso=True, unidad="kg", impuesto_id=20, id=3)
```

Incluir `PESAJE` en el servicio compartido (`_servicio`, ~línea 36):

```python
def _servicio() -> ServicioVenta:
    return ServicioVenta(_FakeProductos(GASEOSA, MANZANA, PESAJE),
                         _FakeImpuestos(IVA, EXCLUIDO))
```

Agregar al final del archivo:

```python
def test_agregar_por_peso_con_importe_usa_importe_como_subtotal():
    s = _servicio()
    linea = s.agregar("01234", peso_kg=Decimal("1.234"), importe=Decimal("1234"))
    assert linea.subtotal == Decimal("1234")          # usa el importe, no precio×peso
    assert linea.cantidad_o_peso == Decimal("1.234")  # el peso sigue rigiendo el inventario


def test_agregar_escaneado_peso_variable_agrega_por_peso():
    s = _servicio()
    linea = s.agregar_escaneado("2012340012344")  # codigo 01234, 1.234 kg
    assert linea.cantidad_o_peso == Decimal("1.234")
    assert linea.subtotal == Decimal("4936")  # 4000 * 1.234


def test_agregar_escaneado_codigo_normal_agrega_unidad():
    s = _servicio()
    linea = s.agregar_escaneado("B")  # Gaseosa: no es peso variable
    assert linea.cantidad_o_peso == Decimal("1")
    assert linea.subtotal == Decimal("3500")


def test_agregar_escaneado_precio_embebido_usa_importe():
    carne = Producto(codigo_barras="01234", nombre="Carne", precio=Decimal("2000"),
                     vendido_por_peso=True, unidad="kg", impuesto_id=20, id=3)
    s = ServicioVenta(_FakeProductos(carne), _FakeImpuestos(EXCLUIDO))
    linea = s.agregar_escaneado("2012340012344", FormatoGS1(valor_es_precio=True))
    assert linea.subtotal == Decimal("1234")           # importe embebido (valor crudo)
    assert linea.cantidad_o_peso == Decimal("0.617")   # 1234 / 2000


def test_agregar_escaneado_producto_inexistente_falla():
    s = ServicioVenta(_FakeProductos(), _FakeImpuestos(EXCLUIDO))
    with pytest.raises(ProductoNoEncontrado):
        s.agregar_escaneado("2012340012344")
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `cd w:/POS && python -m pytest tests/core/test_servicio_venta.py -v`
Expected: FAIL — `TypeError` (`importe` no es parámetro) y `AttributeError` (`agregar_escaneado`).

- [ ] **Step 3: Implementar el cambio mínimo**

En `src/core/servicio_venta.py`, extender el import de gs1 (debajo de los imports de `core.puertos`):

```python
from core.perifericos.gs1 import (
    FORMATO_PESO_DEFECTO, FormatoGS1, ResultadoGS1, decodificar_gs1, es_peso_variable,
)
```

Reemplazar el método `agregar` (líneas 36-63) por esta versión con `importe`:

```python
    def agregar(self, codigo_barras: str, *, cantidad: Decimal | int = 1,
                peso_kg: Decimal | None = None,
                importe: Decimal | None = None) -> LineaVenta:
        producto = self._productos.por_codigo(codigo_barras)
        if producto is None:
            raise ProductoNoEncontrado(f"producto inexistente: {codigo_barras!r}")
        tarifa = CERO
        if producto.impuesto_id is not None:
            impuesto = self._impuestos.por_id(producto.impuesto_id)
            if impuesto is not None:
                tarifa = impuesto.tarifa
        if producto.vendido_por_peso:
            if peso_kg is None:
                raise PesoRequerido(f"{producto.nombre} se vende por peso")
            cantidad_o_peso = peso_kg
            subtotal = (importe if importe is not None
                        else subtotal_por_peso(producto.precio, peso_kg))
        else:
            cantidad_o_peso = Decimal(cantidad)
            subtotal = subtotal_por_unidad(producto.precio, cantidad_o_peso)
        linea = LineaVenta(
            producto_id=producto.id,
            descripcion=producto.nombre,
            cantidad_o_peso=cantidad_o_peso,
            precio_unit=producto.precio,
            impuesto=impuesto_incluido(subtotal, tarifa),
            subtotal=subtotal,
        )
        self._lineas.append(linea)
        return linea

    def agregar_escaneado(self, codigo: str,
                          formato: FormatoGS1 = FORMATO_PESO_DEFECTO) -> LineaVenta:
        """Agrega según un código escaneado: GS1 de peso variable o EAN/PLU normal."""
        if not es_peso_variable(codigo, formato):
            return self.agregar(codigo, cantidad=1)
        resultado = decodificar_gs1(codigo, formato)
        producto = self._productos.por_codigo(resultado.codigo_producto)
        if producto is None:
            raise ProductoNoEncontrado(
                f"producto inexistente: {resultado.codigo_producto!r} (código {codigo!r})")
        if not producto.vendido_por_peso:
            raise ValueError(
                f"{producto.nombre} no se vende por peso pero el código es de peso variable")
        peso, importe = peso_e_importe_gs1(resultado, producto, formato.valor_es_precio)
        return self.agregar(resultado.codigo_producto, peso_kg=peso, importe=importe)
```

Agregar la función pura a nivel de módulo, justo después de la clase `ServicioVenta` (antes de `salidas_de_venta`):

```python
_GRAMO = Decimal("0.001")  # granularidad de peso al derivarlo desde un precio embebido


def peso_e_importe_gs1(resultado: ResultadoGS1, producto: Producto,
                       valor_es_precio: bool) -> tuple[Decimal, Decimal | None]:
    """Traduce un ResultadoGS1 a (peso_kg, importe). importe=None salvo en modo precio."""
    if not valor_es_precio:
        return resultado.peso_kg, None
    if producto.precio <= CERO:
        raise ValueError(
            f"{producto.nombre} con precio 0: no se puede derivar peso de un código de precio")
    importe = Decimal(resultado.valor_crudo)
    peso = (importe / producto.precio).quantize(_GRAMO, rounding=ROUND_HALF_UP)
    return peso, importe
```

Agregar `Producto` al import de `core.entidades` (línea 9-11) para la anotación de tipo:

```python
from core.entidades import (
    Devolucion, ItemDevolucion, LineaDevolucion, LineaVenta, MovimientoInventario,
    Pago, Producto, Venta,
)
```

(`ROUND_HALF_UP` ya está importado en la línea 6.)

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `cd w:/POS && python -m pytest tests/core/test_servicio_venta.py -v`
Expected: PASS (los 8 tests previos + los 5 nuevos).

- [ ] **Step 5: Commit**

```bash
git add src/core/servicio_venta.py tests/core/test_servicio_venta.py
git commit -F <archivo-mensaje>
```
Mensaje: `feat(core): ServicioVenta.agregar_escaneado decodifica GS1 y agrega al carrito`

---

### Task 3: Exponer `formato_gs1` en `ContextoApp`

**Files:**
- Modify: `src/caja/contexto.py`
- Test: `tests/caja/test_contexto.py`

**Interfaces:**
- Consumes: `FormatoGS1`, `FORMATO_PESO_DEFECTO` de `core.perifericos.gs1`.
- Produces: `ContextoApp.formato_gs1: FormatoGS1` (default `FORMATO_PESO_DEFECTO`). La UI lo lee para escanear.

- [ ] **Step 1: Escribir el test que falla**

Agregar a `tests/caja/test_contexto.py`:

```python
def test_contexto_expone_formato_gs1_peso_por_defecto():
    ctx = ContextoApp.crear(":memory:")
    assert ctx.formato_gs1.valor_es_precio is False
```

(Si el archivo aún no importa `ContextoApp`, agregar `from caja.contexto import ContextoApp`.)

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `cd w:/POS && python -m pytest tests/caja/test_contexto.py -v`
Expected: FAIL — `AttributeError: 'ContextoApp' object has no attribute 'formato_gs1'`.

- [ ] **Step 3: Implementar el cambio mínimo**

En `src/caja/contexto.py`, agregar el import (junto a los de `core`):

```python
from core.perifericos.gs1 import FORMATO_PESO_DEFECTO, FormatoGS1
```

Agregar el campo al `@dataclass ContextoApp`, al final de los campos (después de `svc_reportes`):

```python
    svc_reportes: ServicioReportes
    formato_gs1: FormatoGS1 = FORMATO_PESO_DEFECTO
```

(No hace falta tocar `desde_conn`: construye con keywords y el default aplica solo.)

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `cd w:/POS && python -m pytest tests/caja/test_contexto.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/caja/contexto.py tests/caja/test_contexto.py
git commit -F <archivo-mensaje>
```
Mensaje: `feat(caja): ContextoApp expone formato_gs1 (peso embebido por defecto)`

---

### Task 4: Campo de escaneo auto-enfocado en la pantalla de venta

**Files:**
- Modify: `src/caja/pantalla_venta.py`
- Test: `tests/caja/test_pantalla_venta.py`

**Interfaces:**
- Consumes: `ServicioVenta.agregar_escaneado`, `ContextoApp.formato_gs1`.
- Produces: `PantallaVenta._escaneo` (QLineEdit), `PantallaVenta._procesar_escaneo()`.

- [ ] **Step 1: Escribir el test que falla**

Agregar a `tests/caja/test_pantalla_venta.py`:

```python
def test_escanear_codigo_normal_agrega_al_carrito():
    _app = QApplication.instance() or QApplication([])
    ctx = _ctx()
    win = PantallaVenta(ctx)
    win.al_mostrar()
    win._escaneo.setText("7700006")  # Arroz, por unidad
    win._procesar_escaneo()
    assert win._carrito.rowCount() == 1
    assert win._total_actual() == Decimal("2500")
    assert win._escaneo.text() == ""  # el campo se limpia tras escanear
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `cd w:/POS && python -m pytest tests/caja/test_pantalla_venta.py::test_escanear_codigo_normal_agrega_al_carrito -v`
Expected: FAIL — `AttributeError: 'PantallaVenta' object has no attribute '_escaneo'`.

- [ ] **Step 3: Implementar el cambio mínimo**

En `src/caja/pantalla_venta.py`, dentro de `__init__`, en el bloque del carrito (después de crear `self._carrito`, antes de `self._lbl_total`), agregar el campo de escaneo:

```python
        self._escaneo = QLineEdit()
        self._escaneo.setObjectName("escaneo")
        self._escaneo.setPlaceholderText("Escanear…")
        self._escaneo.returnPressed.connect(self._procesar_escaneo)
```

Insertarlo en el layout `der`, justo después de `der.addWidget(self._carrito)`:

```python
        der.addWidget(self._carrito)
        der.addWidget(self._escaneo)
```

En `al_mostrar`, dar el foco al campo de escaneo al final:

```python
    def al_mostrar(self) -> None:
        self._construir_chips()
        self._construir_grid()
        self._refrescar_carrito()
        self._escaneo.setFocus()
```

Agregar el método `_procesar_escaneo` (junto a `_agregar_producto`):

```python
    def _procesar_escaneo(self) -> None:
        codigo = self._escaneo.text().strip()
        self._escaneo.clear()
        if not codigo:
            return
        try:
            self._venta.agregar_escaneado(codigo, self._ctx.formato_gs1)
        except (ProductoNoEncontrado, PesoRequerido, ValueError) as exc:
            self._estado.setText(f"{exc} — código: {codigo}")
            self._escaneo.setFocus()
            return
        self._estado.setText("")
        self._refrescar_carrito()
        self._escaneo.setFocus()
```

En `_registrar_pagos`, tras limpiar la venta, devolver el foco al escaneo (después de `self._refrescar_carrito()`):

```python
        self._venta = self._ctx.nueva_venta()
        self._refrescar_carrito()
        self._escaneo.setFocus()
        self.caja_cambiada.emit()
```

- [ ] **Step 4: Correr la suite de la pantalla y verificar que pasa**

Run: `cd w:/POS && python -m pytest tests/caja/test_pantalla_venta.py -v`
Expected: PASS (los 4 tests previos + el nuevo).

- [ ] **Step 5: Commit**

```bash
git add src/caja/pantalla_venta.py tests/caja/test_pantalla_venta.py
git commit -F <archivo-mensaje>
```
Mensaje: `feat(caja): campo de escaneo auto-enfocado agrega al carrito en venta`

---

### Task 5: Verificación final de toda la suite

**Files:** ninguno (verificación).

- [ ] **Step 1: Correr la suite completa**

Run: `cd w:/POS && python -m pytest -q`
Expected: PASS, sin regresiones. Si algo falla, arreglar antes de cerrar.

- [ ] **Step 2: (Opcional) Prueba manual en el local**

Levantar la app (`cd w:/POS && python -m caja`), abrir caja y escanear:
1. Un producto de empaque (EAN normal) → aparece con cantidad 1.
2. Una etiqueta de la CL3000 (carne) → aparece con peso y subtotal.
Si el peso/precio no calza, anotar los 13 dígitos crudos y ajustar `FormatoGS1` (ver "Puesta en marcha" abajo).

---

## Puesta en marcha (config real de la CL3000, sin tocar código si calza)

El default asume: prefijo `2`, código de producto en posiciones 2–6 (5 dígitos), peso en gramos en
posiciones 8–12, y **peso embebido**. Para que funcione en el local:

1. En la balanza, programar cada PLU con el **mismo número** que el `codigo_barras` del producto en
   el POS (5 dígitos para los de peso).
2. Escanear una etiqueta real y comparar los 13 dígitos con el formato default.
3. Si la balanza emite **precio** en vez de peso, o usa otras posiciones, ajustar el único punto de
   verdad: el `FormatoGS1` que entrega `ContextoApp` (p. ej. `FormatoGS1(valor_es_precio=True)`).
   No hay que tocar la lógica: está parametrizada por `FormatoGS1`.
