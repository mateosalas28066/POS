# Escaneo automático en la pantalla de venta

**Fecha:** 2026-06-26
**Estado:** aprobado (diseño)
**Módulos tocados:** `src/core/perifericos/gs1.py`, `src/core/servicio_venta.py`, `src/caja/pantalla_venta.py`, tests espejo.

## Problema

El POS ya tiene los adaptadores de periféricos (`decodificar_gs1`, `CodigoPesoGS1`,
`BalanzaSerial`, `IngresoManual`) pero **ninguno está cableado a la UI**. Hoy la única forma de
agregar al carrito es hacer clic en las tarjetas del catálogo, y el peso se teclea en un diálogo.
El scanner no agrega nada (escribe en el buscador, que solo filtra).

El negocio (carnes y frutas) usa una balanza **CAS CL3000-30B**, que es una **etiquetadora**: pesa,
calcula y **imprime una etiqueta con código de barras** que lleva embebido el PLU del producto y el
peso (o el precio total). El flujo correcto es: el cajero **escanea esa etiqueta** y la línea aparece
sola. Para productos de empaque, se escanea su EAN normal.

## Objetivo

Escanear → la línea aparece automáticamente en el carrito. Sin diálogos, sin opciones, sin clics.

**Fuera de alcance:** balanza serial en vivo (`BalanzaSerial`). La CL3000 es etiquetadora; no se
conecta por serial para esta operación. El adaptador se deja como está, sin cablear.

## Diseño

### 1. Captura del escaneo (UI)

Un scanner USB se comporta como teclado: teclea los dígitos y emite `Enter`.

- Se agrega un `QLineEdit` de escaneo en el panel del carrito (derecha), discreto, con placeholder
  "Escanear…". Se auto-enfoca en `al_mostrar()` y se vuelve a enfocar tras cada escaneo y tras cada
  cobro. El cajero nunca lo toca a mano; el scanner escribe ahí.
- `returnPressed` → procesa el contenido, limpia el campo y reenfoca.
- El cajero también puede teclear un código y presionar Enter (mismo camino).
- El buscador del catálogo existente se mantiene igual (navegación manual por nombre/código).

**Descartado:** filtro de eventos global con detección de ráfagas del scanner. Más código y riesgo
de tragarse teclas legítimas; rompe Ponytail.

### 2. Lógica al recibir un código

Función pura nueva en `core` que, dado el código escaneado + `FormatoGS1` + el repositorio de
productos, decide qué agregar:

1. **Código de peso variable** (largo 13, dígitos, primer dígito en `formato.prefijos`, p. ej. `2`):
   se decodifica con `decodificar_gs1` → `(codigo_producto, valor)`.
   - Modo **peso embebido** (`valor_es_precio = False`): `valor` son los kg.
     Línea con `peso_kg = valor`, `subtotal = peso × precio` (camino actual de `ServicioVenta`).
   - Modo **precio embebido** (`valor_es_precio = True`): `valor` es el total en pesos.
     `subtotal = valor` (importe directo) y `peso_kg = valor ÷ precio_kg` (para descontar inventario).
2. **Código normal** (no coincide con el patrón de peso variable): se agrega con `cantidad = 1`.
3. **Error** (producto inexistente, código malformado, dígito de control GS1 incorrecto): **no** abre
   diálogo. Muestra el mensaje en la etiqueta de estado **incluyendo el código crudo escaneado**, para
   poder diagnosticar el formato real de la CL3000 durante la puesta en marcha.

### 3. Ubicación según arquitectura hexagonal

- Decodificación GS1: sigue en `core/perifericos/gs1.py`.
- `FormatoGS1` gana un campo `valor_es_precio: bool = False`. El valor real para la CL3000 se
  confirma escaneando una etiqueta en el local; el default queda en peso embebido hasta confirmarlo.
- La conversión "`ResultadoGS1` + `Producto` → `(peso_kg, subtotal_override | None)`" es un **helper
  puro en core**, testeable sin Qt ni SQLite.
- `ServicioVenta.agregar` recibe un parámetro opcional `importe: Decimal | None`. Cuando se pasa
  para un producto de peso, se usa como `subtotal` de la línea (en vez de `peso × precio`), y el
  `cantidad_o_peso` registrado sigue siendo el peso (recibido o derivado) para el inventario.
- `pantalla_venta.py` solo orquesta: lee el campo, llama al helper, refresca el carrito. Sin SQL,
  sin reglas de negocio.

### 4. Convención de datos (puesta en marcha)

El código embebido en la etiqueta son **5 dígitos = el PLU programado en la CL3000**. Para que el
POS encuentre el producto, ese PLU debe coincidir exactamente con el `codigo_barras` del producto en
el maestro (`RepositorioProductos.por_codigo`).

- Productos de peso (carnes, frutas pesadas): `codigo_barras` = el PLU de 5 dígitos de la balanza.
- Productos de empaque: `codigo_barras` = su EAN real impreso.

No cambia el esquema de datos. Es una convención de captura de maestros.

### 5. Manejo de errores

| Caso | Comportamiento |
|---|---|
| Producto inexistente | Etiqueta de estado: mensaje + código crudo. No agrega. |
| EAN-13 con dígito de control inválido | Igual: mensaje + código crudo. |
| Código de peso variable de producto sin `vendido_por_peso` | Mensaje claro; no agrega. |
| Modo precio embebido y `precio_kg = 0` | Evitar división por cero: mensaje de error, no agrega. |

### 6. Pruebas (TDD)

Core (sin Qt):
- Helper de conversión: modo peso, modo precio, producto inexistente, división por cero.
- `decodificar_gs1` con `valor_es_precio` (el decodificador devuelve el crudo; la interpretación
  peso/precio la hace el helper, así que el test cubre que el helper la respete).
- `ServicioVenta.agregar` con `importe`: la línea queda con `subtotal = importe` y
  `cantidad_o_peso = peso`.

UI: se mantiene mínima; sin tests de Qt (la lógica vive en el helper de core).

## Decisiones abiertas

- **Modo de la CL3000 (peso vs precio embebido) y posiciones exactas del código:** se confirma
  escaneando una etiqueta real en el local. El diseño soporta ambos vía `FormatoGS1`; solo hay que
  fijar la config cuando se tenga el dato.
