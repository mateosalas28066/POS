# Ponytail — instalación (si existe como plugin en tu marketplace)

**Estado en este entorno:** Ponytail **no** aparece como skill ni plugin instalado. No fue
posible "activarlo" como herramienta. Mientras tanto, su filosofía se aplica como disciplina
documentada en [ponytail.md](ponytail.md) + las reglas en [../CLAUDE.md](../CLAUDE.md), y la
hace cumplir el subagente `refactor-deadcode`.

Si Ponytail existe como plugin en algún marketplace al que tú tengas acceso, estas son las vías
habituales para instalarlo. Ejecútalas tú y dime el resultado.

## Opción A — Plugin desde un marketplace de Claude Code

```bash
# 1. Listar marketplaces conocidos / añadir el que contenga Ponytail
claude plugin marketplace list
claude plugin marketplace add <owner/repo-del-marketplace>

# 2. Buscar e instalar el plugin
claude plugin search ponytail
claude plugin install ponytail@<marketplace-id>
```

Luego habilítalo en el proyecto (en `.claude/settings.json`):

```json
{
  "enabledPlugins": {
    "ponytail@<marketplace-id>": true
  }
}
```

## Opción B — Desde la UI de Claude Code

1. Abre el menú de plugins (comando `/plugin` o el panel de extensiones del IDE).
2. Busca "Ponytail".
3. Instálalo y actívalo para este workspace.

## Opción C — Si Ponytail es solo un skill (carpeta con SKILL.md)

Si lo que tienes es un skill suelto (no un plugin), cópialo a:

```
.claude/skills/ponytail/SKILL.md
```

y reinicia Claude Code para que lo cargue.

## Si no lo encuentras

No pasa nada: el proyecto **no depende** de Ponytail como herramienta. La filosofía ya está
incorporada en `CLAUDE.md`, `docs/ponytail.md` y el subagente `refactor-deadcode`. Si más
adelante consigues el plugin oficial, lo enchufamos sin cambiar nada del código.
