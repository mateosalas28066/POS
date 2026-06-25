# Referencias open source: OSPOS, uniCenta y Chromis

Qué tomar de cada proyecto open source como referencia de modelo de datos y flujo de caja al
construir `pos-siesa-remake`. **No se forkea código**: se usan como guía conceptual.

> Fuente extensa original: `../haz esto,, tal cual como lo dices con ospos, unice.md`

## Resumen comparativo

| Aspecto | OSPOS (PHP/MySQL) | uniCenta (Java/MariaDB) | Chromis (fork de uniCenta) |
|---|---|---|---|
| Tipo | POS web | POS escritorio táctil | POS escritorio retail |
| Caja/cierre formal | Débil (Expenses + reportes) | **Fuerte** (cash movement + close cash) | Fuerte (igual que uniCenta) |
| Venta por peso | No de serie | Balanzas CAS-PDII/Mettler | **GS1 price/weight barcodes** |
| Multiubicación/stock | Básico | Stock Diary, multiubicación | Stock Diary, multi-terminal |
| DIAN | No | No | No |

## Qué reutilizar (conceptualmente) en nuestro diseño

### De OSPOS — modelo lógico simple
- Estructura clara de **Items, Inventory, Customers, Sales (cabecera+líneas), Employees, Gift cards, Expenses**.
- Registro de **ventas/devoluciones** y reportes básicos por producto/cliente/usuario.
- Roles y permisos por módulo → mapean a "cajero/administrador".

### De uniCenta — flujo de caja maduro
- Flujo completo: **venta → movimientos de caja → cierre de caja con cuadre**.
- **Stock Diary** (diario de movimientos de inventario) y multiubicación → modelo de
  `inventario_movimientos`.
- Soporte de **balanzas** (CAS-PDII/Mettler) → referencia para el adaptador `BalanzaSerial`.

### De Chromis — lo más cercano a este negocio
- **Códigos de barras GS1 que codifican peso/precio** para venta a granel → referencia directa
  del adaptador `CodigoPesoGS1` (carne).
- Múltiples modos de venta, multi-terminal, BD embebida o cliente-servidor.
- Loyalty / gift cards / promociones (futuro, no MVP).

## Cómo se refleja en `src/`

- `inventario/` ← modelo de Items/Stock Diary (OSPOS + uniCenta).
- `caja/` ← flujo venta/cierre de uniCenta/Chromis.
- `core/perifericos/` ← balanza (uniCenta) + GS1 (Chromis), detrás del puerto `LectorPeso`.
- `facturacion_dian/` ← lo que **ninguno** trae: se construye desde cero tras la interfaz `EmisorDIAN`.
