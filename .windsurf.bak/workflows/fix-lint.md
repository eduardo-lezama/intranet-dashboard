---
description: Corregir automáticamente errores de lint y formato con ruff
---

# /fix-lint

Corrige automáticamente errores de lint y formato.

## Pasos

1. Corregir errores de lint automáticamente
```bash
ruff check --fix .
```

2. Formatear código
```bash
ruff format .
```

3. Verificar que no quedan errores
```bash
ruff check .
```

## Notas

- Algunos errores no son auto-corregibles y requieren intervención manual
- Revisar los cambios con `git diff` antes de commitear
