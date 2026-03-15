---
trigger: model_decision
description: Aplicar siempre al inicio de cualquier tarea nueva o cuando el usuario pida implementar algo
---

# Orquestador - Protocolo de Tareas

<pre_tarea>
## Antes de Empezar CUALQUIER Tarea

1. **Identificar dominio**: ¿Backend / Frontend / Ambos / Config?
2. **Leer archivos relacionados** ANTES de modificar nada
3. **Verificar skills**: ¿Existe una skill que aplique? Si sí, usarla
4. **Definir scope**: Qué archivos tocar y cuáles NO
5. **Verificar versiones**: Si usas una API/librería, comprobar versión en `requirements.txt` o `pyproject.toml`
</pre_tarea>

<durante_tarea>
## Durante la Tarea

- **NO instales dependencias** sin preguntar primero
- **NO modifiques archivos** fuera del scope definido
- **NO elimines código** sin preguntar aunque parezca muerto
- **NO cambies interfaces públicas** sin avisar del impacto
- **Si encuentras algo inesperado**, para y comunícalo
</durante_tarea>

<post_tarea>
## Al Terminar (en este orden)

1. `ruff check .` — debe pasar con 0 errores
2. `ruff format --check .` — debe pasar
3. `pytest tests/ -v` — todos en verde (si hay tests)
4. `python -c "from app import app"` — import check
5. Confirmar qué archivos se han modificado
6. Proponer commit siguiendo Conventional Commits

**La tarea NO está completa hasta que los 4 primeros pasen.**
</post_tarea>

## Skills Disponibles

| Skill | Cuándo usar |
|-------|-------------|
| `@commit` | Al preparar cualquier commit |
| `@nueva-feature` | Implementar funcionalidad nueva |
| `@crear-endpoint` | Crear nuevo endpoint API |
| `@crear-cliente` | Crear cliente para servicio externo |
| `@crear-widget` | Crear widget JS en dashboard |
| `@añadir-servicio` | Integrar servicio completo (config→cliente→endpoint→widget) |
| `@refactor` | Refactorizar código existente |
| `@limpiar-duplicados` | Eliminar código duplicado |
| `@debug` | Investigar un bug |
| `@test` | Crear o modificar tests |

## Checklist Rápido

```
[ ] ¿He leído los archivos antes de modificar?
[ ] ¿Estoy dentro del scope definido?
[ ] ¿He usado la skill correcta si existe?
[ ] ¿ruff check pasa?
[ ] ¿La app arranca?
[ ] ¿El commit sigue Conventional Commits?
```
