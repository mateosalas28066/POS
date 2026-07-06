# Prompt — Resolver errores acumulados (POS carnes y frutas)

Copia todo lo que sigue como primer mensaje de la nueva sesión.

---

Trabaja en el repo **pos-siesa-remake** en `w:\POS` (POS autónomo Python + PySide6 + SQLite,
arquitectura hexagonal). Tu tarea es **arreglar directamente** una lista de errores acumulados
—funcionales, visuales y de comodidad— ya auditados y documentados.

## Fuente de verdad

Todo está en **[Errores.md](../../../Errores.md)** (`w:\POS\Errores.md`). Léelo completo antes de
tocar nada: cada ítem trae ubicación (`archivo:línea`), comportamiento esperado y prioridad.
Ese MD **es tu backlog**: resuélvelo tal cual, no lo reinterpretes.

## Reglas de trabajo (importante)

- **NO escribas specs ni planes de implementación.** Nada de `docs/superpowers/specs|plans`.
  Resuelve cada ítem directo en el código, guiándote por el MD.
- **Alcance:** arregla **todos los ítems del MD EXCEPTO F6** (marcado ⛔ FUERA DE ALCANCE:
  validaciones automáticas de fecha/porcentaje en promociones). Todo lo demás sí:
  F1, F2, F3, F4, F5, F7, V1, V2, V3, V4, C1, C2, C3, C4.
- Sigue las **reglas Ponytail** (mínimo código necesario, YAGNI, stdlib primero, reutiliza lo
  nativo de Qt) y la **arquitectura hexagonal**: `src/core/` no conoce Qt ni SQLite; el SQL vive
  solo en los adaptadores de repositorio. Estos fixes son casi todos de UI (`src/caja/`), así que
  no deberías tocar `core/` salvo que un ítem lo pida.
- **Aprovecha soluciones compartidas** que el MD ya sugiere: C1+C2 → una sola subclase central de
  spinbox (p.ej. `SpinMoneda`/`SpinBoxPos` con `focusInEvent → selectAll()` y
  `setGroupSeparatorShown(True)`) reutilizada en los 8 archivos; F1+F2 → un mismo manejo del estado
  del conteo. No repitas lógica archivo por archivo si puedes centralizarla.
- **Tests:** hay una suite pytest (`python -m pytest -q`, hoy **318 passed**). Corre la suite antes
  de empezar (baseline) y después de cada grupo de cambios. Si tu cambio rompe un test, decide si el
  test asumía el comportamiento viejo (actualízalo) o si introdujiste un bug (arréglalo). Para lógica
  nueva no trivial (p.ej. persistencia del desglose de conteo, reordenamiento de grilla), **agrega
  tests** siguiendo la convención del proyecto (`tests/` espejo de `src/`, `test_*.py`). Para ajustes
  puramente visuales (QSS, tamaños), verificación manual basta.
- **Verifica en la app real** los ítems visuales/UX: `python -m caja` (admin por defecto
  `admin` / `admin1234`). El MD tiene una sección "4. Cómo verificar" con los pasos por ítem.
- **Git:** estás en `master`. **Crea una rama antes de commitear** (p.ej.
  `fix/errores-acumulados`). Commits pequeños y temáticos por ítem o grupo de ítems, en español,
  estilo del repo (`fix(conteo): ...`, `fix(reportes): ...`, `fix(venta): ...`). **No hagas merge
  ni push sin preguntar.**
- A medida que cierres cada ítem, **marca su encabezado en Errores.md con ✅**. Al terminar,
  actualiza el conteo de tests en `docs/README-pos.md` si cambió.

## Orden sugerido

Ataca primero los 🔴 (F1, F2, F3, F4, V1, C1), luego 🟡 (F5, V2, V3, C2), luego 🟢 (F7, V4, C3, C4).
C1 y C2 conviene hacerlos temprano porque la subclase de spinbox la reutilizarás en varios otros
ítems.

## Al terminar

- Suite `python -m pytest -q` en verde.
- Errores.md con todos los ítems en alcance marcados ✅ (F6 sigue ⛔).
- Rama lista con los commits. Reporta un resumen de qué se arregló y cómo se verificó cada cosa,
  y **pregunta** antes de integrar (merge/PR) — no lo hagas por tu cuenta.

Carga la skill `superpowers:using-superpowers` al arrancar y las que apliquen (p.ej.
`testing-pos` al escribir pruebas, `pos-dominio` si algún fix toca lógica de negocio).
