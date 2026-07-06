# Scanner de balanza (serial) — estado y pendiente

> Fecha: 2026-07-02. Estado: **decodificación GS1 OK; queda validar un scanner serial de balanza.**

## Resumen

El POS ya vende por código escaneado de balanza (EAN‑13 de peso variable, prefijo `24`).
La **lógica de decodificación está verificada y funcionando**:

- Scanner **plug-and-play (modo teclado)** conectado hoy: escanea la etiqueta y agrega el
  producto correctamente (probado con **Ampolleta** `2400190008059` y **Pezuña de cerdo**
  `2400121004457`).
- 401 tests en verde, incluyendo la decodificación de ambas etiquetas reales.

Lo que **falta terminar de probar** es un **scanner serial específico** (el que venía con la
balanza), que no pudo seguirse en horario laboral.

## El problema observado con el scanner serial de la balanza

Al escanear la Ampolleta con ese lector, al POS llegó `082400190008059` (15 dígitos) en vez de
`2400190008059` (13). El `08` extra hace que `es_peso_variable` dé `False`
([src/core/perifericos/gs1.py](../src/core/perifericos/gs1.py#L37)) y el código se busque tal
cual → "producto inexistente". **No es un fallo de la decodificación**, sino de qué bytes manda
ese scanner.

Dos hipótesis (no confirmadas — hace falta la captura cruda):

1. **Prefijo de hardware:** el scanner está configurado para anteponer `08` a cada lectura.
   → Se arregla reconfigurando el scanner (quitar prefijo) o normalizando en software.
2. **Pegado en el buffer:** el lector serial del POS
   ([src/caja/pantalla_venta.py](../src/caja/pantalla_venta.py#L136-L157)) acumula bytes hasta
   ver `\r`/`\n`. Si el scanner manda algo suelto sin terminador, se pega con el siguiente
   escaneo. `08` + `2400190008059` daría exactamente lo observado.
   → Es un bug nuestro del buffer serial.

## Cómo retomar (paso siguiente concreto)

1. Cerrar cualquier ventana/POS que tenga el puerto abierto.
2. Capturar los **bytes crudos** que manda el scanner:
   ```powershell
   cd W:\POS
   python scripts\leer_scanner.py COM6        # ajustar puerto/baud si aplica
   ```
   Escanear la etiqueta y mirar la línea `crudo:`.
3. Decidir el arreglo según lo que muestre:
   - `08` viene **pegado en la misma lectura** (`b'082400190008059\r\n'`) → prefijo de hardware:
     reconfigurar el scanner, o quitar prefijo conocido en `_leer_scanner_serial`.
   - `08` llega en **lectura separada** y se pega al siguiente → arreglar el buffer serial
     (separar por gap de tiempo entre escaneos, o por longitud EAN‑13, no solo por `\r`/`\n`).
   - Sale limpio (`b'2400190008059\r\n'`) → era un escaneo fallido puntual; reintentar.
   - Caracteres no imprimibles → baud rate/paridad mal (probar `--baud 115200`).

## Cómo usar un scanner serial hoy (si hace falta)

El soporte serial ya existe; se activa por variables de entorno:
```powershell
cd W:\POS
$env:PYTHONPATH = "src"
$env:POS_SCANNER_PORT = "COM6"
$env:POS_SCANNER_BAUD = "9600"
python -m caja pos-prueba.db
```
Un scanner **modo teclado** (plug-and-play) no necesita nada de esto: escribe directo en el
campo "Escanear…" y funciona ya.

## Productos de prueba sembrados (seed demo)

En [src/caja/bootstrap.py](../src/caja/bootstrap.py) (`_PRODUCTOS_DEMO`), vendidos por peso:

| PLU (código) | Nombre           | Precio/kg | Etiqueta real (EAN‑13) | Peso  | Total |
|--------------|------------------|-----------|------------------------|-------|-------|
| `00190`      | Ampolleta        | 30000     | `2400190008059`        | 0.805 | 24150 |
| `00121`      | Pezuña de cerdo  | 10000     | `2400121004457`        | 0.445 | 4450  |

> El seed solo inserta productos faltantes al arrancar. En una DB ya existente puede que estos
> no se agreguen; para prueba limpia usar una DB nueva (`pos-prueba.db`) o crear el PLU a mano.
