---
trigger: always_on
---

# Git - Conventional Commits

## Formato de Commit

```
<tipo>(<scope>): <descripción corta>

[cuerpo opcional]

[footer opcional]
```

## Tipos Permitidos

| Tipo | Uso |
|------|-----|
| `feat` | Nueva funcionalidad |
| `fix` | Corrección de bug |
| `docs` | Solo documentación |
| `style` | Formato, sin cambio de lógica |
| `refactor` | Refactorización sin cambio funcional |
| `test` | Añadir o modificar tests |
| `chore` | Tareas de mantenimiento, deps |

## Scopes del Proyecto

| Scope | Carpeta/Área |
|-------|--------------|
| `api` | Endpoints en blueprints/main.py |
| `energy` | Cliente Home Assistant |
| `pihole` | Cliente Pi-hole |
| `mealie` | Cliente Mealie |
| `settleup` | Cliente Settle Up |
| `ui` | Templates y CSS |
| `js` | JavaScript frontend |
| `config` | Configuración y .env |
| `docker` | Dockerfile, compose |
| `deps` | requirements.txt |

## Ejemplos

```bash
# Nueva feature
feat(api): añadir endpoint /api/network para dispositivos WiFi

# Bug fix
fix(energy): manejar estado 'unavailable' de sensores HA

# Refactor
refactor(pihole): extraer lógica de auth a método separado

# Docs
docs(readme): actualizar instrucciones de instalación NAS

# Chore
chore(deps): actualizar Flask a 3.0.3
```

## Breaking Changes

Si el cambio rompe compatibilidad, añadir `!` y footer:

```
feat(api)!: cambiar respuesta de /api/energy a formato v2

BREAKING CHANGE: El campo 'cost' ahora es objeto en lugar de número.
Actualizar dashboard.js para usar data.cost.value
```

## Reglas

- Descripción en imperativo: "añadir", "corregir", "actualizar"
- Máximo 72 caracteres en primera línea
- Scope siempre en minúsculas
- No punto final en descripción
