# ECC con lo nativo de Claude Code (skills + subagentes)

"ECC" (Everything Claude Code) no es un framework instalado en este entorno. Su idea central —
**organizar el trabajo con skills (módulos de workflow/conocimiento) y subagentes (ejecutores
delegados con contexto aislado)** — se cubre **con lo nativo de Claude Code**. Este documento
explica cómo lo aplicamos en `pos-siesa-remake`.

## Skills (`.claude/skills/<nombre>/SKILL.md`)

Un skill es una carpeta con `SKILL.md` (frontmatter `name` + `description`). Claude carga el
skill cuando la tarea coincide con su descripción.

| Skill | Cuándo cargarlo |
|---|---|
| `pos-dominio` | Al tocar **cualquier** código de negocio del POS (entidades, ventas, caja, inventario, clientes, impuestos, peso). |
| `facturacion-dian` | Al trabajar en facturación electrónica / cumplimiento DIAN. |
| `db-design-pos` | Al diseñar o modificar tablas / modelo de datos. |
| `testing-pos` | Al escribir o reorganizar pruebas. |

## Subagentes (`.claude/agents/<nombre>.md`)

Un subagente es un prompt con su propio contexto y herramientas acotadas. Se invoca para tareas
especializadas sin contaminar el hilo principal.

| Subagente | Rol | Herramientas |
|---|---|---|
| `arquitecto-pos` | Revisa arquitectura global y cambios grandes; guarda el aislamiento de capas. | solo lectura |
| `auditor-dian` | Audita facturación electrónica y cumplimiento DIAN. | solo lectura |
| `refactor-deadcode` | Limpia código muerto, simplifica, aplica Ponytail (sin cambiar comportamiento). | lectura + edición + bash |

## Flujo de trabajo propuesto

1. **Antes de codear una funcionalidad de negocio:** cargar `pos-dominio` (y `db-design-pos` si
   toca tablas, `facturacion-dian` si toca DIAN).
2. **Al escribir pruebas:** cargar `testing-pos`.
3. **Antes de un cambio estructural grande o un módulo nuevo:** invocar `arquitecto-pos` para
   revisar la frontera de capas.
4. **Antes de dar por terminado algo de DIAN:** invocar `auditor-dian`.
5. **Después de aterrizar una feature o cuando un módulo se infle:** invocar `refactor-deadcode`.

## Por qué así (y no un plugin externo)

- **Cero dependencias nuevas** (Ponytail): usamos lo que Claude Code ya trae.
- **Contexto separado por rol:** cada skill/subagente acota qué conocimiento y permisos entran,
  reduciendo errores.
- **Versionado con el repo:** skills y agentes viven en `.claude/` y viajan con el proyecto
  (excepto `settings.local.json`, que es personal y va en `.gitignore`).
