<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# haz esto,, tal cual como lo dices con ospos, unicenta y chromis

La forma más directa de usar código abierto como base para tu POS equivalente al de Siesa es tomar OSPOS como referencia web sencilla y uniCenta/Chromis como referencia de cliente de escritorio Java con soporte de inventario, caja, múltiples impuestos y ventas por peso.  A continuación te detallo, “tal cual”, el análisis profundo de modelo de datos y flujos de caja para OSPOS, uniCenta y Chromis, mapeado contra las necesidades típicas del POS/PDV de Siesa que vimos en el reporte anterior.[^1][^2][^3][^4][^5][^6]

***

## OSPOS como base (PHP + MySQL)

OSPOS es una aplicación web de punto de venta escrita en PHP sobre CodeIgniter, usando MySQL/MariaDB como backend, pensada para ejecutarse en cualquier servidor Linux/Windows y ser usada desde navegador, incluso en entornos locales tipo LAMP.  Su documentación oficial describe el sistema como un POS con gestión de stock, seguimiento de ventas, impresión de recibos/presupuestos/facturas, soporte multiusuario/multilenguaje y un módulo de CRM básico.[^7][^2][^1]

### Modelo de datos lógico de OSPOS

La wiki técnica indica que OSPOS se centra en gestión de stock (Items y Kits), inventario, proveedores y clientes, además de un registro de ventas/devoluciones con logging de transacciones e impresión de tickets.[^1]
A partir de las descripciones de SourceForge y la wiki se puede reconstruir el núcleo del modelo lógico así:[^2][^1]

- **Items/Kits**: catálogo de productos con código de barras, descripción, precio, costo, impuestos y posibilidad de agrupar ítems en “Kits” (paquetes).[^2][^1]
- **Inventory**: registros de movimiento de inventario (entradas/salidas) vinculados a Items, con cantidad, fecha, tipo de movimiento y almacén (multi-stock management).[^1][^2]
- **Customers**: tabla de clientes con datos básicos de contacto, identificadores y notas para CRM.[^1]
- **Suppliers**: proveedores ligados a compras/recepciones de mercancía.[^2][^1]
- **Sales**: cabecera de venta con fecha, usuario, cliente opcional, total, impuestos y estado (venta/ devolución), y líneas de detalle de productos (Items) con cantidades y precios; incluye asociación a Gift cards, descuentos y método de pago.[^2][^1]
- **Receivings**: módulo para entradas de mercancía desde proveedores, similar a compras, que impacta el inventario.[^1][^2]
- **People/Employees**: usuarios del sistema con roles y permisos, usados para controlar acceso a módulos y operaciones.[^2][^1]
- **Gift cards**: tarjetas regalo con saldo y movimientos, usadas como medio de pago.[^1][^2]
- **Expenses**: módulo de gastos que registra salidas de dinero relacionadas con la operación.[^1]

Este modelo cubre gran parte de lo que el POS de Siesa maneja a nivel de productos, clientes, inventarios, ventas y seguridad, aunque no tiene, de serie, la capa de contabilidad/facturación electrónica que tiene Siesa Enterprise.[^8][^9][^2][^1]

### Flujos de caja y operación en OSPOS

La documentación describe un “Sale/Return register” que funciona como caja: se seleccionan artículos (por escáner o búsqueda), se aplican descuentos, se elige cliente opcional y se genera el ticket, con soporte de impresión y correos electrónicos.  Las devoluciones se registran como ventas negativas o transacciones de retorno, manteniendo el historial de movimientos de caja por usuario.[^2][^1]

En inventarios se usan operaciones de “stock management” para ajustar existencias por compras, correcciones o devoluciones, y hay reportes de inventario, ventas por producto, ventas por cliente y otros informes estándar.  La seguridad se basa en roles: cada usuario (Employee) puede tener permisos sobre venta, inventario, informes, etc., lo cual se alinea con la idea de “cajeros” y “administradores” de Siesa.[^10][^2][^1]

### Mapeo contra funcionalidades de Siesa POS/PDV

- **Usuarios y seguridad**: OSPOS ya tiene multiusuario, roles y permisos por módulo, muy similar al Administrador de seguridad de Siesa; puedes mapear “Employees” a “cajeros” y “administradores”.[^11][^2][^1]
- **Caja (apertura/cierre, arqueos)**: OSPOS registra ventas/gastos y tiene informes de ventas, pero no trae explícitamente un módulo de arqueo/cierre de caja tan detallado como uniCenta; se puede implementar usando el módulo de Expenses más reportes de ventas por usuario y día.[^2][^1]
- **Ventas, anticipos, notas crédito/débito**: soporta ventas y devoluciones (returns) con registro por usuario, y gift cards como forma de “anticipo” prepagado; notas crédito/débito formales (documentos contables) habría que agregarlas en una capa contable aparte.[^8][^1][^2]
- **Clientes y bloqueo/modificación**: la base de clientes es simple; para emular el bloqueo de edición de Siesa POS, deberías extender el modelo de permisos y añadir flags de “no modificable” por tipo de cliente.[^11][^1][^2]
- **Inventarios y productos (carnes/frutas)**: OSPOS tiene inventario y códigos de barras, pero no trae de serie soporte explícito de venta por peso ni escalas; podrías manejarlo como unidades (kilos) y precios unitarios, o personalizar el modelo de Items para integrar balanzas.[^1][^2]
- **Operación offline y PDV desconectado**: al ser web, OSPOS está pensado para servidor accesible; si lo instalas en el mismo Debian de la tienda y usas navegador local, podrías simular modo desconectado, pero no tiene explícito el modelo de transmisión/recepción de PDV como Siesa.[^12][^2][^1]
- **Facturación electrónica DIAN**: no hay soporte nativo; deberías construir un módulo adicional que tome las ventas de OSPOS y genere XML/UBL para DIAN, similar a lo que hace Siesa e-Invoicing.[^13][^11][^1]

En resumen, OSPOS es una buena base si quieres un POS web sencillo, multiusuario, con inventario, clientes y reportes, y estás dispuesto a implementar de cero la parte fiscal/DIAN y el modo desconectado al estilo PDV de Siesa.

***

## uniCenta oPOS como base (Java + MariaDB/MySQL)

uniCenta oPOS es un POS de escritorio táctil de grado comercial, derivado de Openbravo, con módulos de Sistema, Ventas (Sales), Inventario, Proveedores, Clientes, Empleados y Web Reports, orientado a retail y hospitalidad.  Funciona con base de datos MySQL/MariaDB, tiene guías de configuración, esquema de base de datos, scripting y reporting, y se distribuye como open source (GPL) con binarios y guías de usuario/developer.[^14][^15][^16][^3][^17]

### Modelo de datos lógico de uniCenta

Los manuales de usuario describen claramente cómo se configuran productos, inventario, caja y clientes, lo que permite inferir un modelo lógico muy cercano al de un PDV maduro.[^18][^3]

A partir de las guías y el Database Schema Guide se puede esquematizar:[^16][^3]

- **Products**: catálogo de productos con nombre, código de barras, precio, categoría, impuestos, atributos, imagen y parámetros adicionales (botones, propiedades, descuentos).[^15][^3]
- **Categories**: clasificación de productos por grupos (carnes, frutas, lácteos, etc.), usada tanto para organización visual como para reglas de precios/impuestos.[^3][^15]
- **Tickets (Sales)**: tabla de cabecera de ventas con fecha/hora, usuario/cajero, caja/terminal, total, impuestos, cliente opcional y estado; y tabla de líneas con producto, cantidad, precio, impuestos y descuentos.[^15][^3]
- **Payments**: registro de formas de pago por ticket (efectivo, tarjeta, otros), con campos de importe, tipo de pago y referencia.[^3][^15]
- **Cash Movements / Close Cash**: movimientos de caja (entradas/salidas no asociadas a ventas) y cierres de caja diarios con reporte de efectivo, salidas y cuadre.[^3]
- **Customers**: clientes con datos de identificación, límite de crédito y saldos, usados para ventas a crédito y seguimiento.[^15][^3]
- **Suppliers**: proveedores usados en módulos de compra/reabastecimiento.[^16][^15]
- **Stock / Inventory movements**: movimientos de inventario (ajustes, compras, ventas) registrados en “Stock Diary” o tablas equivalentes, con soporte de multiubicación.[^4][^19][^16]
- **Employees/Users**: usuarios con roles, permisos y acceso a módulos, incluyendo caja y administración.[^17][^15]
- **Tables/Floor plan (modo restaurante)**: gestión de mesas, número de comensales y botones de mesa para restaurantes, similar al módulo PDV Restaurante de Siesa.[^4][^15]

La documentación de diferencias de la versión 4/5 añade soporte explícito para balanzas CAS-PDII y Mettler, múltiples bases de datos (Primary + Secondary) y notificaciones de stock, lo cual es relevante para negocios de carnes/frutas que venden por peso.[^4]

### Flujos de caja y operación en uniCenta

El manual en inglés (incluye ejemplos para Colombia) muestra el flujo típico:[^3]

- **Configuración inicial**: instalación del software, elección de idioma/moneda, configuración de impresora, creación de usuarios y contraseña de administrador.[^3]
- **Alta de productos**: desde el menú “Inventory > Products” se crean productos con código de barras, precio, categoría y atributos; se pueden cargar imágenes y ajustar parámetros de inventario.[^3]
- **Venta en caja**: en el menú “Sales” se usan botones de producto o lector de código de barras para añadir ítems al ticket, ajustar cantidades y aplicar descuentos; al finalizar la venta, se elige medio de pago (cash, debit, etc.) y se imprime el recibo.[^3]
- **Movimientos de caja**: en “Cash Movement” se registran entradas/salidas de dinero no asociadas a ventas (por ejemplo, gastos menores), con motivos.[^3]
- **Cierre de caja**: al final del día se ejecuta el cierre de caja, se calcula el total en caja, ventas del día, salidas y se puede imprimir un reporte de cierre para archivo físico.[^3]
- **Inventario**: en el menú “Inventory” se usan opciones para ajustar stock, ver movimientos y organizar productos por categorías/atributos.[^16][^3]

La guía de esquemas de BD y developer docs permite extender el sistema: añadir campos nuevos a productos, modificar plantillas de tickets, integrar reportes personalizados, etc.[^20][^16]

### Mapeo contra funcionalidades de Siesa POS/PDV

- **Usuarios, cajeros y perfiles**: uniCenta tiene usuarios con roles y permisos, y el manual muestra cómo proteger el usuario administrador con contraseña y controlar quién accede a configuración y caja, similar al Administrador de seguridad de Siesa.[^9][^15][^3]
- **Caja (apertura/cierre, arqueos)**: el flujo de ventas, movimientos de caja y cierre de caja con reporte es muy cercano al comportamiento del PDV de Siesa (apertura de caja, registro de ventas, salidas de dinero, cierre con cuadre).[^12][^3]
- **Ventas por peso (carnes/frutas)**: la compatibilidad con balanzas CAS-PDII y Mettler y el manejo de unidades/atributos en productos hacen viable implementar venta por peso con códigos de barras de peso, similar al soporte GS1 de Chromis.[^6][^4]
- **Clientes, crédito y notas**: uniCenta maneja clientes, límites de crédito y saldos, lo que permite ventas a crédito y seguimiento de cuentas; notas crédito/débito contables habría que modelarlas como tickets de devolución/ajuste más integración con contabilidad.[^8][^15][^3]
- **Inventarios, multiubicación y lotes**: el “Stock Diary” y soporte de multiubicación permiten reflejar entradas/salidas por almacén o tienda, lo que se alinea con PDV almacén de Siesa; para lotes/fechas de vencimiento habría que extender el modelo de producto o crear tablas adicionales.[^12][^16][^4]
- **Modo desconectado y PDV local**: uniCenta corre contra una BD local (MySQL/MariaDB o embebida) en cada tienda; la sincronización con un ERP central habría que implementarla mediante procesos de export/import (como el Database Transfer Tool) o servicios propios, similar a transmisión/recepción PDV.[^20][^16][^12]
- **Facturación electrónica DIAN**: de serie no tiene integración DIAN; deberías desarrollar un módulo que lea tickets y genere documentos electrónicos (XML UBL) y los transmita a DIAN, como hace el módulo de e-Invoicing de Siesa.[^13][^11][^16]

Por su arquitectura Java y sus capacidades de inventario/caja, uniCenta es una base muy fuerte si quieres algo cercano a la experiencia de terminal Linux con PDV de Siesa, especialmente para supermercados y restaurantes.

***

## Chromis POS como base (fork de uniCenta orientado a retail)

Chromis POS es un fork de uniCenta orientado a retail y restauración, con soporte de múltiples modos de venta, precios escalonados, pantallas de cocina y, muy importante para tu caso, soporte explícito de códigos de barras “price/weight encoded” conforme estándares GS1.  Se ejecuta sobre Java 11, ha sido probado en Linux Mint y distintos Windows, y separa las aplicaciones de caja (POS) y administración (back office).[][^5][^6]

### Modelo de datos lógico de Chromis

Al ser fork de uniCenta, el modelo de datos es prácticamente el mismo, con ampliaciones para funciones avanzadas de retail.  A partir de la documentación y fichas de producto se puede resumir así:[^21][^5][^6]

- **Products**: productos con precio, código de barras, categoría, impuestos, niveles de precio (multi-tiered pricing) y opciones de gestión de stock; incluye soporte de códigos de barras que codifican precio/peso (GS1) para venta a granel.[^5][^6]
- **Tickets/Sales**: tickets de venta con múltiples modos (venta al detalle, restaurante, etc.), líneas de producto, impuestos, descuentos y referencia de mesa/usuario cuando se usa modo restaurante.[^19][^6][^5]
- **Payments**: módulo de pagos con distintos medios y posibilidad de integrarse con pasarelas (por ejemplo Planetauthorize, aunque esto es más común en instalaciones específicas).[^22][^5]
- **Customers/Employees**: base de clientes con datos y límites, y base de empleados con roles, usada para controlar acceso y registrar ventas por usuario.[^21][^6][^5]
- **Stock Management/Stock Diary**: gestión de stock, suppliers, órdenes a proveedores y diario de movimientos de stock, igual que en uniCenta.[^19][^6][^5]
- **Kitchen Display y Tables**: pantallas de cocina y gestión de mesas (table management), útiles para restaurantes y áreas de preparación de carne o comida.[^23][^6][^5]
- **Loyalty y Gift cards**: sistema de fidelización, tarjetas regalo y promociones/ descuentos.[^6][^5]

La documentación destaca que Chromis soporta base de datos embebida Derby para instalaciones simples y MySQL/PostgreSQL para multi-terminal, y que puede funcionar en modo multi-tienda y multi-ubicación.[^5][^6]

### Flujos de caja y operación en Chromis

Tutoriales y fichas describen un flujo de uso muy similar al de uniCenta, con algunas extensiones:[^24][^19][^6]

- **Configuración**: instalación mediante su propio instalador en distintas plataformas, configuración de BD (Derby para pruebas, MySQL/PostgreSQL para producción), creación de usuarios y roles.[^6][^5]
- **Alta de productos**: uso del “Stock Diary” y panel de productos para crear artículos, asignar códigos de barras (incluyendo los que codifican peso/precio), categorías y niveles de precio.[^19][^5][^6]
- **Venta en caja**: pantalla de ventas personalizable con botones de producto, lector de código de barras, gestión de mesas en modo restaurante, envío de pedidos a pantalla de cocina y registro de pagos.[^23][^5][^19]
- **Gestión de stock**: ajustes de existencias, entradas desde proveedores, consultas de stock por producto y ubicación.[^5][^19][^6]
- **Cierres de caja y reportes**: generación de informes de ventas, stock, usuarios, cierres de caja y otros reportes integrados.[^21][^6][^5]

La ficha de características resalta soporte para “Price\weight encoded barcodes” según GS1, múltiples modos de venta, pantalla táctil, terminales múltiples y funcionamiento con hardware estándar de POS (impresoras, escáneres, etc.).[^24][^6][^5]

### Mapeo contra funcionalidades de Siesa POS/PDV

- **Usuarios y seguridad**: Chromis tiene “user security”, roles y restricción de acceso a funciones, lo que permite replicar perfiles tipo cajero/administrador como en Siesa.[^21][^6][^5]
- **Caja y arqueos**: como uniCenta, integra venta, movimientos de caja y cierres con reportes; puedes implementar un flujo de apertura/cierre/arqueo diario equivalente al PDV de Siesa con poca adaptación.[^6][^5][^3]
- **Venta por peso (carnes/frutas)**: el soporte directo de códigos de barras que codifican precio/peso conforme GS1 es una ventaja grande para carnicerías y fruterías, pues permite pesar producto en la balanza, imprimir etiqueta con código GS1 y leerlo en caja sin lógica adicional compleja.[^5][^6]
- **Inventarios, proveedores y multiubicación**: la integración de stock management, suppliers y multi-terminal favorece escenarios de almacén + tienda, similar al PDV almacén de Siesa; se puede definir una lógica de transmisión/sincronización entre tiendas/servidor central.[^12][^6][^5]
- **Clientes, lealtad y gift cards**: la presencia de loyalty system y electronic gift cards complementa la CRM básica de Siesa POS, y se puede mapear a anticipos o programas de fidelización propios.[^8][^6][^5]
- **Pantalla de cocina/restaurante**: si la empresa tiene sección de preparación (desposte, empaques, comidas rápidas), las pantallas de cocina y gestión de mesas permiten replicar el PDV Restaurante de Siesa.[^6][^12][^5]
- **Modo desconectado**: al ser self–hosted y correr sobre BD local, Chromis puede trabajar durante caídas de internet y luego sincronizar datos, alineándose con el modelo “facturación no se interrumpe al perder conectividad” que Siesa promociona.[^25][^21][^5][^6]
- **Facturación electrónica DIAN**: igual que uniCenta, no trae DIAN integrado; deberías implementar un servicio de facturación electrónica externo que consuma los tickets y los envíe a DIAN.[^11][^13][^5][^6]

Chromis, por ser un fork actualizado y orientado a retail con venta por peso y hardware de tienda, es probablemente la base más cercana a lo que necesitas para una empresa de carnes y frutas que hoy usa PDV Siesa en Linux.

***

## Cómo aprovecharlos “tal cual” para tu diseño de POS

Para seguir “tal cual” lo que te propuse, el enfoque práctico sería:

- Tomar **OSPOS** como referencia de arquitectura web sencilla (PHP + MySQL) para entender cómo modelar Items, Inventory, Customers, Sales, Employees y Gift cards, y cómo se organiza un registro de ventas/devoluciones y reportes básicos.[^2][^1]
- Tomar **uniCenta** y **Chromis** como referencia para cliente de escritorio en Linux con flujo completo de caja (ventas, movimientos de caja, cierre de caja), inventario, multiubicación, usuarios y soporte de dispositivos POS (balanzas, impresoras, escáneres).[^15][^4][^5][^6][^3]
- Mapear cada requisito del POS de Siesa (usuarios, caja, PDV desconectado, inventarios, clientes, impuestos, DIAN, informes) contra estos modelos: reutilizar tal cual las partes que ya existen en uniCenta/Chromis (ventas por peso, cierres de caja, stock diary, usuarios y permisos) y usar OSPOS como guía para la API/estructura si partes de una arquitectura web.[^8][^12][^5][^6][^1][^3]

Cuando quieras, podemos bajar esto a un nivel aún más técnico: por ejemplo, dibujar un esquema de tablas mínimo inspirado en Chromis/uniCenta pero adaptado a tus reglas de negocio (pesos, lotes, vencimientos, resolución DIAN, operación desconectada) y definir los flujos de transmisión/sincronización que necesitas para reemplazar al PDV de Siesa sin perder funcionalidad.
<span style="display:none">[^26][^27][^28][^29][^30][^31][^32][^33][^34][^35][^36][^37]</span>

<div align="center">⁂</div>

[^1]: https://github-wiki-see.page/m/opensourcepos/opensourcepos/wiki

[^2]: https://sourceforge.net/projects/opensourcepos/files/

[^3]: https://es.scribd.com/document/465839529/UniCenta-OPOS-Manual-English

[^4]: https://unicenta.com/features/differences/

[^5]: https://sourceforge.net/projects/chromispos/

[^6]: https://opensourcedownloads.com/chromis-pos-retail-management/

[^7]: https://opensourcepos.org

[^8]: https://pruebascustomersupport.siesacloud.com/manuales-3/

[^9]: https://www.siesacustomersupport.com/manuales-2/

[^10]: https://es.scribd.com/document/587401126/Manual-Co-mo-crear-un-usuario-cajero-para-usar-en-el-Siesa-Pos11

[^11]: https://www.siesacustomersupport.com/wp-content/uploads/2025/10/Manual-Bloqueo-y-modificacion-de-clientes-POS-Gestion-de-Puntos-de-Venta.pdf

[^12]: https://www.siesacustomersupport.com/category/manuales/siesa-85/sistema-de-ventas-pdv/

[^13]: https://www.retaildelfuturo.com/retail-inteligente-con-siesa-cuando-la-tecnologia-se-convierte-en-ventaja-competitiva/

[^14]: https://sourceforge.net/projects/unicentaopos/files/docs/

[^15]: https://unicenta.com/features/

[^16]: https://unicenta.com/downloads/guides/

[^17]: https://unicenta.com/pages/

[^18]: https://www.scribd.com/document/444493603/User-Training-Guide-for-uniCenta-users-pdf

[^19]: https://www.youtube.com/watch?v=lPvwBHSIvQo

[^20]: https://unicenta.com/unicenta-opos-release-4-6/

[^21]: https://us.fitgap.com/products/006866/chromis-pos

[^22]: http://retailpayments.com/chromispos.html

[^23]: https://www.softwaresuggest.com/chromis

[^24]: https://chromis.software.informer.com/0.5/

[^25]: https://www.capterra.co/software/1023938/siesa-pos

[^26]: https://mikaelsondi.files.wordpress.com/2014/09/unicenta03.pdf

[^27]: https://www.scribd.com/document/465839529/UniCenta-OPOS-Manual-English

[^28]: https://www.scribd.com/document/465832750/Unicenta-oPOS-4-3-Readme

[^29]: https://unicenta.com/unicenta-opos-videos/

[^30]: https://www.ds4it.com/pdf/DigitalStyle_User_Manual.pdf

[^31]: https://www.youtube.com/watch?v=uotbqhxt2ME

[^32]: https://github.com/ChromisPos/ChromisPOS/wiki

[^33]: https://www.youtube.com/watch?v=ooHbx86Ea8Q

[^34]: https://medevel.com/pos-2024-os-1300/

[^35]: https://sourceforge.net/software/product/Chromis-POS/

[^36]: https://sourceforge.net/projects/chromispos/files/

[^37]: https://github.com/ChromisPos/ChromisPOS/blob/master/README.txt

