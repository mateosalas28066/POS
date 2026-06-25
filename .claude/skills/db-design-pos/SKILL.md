---
name: db-design-pos
description: Use when designing or modifying the data model, tables, or relations of pos-siesa-remake (SQLite now, PostgreSQL later). Defines the minimum schema, the lotes/vencimientos model, and reserved DIAN master space.
---

# Diseño de modelo de datos (pos-siesa-remake)

Cargar al crear o modificar tablas/migraciones. **Todo acceso a estas tablas pasa por
adaptadores de repositorio**; nada de SQL en `core`/`caja`/`inventario` salvo el adaptador.

## Tablas del MVP

- `usuarios` (id, nombre, rol, hash_password)
- `categorias` (id, nombre)
- `impuestos` (id, nombre, tarifa, `codigo_dian` _reservado_)
- `medios_pago` (id, nombre)
- `productos` (id, codigo_barras, nombre, categoria_id→categorias, precio, costo,
  impuesto_id→impuestos, `vendido_por_peso` BOOL, unidad)
- `clientes` (id, identificacion, nombre, contacto, `bloqueado_edicion` BOOL,
  `tipo_documento`/`regimen`/`tipo_responsabilidad` _reservados DIAN_)
- `caja_sesiones` (id, usuario_id→usuarios, apertura_fecha, monto_inicial, cierre_fecha,
  monto_contado, estado)
- `ventas` (id, fecha, usuario_id, caja_sesion_id→caja_sesiones, cliente_id→clientes, total,
  total_impuestos, estado)
- `venta_lineas` (id, venta_id→ventas, producto_id→productos, cantidad_o_peso, precio_unit,
  impuesto, subtotal)
- `pagos` (id, venta_id→ventas, medio_pago_id→medios_pago, monto, referencia)
- `inventario_movimientos` (id, producto_id→productos, `lote_id` NULLABLE→lotes, tipo, cantidad,
  fecha, ref)
- `outbox_eventos` (id, tipo_evento, payload_json, fecha, estado_sync)

## Definidas en el modelo, código diferido

- `lotes` (id, producto_id→productos, lote, fecha_vencimiento, cantidad).
  **Se define ahora** (carnicería/fruver lo exigirá); enlazada vía `inventario_movimientos.lote_id`.
  Evita parches fuera del modelo más adelante.
- Maestros DIAN (`param_dian_*` / columnas reservadas): **minimalistas**, solo espacio reservado.

## Principios

- Claves foráneas explícitas; integridad referencial activada en SQLite (`PRAGMA foreign_keys`).
- Migraciones versionadas en `scripts/`.
- No sobre-modelar: agregar columnas/tablas cuando el requisito sea real (Ponytail/YAGNI).
- Diseñar pensando en portabilidad SQLite→PostgreSQL (tipos y SQL neutros donde sea posible).
