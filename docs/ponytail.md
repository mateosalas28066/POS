# Ponytail — filosofía de mínimo código necesario

Ponytail es la regla de trabajo de `pos-siesa-remake`: **escribir solo el código mínimo
necesario**. No es un plugin instalado en este entorno (ver [ponytail-instalar.md](ponytail-instalar.md));
aquí se aplica como disciplina documentada, reforzada por el subagente `refactor-deadcode`.

## Las 4 preguntas (en orden, antes de escribir cualquier código)

1. **¿Hace falta de verdad?**
   Si no resuelve un requisito real y **presente**, no se escribe. Nada "por si acaso" (YAGNI).
2. **¿Lo resuelve la stdlib?**
   Preferir la biblioteca estándar de Python antes que añadir una dependencia nueva.
3. **¿Es nativo / ya existe?**
   Reutilizar lo que el framework ya ofrece (Qt para UI/eventos, `sqlite3` para datos) antes de
   construir abstracciones propias.
4. **¿Se puede más simple / en menos líneas?**
   Reducir sin sacrificar legibilidad. Menos código = menos superficie de error.

## Cómo se aplica en este proyecto

- **Costuras sí, implementación no:** `facturacion_dian/` y `sync_pdv/` existen como interfaces
  y stubs. No se implementan a fondo hasta que haya un requisito real (proveedor DIAN elegido,
  segundo local conectado).
- **Modelo de datos reservado pero vacío:** `lotes` y maestros DIAN se **definen** para no
  romper el modelo después, pero su lógica no se escribe hasta usarse.
- **Una dependencia nueva = una decisión:** justificar por qué la stdlib o Qt no bastan.
- **Adaptadores intercambiables:** el puerto `LectorPeso` evita duplicar lógica de peso entre
  balanza, GS1 e ingreso manual.

## Señales de que estás rompiendo Ponytail

- Abstracciones con un solo caso de uso ("framework" propio sin segundo consumidor).
- Dependencias que duplican algo de la stdlib/Qt.
- Código muerto, parámetros que nadie pasa, ramas inalcanzables.
- Implementar hoy una capa (multi-local, DIAN real) que aún no tiene requisito.

Cuando aparezcan, invocar el subagente `refactor-deadcode` (preserva comportamiento, verifica
con `pytest`).
