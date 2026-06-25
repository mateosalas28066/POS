---
name: facturacion-dian
description: Use when working on electronic invoicing or DIAN compliance in pos-siesa-remake (EmisorDIAN port, UBL 2.1, CUFE, QR, resoluciones/anexos DIAN, proveedor tecnologico). Provides the index of resolutions/anexos and key UBL fields for the Auditor DIAN subagent.
---

# Facturación electrónica DIAN (pos-siesa-remake)

Cargar al trabajar en `src/facturacion_dian/` o en las reglas fiscales de `core`.

## Frontera arquitectónica (no romper)

- **Armado del documento** (de `Venta` + `Cliente` + `Impuesto`, reglas fiscales) = lógica de
  dominio en `src/core/`.
- `src/facturacion_dian/` = **solo** el puerto `EmisorDIAN` + adaptadores:
  - `EmisorStub` — comprobante interno **sin valor fiscal** (hoy).
  - `EmisorProveedor` — futuro: envía a un proveedor tecnológico autorizado (API) que firma y
    transmite a la DIAN y devuelve CUFE/QR/PDF validados.

## Dos caminos hacia la DIAN

1. **Proveedor tecnológico** (recomendado para empezar): el POS manda datos de la venta vía API;
   el proveedor genera el XML legal, firma, transmite y devuelve la factura validada.
   Ej.: Facturatech, Carvajal, The Factory HKA, Siigo, Delcop.
2. **Emisor propio (habilitación directa)**: generar UBL 2.1, firmar, calcular CUFE, generar QR,
   transmitir al web service DIAN, pasar el set de pruebas. Mucho más trabajo y cumplimiento legal.

## Índice de resoluciones / anexos a tener presente

- Anexos técnicos DIAN **1.8, 1.9** (y 1.0 histórico) — estructura del documento electrónico.
- Resoluciones citadas en el dominio Siesa: **000042, 000165, 001092, 000012, 000238**.
- Documentos: factura electrónica de venta, **nota crédito**, **nota débito**, documento equivalente.

> Confirmar versión de anexo vigente y la resolución de facturación real de la empresa antes de
> implementar producción. No hardcodear: usar maestros `param_dian_*`.

## Campos UBL clave (mínimo a mapear)

- Emisor/receptor: identificación, **tipo_documento**, **regimen**, **tipo_responsabilidad**.
- Factura: número + resolución (rango, vigencia, prefijo), fecha/hora, moneda.
- Líneas: producto, cantidad/peso, precio, **código de impuesto DIAN**, tarifa, base, valor.
- Totales: subtotal, impuestos, total. **CUFE**, **QR**, representación gráfica.

## Espacio reservado en el modelo (minimalista, Ponytail)

`impuestos.codigo_dian`; `clientes.tipo_documento/regimen/tipo_responsabilidad`; tablas
`param_dian_*` para maestros. Definidos como espacio reservado; sin reglas fiscales aún.
