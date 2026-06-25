# Análisis técnico del sistema Siesa POS y módulos PDV/POS relacionados

## 1. Alcance del sistema POS de Siesa

El ecosistema de punto de venta de Siesa no es un único producto, sino un conjunto de componentes: Siesa POS, el módulo de Ventas PDV de Siesa 8.5 y el entorno Siesa Enterprise/Zeus POS que se integra con facturación electrónica y otros módulos del ERP.  En los manuales oficiales se distingue explícitamente "Sistema de Ventas PDV" (40 manuales listados) y "POS" (45 manuales), lo que indica que la funcionalidad de punto de venta está dividida en varias capas (caja local, administración central, integración con inventarios/financiero).[^1][^2][^3][^4]

En la documentación reciente Siesa POS se presenta como la solución para cadenas de supermercados, restaurantes y retail de alto tráfico, enfocada en garantizar continuidad de facturación incluso sin conectividad y en soportar múltiples medios de pago.  Esto implica que el POS clásico tipo terminal en Debian que estás reemplazando forma parte de una arquitectura más amplia de ERP y PDV que hay que considerar para no perder funcionalidades.[^5][^3]

## 2. Versiones y plataformas relevantes

### 2.1. Familias de versión

Los manuales y materiales de soporte se organizan principalmente alrededor de dos grandes familias de versión:

- **Siesa 8.5 / Sistema de Ventas PDV 8.5**: conjunto de manuales que describen el funcionamiento del PDV (punto de venta) desconectado, transmisión de datos, parámetros de restaurante y manejo de caja.[^2][^4]
- **Siesa Enterprise / Siesa POS / Zeus POS**: línea más moderna orientada a integración con Enterprise, facturación electrónica bajo anexos DIAN 1.8 y 1.9 y resoluciones como 000165, 000042 y 001092.[^6][^7][^4]

La página de Capterra para "Siesa POS" describe el producto actual como una aplicación para operar puntos de venta físicos o electrónicos, con soporte de facturación continua, desconexión controlada y múltiples métodos de pago, dirigida a supermercados, restaurantes y grandes almacenes.  Esto sugiere que el POS clásico se ha ido alineando con requisitos de facturación electrónica y retail moderno.[^3]

### 2.2. Plataformas y modo de operación

Aunque los manuales públicos no detallan explícitamente la plataforma del POS clásico, varios documentos de Siesa 8.5 hablan de actualización de Java para Linux y Windows y de ejecución mediante Java Web Start (javaws), lo que indica un cliente rico tipo escritorio sobre Java para los módulos de caja y PDV.  La referencia a "Cómo actualizar correctamente las mejoras del sistema Siesa 8.5 (Linux)" también confirma soporte oficial para entornos GNU/Linux.[^4][^1]

En las listas de manuales se diferencian claramente componentes "POS" y "Sistema de Ventas PDV" ligados a Siesa 8.5 y Siesa Enterprise, lo que sugiere arquitecturas cliente-servidor donde el POS/PDV se conecta a un servidor central (Enterprise/Zeus) y puede operar desconectado mediante mecanismos de transmisión/recepción.[^2][^4]

## 3. Módulos funcionales principales

### 3.1. Sistema de Ventas PDV (Siesa 8.5)

El apartado "Sistema de Ventas PDV" en el portal de manuales de Siesa registra 40 manuales específicos, lo que muestra que el módulo PDV es extenso y modular.  Los títulos accesibles para Siesa 8.5 incluyen:[^4]

- Manual de PDV Restaurante: describe el flujo operativo de un punto de venta tipo restaurante, con manejo de mesas, pedidos y parámetros específicos.[^2]
- Manual de parámetros PDV Restaurante: detalla la configuración de parámetros de restaurante en el sistema PDV, probablemente opciones de impresión, tiempos de preparación, impuestos y manejo de servicio.[^2]
- Manual de asignación de cuenta a caja de punto de venta: explica cómo vincular cuentas contables y de caja a una TPV (terminal punto de venta) dentro del sistema PDV.[^2]
- Manual de transmisión y recepción PDV almacén: documenta el procedimiento de transmisión de ventas desde las cajas al servidor central y la recepción de información, clave para operación desconectada.[^2]
- Manual de resolución de facturación en PDV: indica el proceso para actualizar la resolución de facturación en el módulo PDV, ajustándose a cambios DIAN.[^2]

Estos manuales dejan claro que el PDV cubre la lógica de caja local (ventas, formas de pago, manejo de consecutivos) y su comunicación con el ERP (consecutivos, resolución de facturación, cuentas contables, parámetros de restaurante).[^2]

### 3.2. Módulo POS dentro de Siesa Enterprise / Siesa POS

En la categoría general de manuales se identifican 45 manuales bajo el descriptor "POS", asociados a Siesa Enterprise y Siesa POS.  Aunque el contenido completo de cada manual no se muestra en la lista, se cita explícitamente un "Manual: Impresión de Factura Electrónica desde el POS – Siesa POS" dentro de la sección Siesa Enterprise, lo que evidencia integración del POS con la capa de facturación electrónica.[^4]

La documentación de Siesa Enterprise también referencía "Informes Siesa POS – Siesa 8.5", indicando que existen reportes de acumulación de ventas POS, análisis de inventarios y posiblemente cierres de caja vinculados al POS.  Al mismo tiempo, Siesa POS se presenta en materiales comerciales como solución escogida por más de 800 empresas de retail, centrada en gestión de puntos de venta y escalabilidad.[^8][^3][^4]

### 3.3. Integraciones transversales (Contabilidad, Inventarios, Compras, Facturación electrónica)

El portal de manuales muestra que POS/PDV interactúa con múltiples módulos:

- **Inventarios**: manuales de solucionado de errores de inventario, configuración de impuestos (plásticos, bebidas azucaradas, alimentos ultraprocesados), manejo de costos y existencias, que afectan directamente la lógica de ventas en POS.[^1]
- **Contabilidad y financiero**: manuales de creación de resolución de facturación, notas débito/crédito, configuración de descuentos globales y mandatos para facturas, que definen cómo el POS registra operaciones contables.[^1]
- **Compras y documentos soporte**: procesos de documento soporte en adquisiciones a no obligados a facturar, que pueden interactuar con devoluciones en venta y compras por POS.[^1][^4]
- **Facturación electrónica**: gran número de manuales sobre anexos DIAN, equivalencias UBL 2.1, generación y envío de facturas, notas crédito/débito y documentos equivalentes electrónicos, donde parte del flujo puede originarse en POS.[^7][^4]

Para replicar completamente el comportamiento del POS de Siesa en un nuevo sistema, será necesario contemplar estas integraciones, no solo la lógica de caja.

## 4. Funcionalidades clave del POS/PDV según los manuales

### 4.1. Operación de caja: venta, pago y cierre

Los manuales específicos de Siesa POS incluyen guías sobre creación de usuario cajero, apertura de caja y facturación, indicando que el POS gestiona:

- Creación de usuarios internos y asignación como cajeros, vinculándolos a clientes y empleados para control de seguridad.[^9]
- Apertura de caja y prueba de facturación para cada cajero, lo que implica manejo de turnos y arqueos.[^9]

Otros manuales citados por el resumen de contenidos (aunque no totalmente visibles) se refieren a notas crédito/débito totales en sistema POS, manejo de anticipos mediante pagos y contabilización de atenciones y funcionarios, señalando que el POS soporta:

- Facturación directa de ventas con posibilidad de aplicar descuentos y promociones.
- Emisión de notas crédito/débito desde la interfaz de POS para reversión de ventas.[^1]
- Manejo de anticipos de clientes, aplicados posteriormente a ventas.[^1]

En el contexto PDV 8.5, el manual de acumulación de ventas y el manejo de consecutivo 999999 indican que el sistema:

- Lleva consecutivos de venta a nivel de punto de venta y maneja escenarios donde se alcanza el límite numérico.[^2]
- Ofrece procesos de acumulación de ventas, probablemente para consolidar tickets a nivel de cliente o cierre de jornada.[^2]

### 4.2. Gestión de clientes y bloqueo/modificación

Un manual específico titulado "Bloqueo y modificación de clientes POS" explica que se añadió una mejora para evitar que usuarios modifiquen clientes POS previamente creados con el fin de no crear nuevos registros.  Desde el Administrador de seguridad se retiran permisos de modificar clientes POS y de modificar el indicador de bloqueo de edición, controlando quién puede alterar datos de clientes.[^7]

Esto muestra que el POS administra un maestro de clientes (con datos de identificación, tributarios y comerciales) y que la seguridad se puede granular a nivel de operaciones sobre clientes, ajustando el riesgo de corrupción de datos.  Un nuevo POS deberá soportar estos controles de edición, incluyendo perfiles con permisos específicos.[^7]

### 4.3. Manejo de resoluciones de facturación y requisitos DIAN

Hay múltiples manuales y comunicados sobre resoluciones DIAN (000042, 000165, 001092, 000012, 000238, entre otras) y anexos técnicos (1.8, 1.9, 1.0) que afectan la forma en que el POS genera facturas electrónicas y documentos equivalentes.  En particular:[^6][^7][^4]

- Manuales de "configuración de UVT (factores de unidad tributaria) para facturación electrónica – Siesa POS".[^4]
- Manual "Impresión de factura electrónica desde el POS – Siesa POS".[^4]
- Manuales de configuración de equivalencias (país, moneda, unidad de medida, tipo de identificación, impuestos, medios de pago, conceptos ND/NC) en Siesa 8.5 y Enterprise que aplican a documentos generados desde POS.[^7][^4]

Desde la perspectiva de un nuevo POS, esto implica:

- Soportar resolución de facturación con rangos de numeración, vigencia, código DIAN y tipo de documento.
- Generar facturas electrónicas, notas crédito y débito cumpliendo anexos UBL 2.1, con equivalencias correctas a maestros del ERP.
- Imprimir representación gráfica conforme a requerimientos DIAN, incluyendo QR, CUFE/cuivalor y textos legales.

### 4.4. Operación desconectada, transmisión y recepción

El manual "procedimientos de transmisión y recepción del Sistema PDV almacén Siesa 8.5" describe el proceso de sincronización entre las cajas PDV y el servidor central, incluyendo transmisión de ventas, recepción de maestros y resolución de facturación.  Además, la descripción comercial de Siesa POS indica explícitamente que garantiza que la facturación no se interrumpa al perder conectividad con el servidor central, permitiendo continuidad y posterior recuperación.[^3][^2]

Este comportamiento suele implicar:

- Una base de datos local o archivo de cola para tickets generados offline.
- Proceso programado o manual para subir ventas al servidor cuando vuelve la conexión.
- Mecanismo para bloquear la operación si se alcanza determinado límite de tickets offline o límite de fecha de resolución.

Cualquier nuevo POS que pretenda ser "como mínimo" equivalente debe contemplar este escenario de operación desconectada, si la empresa actual lo utiliza.

### 4.5. Impuestos, descuentos y promociones

Siesa Inventario incluye manuales para configuración de impuestos especiales (impuestos saludables, ADV, impuesto al consumo de licores) y su aplicación en facturación desde inventario, lo que se refleja en la lógica de POS al vender ítems afectados.  Existen manuales específicos de "Parametrización para descuentos en ventas en el módulo comercial – Siesa 8.5" y "Grupos de descuentos – Siesa Enterprise" que permiten definir descuentos por grupos de productos o clientes.[^4][^1]

Esto implica que el POS debe:

- Aplicar impuestos específicos por artículo, según tablas configuradas en inventarios/comercial.
- Permitir definir y aplicar descuentos globales o por línea, posiblemente condicionados a perfiles de usuario y promociones activas.
- Respetar reglas de día sin IVA (decretos 682 y resoluciones 2155), ajustando tarifas y exenciones según la fecha y tipo de producto.

### 4.6. Informes y acumulación de ventas

En Siesa 8.5 se mencionan "Informes Siesa POS" y cursos como "Tips acumulación POS Siesa 8.5", además de manuales de listados por proveedor, número y consulta en cuentas por pagar y otros módulos.  Esto sugiere que el POS genera reportes operativos como:[^4]

- Acumulación de ventas por caja, por cajero, por día.
- Detalle de ventas por producto, categoría y cliente.
- Cierres de caja con cuadre de efectivo, tarjetas y otros medios de pago.

La empresa para la que desarrollas el nuevo POS necesitará estos informes mínimos para controlar operación diaria y conciliaciones.

## 5. Seguridad y administración desde Siesa Enterprise/Zeus

### 5.1. Perfiles, usuarios y métodos de seguridad

El portal de manuales incluye una sección de "Administrador de seguridad" con manuales sobre usuarios, métodos y administración de perfiles.  El manual de bloqueo/modificación de clientes POS se apoya explícitamente en este administrador de seguridad para controlar permisos sobre clientes POS.[^7][^4]

En general, la seguridad del POS se basa en:

- Definición de perfiles con permisos sobre módulos concretos (POS central, maestros de clientes, modificación de indicadores, etc.).[^7][^4]
- Asignación de usuarios internos y vinculación con empleados/cajeros.[^9]
- Métodos de autenticación y posiblemente políticas de contraseña administradas desde la capa Enterprise.

Un nuevo POS debe soportar integración con un administrador de seguridad central o replicar un mecanismo equivalente, incluyendo perfiles, roles y permisos por operación.

### 5.2. Manejo de errores y logs

Siesa Enterprise y Siesa 8.5 tienen numerosos manuales de "solución a errores" con códigos como NSAJ73, VLR01, DSAB10, DSBA19b, ZB01, entre otros, relacionados con gestión de documentos electrónicos y POS.  Esto indica que:[^7][^4]

- El POS y PDV reportan errores específicos cuando fallan transmisiones, validaciones DIAN o operaciones de caja.
- Existen logs de errores y herramientas como "Log de errores – Enterprise" para diagnóstico.[^4]

En el diseño de un nuevo POS es recomendable incluir:

- Modelo explícito de códigos y mensajes de error documentados.
- Logs auditables de operaciones (ventas, anulaciones, modificaciones de clientes, cambios de resolución).

## 6. Arquitectura y componentes implicados

### 6.1. Capas del sistema POS de Siesa

A partir de la documentación accesible se puede inferir que el sistema POS de Siesa típico para retail funciona en varias capas integradas:

- **Capa de caja/PDV**: aplicación local (Java/cliente rich) sobre Linux/Windows que ejecuta ventas, maneja usuarios cajeros, imprime tickets y puede operar desconectada.[^1][^4][^2]
- **Capa de administración POS central**: módulo en Siesa Enterprise/Zeus que configura TPV (terminales de punto de venta), maestros de clientes POS, resoluciones, perfiles y parámetros fiscales.[^10][^7][^4]
- **Capa ERP (contabilidad, inventarios, compras, financiero)**: maneja maestros de artículos, cuentas contables, impuestos, documentos soporte, medios de pago y los registros contables de las ventas del POS.[^1][^4]
- **Capa de facturación electrónica/PT Siesa e-Invoicing**: responsable de transmisión DIAN, anexos técnicos, equivalencias UBL, eventos de factura y recepción de documentos electrónicos; el POS alimenta esta capa con documentos.[^6][^7][^4]

Cualquier sustitución del POS debe considerar qué capas seguirán utilizando Siesa y cuáles se reemplazarán, para mantener compatibilidad de datos y procesos.

### 6.2. Integración y flujos de datos

Los manuales de transmisión/recepción PDV, generación de facturas electrónicas, equivalencias UBL y errores de transmisión apuntan a flujos típicos:

1. La caja POS/PDV genera ventas y las almacena localmente.
2. Se transmite la información al servidor PDV/ERP mediante procesos de transmisión (PDV almacén) o servicios.[^4][^2]
3. El ERP genera documentos contables y electrónicos, aplicando impuestos, equivalencias y resoluciones.[^7][^4]
4. El proveedor tecnológico Siesa e-Invoicing realiza la validación DIAN, generando eventos y posibles errores.[^6][^4]

Para una empresa que sólo cambia el módulo POS pero mantiene Siesa como ERP, el nuevo POS deberá integrarse con los procesos de transmisión definidos por Siesa (por ejemplo, con formatos o servicios ya establecidos). Si se reemplaza todo, habrá que replicar esos flujos.[^1][^2]

## 7. Código fuente y disponibilidad técnica

No hay evidencia pública de que el código fuente de Siesa POS o de los módulos PDV/POS de Siesa 8.5/Enterprise esté disponible; los manuales y documentación son de producto cerrado, orientados a usuarios finales y administradores.  La presencia de manuales sobre Java, web services, configuraciones y errores confirma que es un software propietario con componentes Java, pero no se exponen APIs de código ni repositorios de ejemplo.[^1][^4]

Para el diseño de tu propio POS, será necesario basarse en estas especificaciones funcionales y en la observación directa del sistema actual (pantallas, flujos, formatos de transmisión), más que en reutilizar código existente.

## 8. Conjunto mínimo de requisitos para tu nuevo POS

Con base en la funcionalidad inferida de los manuales y descripciones de Siesa POS/PDV, el nuevo POS debería cubrir como mínimo:

- Gestión de usuarios cajeros, perfiles y permisos, incluyendo creación, bloqueo y restricción de edición de clientes.
- Apertura/cierre de caja, arqueos, control de turnos y medios de pago.
- Registro de ventas con soporte de múltiples formas de pago (efectivo, tarjetas, vales, etc.) y manejo de anticipos.
- Manejo de maestros de clientes y productos, con impuestos específicos y descuentos/promociones aplicables.
- Generación de facturas, notas crédito y notas débito, ajustadas a resoluciones de facturación vigentes.
- Operación desconectada con almacenamiento local y proceso de transmisión/recepción de información hacia un servidor central.
- Gestión de consecutivos de venta, incluyendo escenarios de límites y reutilización controlada.
- Integración con módulo de inventarios para actualización de existencias y costos.
- Integración con contabilidad/financiero para registros de cuentas por cobrar, ingresos y documentos soporte en compras.
- Soporte a facturación electrónica conforme anexos DIAN (resoluciones 000042, 000165, 001092 y anexos 1.8, 1.9, 1.0) si la empresa los requiere.
- Informes operativos de ventas, cierres de caja, acumulación POS y estadísticas por producto, cliente y cajero.

Este conjunto se fundamenta en las funcionalidades observadas en los manuales de Siesa POS y PDV, aunque para tu caso concreto será clave revisar los procesos específicos de la empresa (carnes y frutas, manejo de pesos, lotes, fechas de vencimiento) y mapearlos sobre esta base técnica.

---

## References

1. [Manuales – Soporte Siesa | Siesa Customer Support](https://pruebascustomersupport.siesacloud.com/manuales-3/)

2. [Sistema de Ventas PDV - Soporte Siesa](https://www.siesacustomersupport.com/category/manuales/siesa-85/sistema-de-ventas-pdv/)

3. [Siesa POS](https://www.capterra.co/software/1023938/siesa-pos) - ¿Qué piensan los usuarios de Siesa POS? Lee las reseñas y opiniones verificadas, descubre sus caract...

4. [Manuales – Soporte Siesa | Siesa Customer Support](https://www.siesacustomersupport.com/manuales-2/)

5. [Retail del futuro | Siesa Punto de Venta (POS) - YouTube](https://www.youtube.com/watch?v=mZTC7sUMSTA) - ... Retail de Futuro, descubrimos las últimas tendencias en el mundo del retail y presentamos nuestr...

6. [Retail inteligente con Siesa: cuando la tecnología se convierte en ...](https://www.retaildelfuturo.com/retail-inteligente-con-siesa-cuando-la-tecnologia-se-convierte-en-ventaja-competitiva/) - En este escenario, soluciones como Siesa Punto de Venta están diseñadas para integrar la operación e...

7. [[PDF] Bloqueo y modificación de clientes POS](https://www.siesacustomersupport.com/wp-content/uploads/2025/10/Manual-Bloqueo-y-modificacion-de-clientes-POS-Gestion-de-Puntos-de-Venta.pdf)

8. [Siesa - Facebook](https://www.facebook.com/siesaoficial/photos/siesapos-siesa-pos-es-la-soluci%C3%B3n-escogida-por-m%C3%A1s-de-800-empresas-de-retail-que/1646120148781169/?locale=es_LA) - #SiesaPos Siesa POS es la solución escogida por más de 800 empresas de retail que facilita la gestió...

9. [Manual_Cómo-crear-un-usuario-cajero-para-usar-en-el-Siesa-Pos11](https://es.scribd.com/document/587401126/Manual-Co-mo-crear-un-usuario-cajero-para-usar-en-el-Siesa-Pos11) - Crear un usuario cajero requiere: 1) crear el usuario como interno en el administrador de seguridad,...

10. [Installation Guide for Siesa POS and SQL Server Setup | Course Hero](https://www.coursehero.com/es/file/235048944/Manual-de-Instalaci%C3%B3n-de-Siesa-POS-en-Cajas-Desconectada-2docx/) - Para ellos vamos al Módulo de POS Central –> Pos Central -> Configuración TPV -> TPV (Terminal punto...

