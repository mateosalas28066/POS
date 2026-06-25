# POS de Siesa — Análisis funcional y requisitos mínimos

Resumen funcional del POS/PDV de Siesa, usado como referencia de "qué no perder" al construir
`pos-siesa-remake`. Basado en el análisis técnico de los manuales de Siesa POS, Sistema de
Ventas PDV 8.5 y Siesa Enterprise.

> Fuente extensa original: `../Análisis técnico del sistema Siesa POS y módulos PDV POS relacionados.md`

## Capas del sistema Siesa (contexto)

1. **Caja/PDV** — app local (Java) en Linux/Windows: ventas, cajeros, tickets, opera desconectada.
2. **Administración POS central** — configura terminales (TPV), maestros de clientes POS, resoluciones, perfiles.
3. **ERP** — contabilidad, inventarios, compras, impuestos, medios de pago, registros contables.
4. **Facturación electrónica (e-Invoicing)** — transmisión DIAN, anexos UBL, eventos.

`pos-siesa-remake` es **autónomo**: reemplaza las 4 capas a su escala (no integra con Siesa),
empezando por la capa de caja local.

## Funcionalidades clave observadas en Siesa

- **Operación de caja:** usuarios cajeros, apertura de caja, facturación, turnos y arqueos;
  consecutivos de venta por punto de venta.
- **Medios de pago y notas:** múltiples formas de pago; notas crédito/débito desde POS;
  manejo de anticipos.
- **Clientes:** maestro de clientes con datos tributarios; **bloqueo/restricción de edición**
  de clientes POS controlado por permisos (Administrador de seguridad).
- **Resoluciones DIAN:** resolución de facturación con rangos, vigencia, código DIAN; UVT;
  impresión de factura electrónica con QR/CUFE.
- **Operación desconectada:** cola local de tickets + transmisión/recepción al servidor central
  (PDV almacén); continuidad de facturación sin conectividad.
- **Impuestos, descuentos y promociones:** impuestos especiales por artículo (saludables, consumo),
  descuentos por grupo/cliente, día sin IVA.
- **Informes:** acumulación de ventas por caja/cajero/día, detalle por producto/cliente, cierres de caja.
- **Seguridad:** perfiles, usuarios, permisos por operación; logs de errores auditables.

## Requisitos mínimos del nuevo POS

El POS debe cubrir, como mínimo:

1. Usuarios cajeros, perfiles y permisos; creación, bloqueo y restricción de edición de clientes.
2. Apertura/cierre de caja, arqueos, control de turnos y medios de pago.
3. Registro de ventas con múltiples formas de pago y (futuro) anticipos.
4. Maestros de clientes y productos, con impuestos por artículo y descuentos.
5. **Venta por peso** (carnes/frutas): balanza serial + código GS1 peso/precio.
6. Generación de facturas/NC/ND ajustadas a resoluciones (vía interfaz `EmisorDIAN`).
7. Operación desconectada con almacenamiento local y transmisión/recepción (patrón outbox).
8. Gestión de consecutivos de venta.
9. Inventario: actualización de existencias y costos; lotes/vencimientos (perecederos).
10. Informes operativos: ventas, cierres, acumulación por producto/cliente/cajero.

## Específico del negocio (carnes y frutas)

- **Venta por peso** en dos modalidades reales: balanza conectada (fruver) y código de barras
  GS1 con peso/precio impreso por la balanza (carne).
- **Lotes y fechas de vencimiento** para perecederos (definido en el modelo, código diferido).
