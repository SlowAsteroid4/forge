# Seeds de Forge

Este directorio contiene archivos YAML con datos iniciales para los catálogos del sistema.

## Uso

```bash
# Cargar todos los seeds
uv run forge seed

# Cargar solo catálogos
uv run forge seed --no-players

# Cargar solo players
uv run forge seed --no-catalogs
```

## Archivos disponibles

- `engine_versions.yaml` - Versiones del motor de cálculo
- `players_yapsi.yaml` - Equipo Yapsi (ejemplo, reemplazar con datos reales)
- `classes.yaml` - Clases RPG (C01-C12) - TODO
- `avatars.yaml` - Avatares (A01-A16) - TODO
- `projects.yaml` - Proyectos/Dungeons (P01-P03) - TODO
- `buffs.yaml` - Buffs (B01-B17) - TODO
- `debuffs.yaml` - Debuffs (D01-D16) - TODO
- `achievements.yaml` - Achievements (ACH01-ACH12) - TODO
- `shop_items.yaml` - Items de tienda (S01-S08) - TODO

## Formato

Todos los archivos siguen el formato YAML estándar:

```yaml
- field1: value1
  field2: value2
- field1: value3
  field2: value4
```

## Importar desde Jira

Para players, la mejor opción es importar directamente desde Jira:

```bash
uv run forge sync --jql "project = SIMPL"
```

Esto creará automáticamente los registros de Player basándose en los assignees.
