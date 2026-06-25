---
name: pos-dominio
description: Use when touching ANY POS business logic in pos-siesa-remake (entidades, ventas, caja, inventario, clientes, impuestos, precio por peso) - carries the functional map of Siesa POS/PDV and the OSPOS/uniCenta/Chromis references the design is based on.
---

# Dominio del POS (pos-siesa-remake)

**Cargar este skill SIEMPRE que toques código de negocio del POS.** Te da el mapa funcional
de Siesa y las referencias open source para no reinventar ni desviarte del modelo.

## Funcionalidades mínimas (qué debe cubrir el POS)

- Usuarios/cajeros con perfiles y permisos; bloqueo/restricción de edición de clientes.
- Apertura/cierre de caja, arqueo, turnos y medios de pago.
- Ventas con múltiples medios de pago; devoluciones; (futuro) anticipos y notas crédito/débito.
- Maestros de clientes y productos; impuestos por artículo; descuentos.
- Venta por peso (carnes/frutas): balanza serial + código GS1 peso/precio.
- (Costura) Facturación electrónica DIAN tras interfaz `EmisorDIAN`.
- (Costura) Operación desconectada + transmisión/recepción (patrón outbox = PDV almacén de Siesa).
- Informes: ventas por caja/cajero/día, cierres, acumulación.

Detalle funcional: [docs/pos-siesa-funcional.md](../../../docs/pos-siesa-funcional.md)

## De dónde tomar referencia (qué reutilizar conceptualmente)

- **OSPOS** (PHP/MySQL): estructura de Items, Inventory, Customers, Sales, Employees, Gift cards;
  registro de ventas/devoluciones y reportes básicos. Buena guía de modelo lógico.
- **uniCenta** (Java): flujo completo de caja (venta → movimientos de caja → cierre con cuadre),
  Stock Diary, multiubicación, balanzas CAS-PDII/Mettler.
- **Chromis** (fork de uniCenta): **venta por peso con códigos GS1 (price/weight encoded)**, modos
  de venta, multi-terminal. Es la referencia más cercana a este negocio.

Detalle: [docs/pos-open-source-referencias.md](../../../docs/pos-open-source-referencias.md)

## Reglas de arquitectura al implementar

- El dominio va en `src/core/`, sin Qt ni SQLite.
- Acceso a datos solo por puertos `RepositorioX`; nunca SQL en `core`/`caja`/`inventario` salvo el adaptador.
- Reglas fiscales DIAN en `core`, no en `facturacion_dian/`.
- Aplicar Ponytail: mínimo código, stdlib primero, YAGNI.
