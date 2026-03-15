---
description: Ejecutar validación completa del proyecto (lint + format + tests + import check)
---

# /validar

Ejecuta todas las validaciones del proyecto en secuencia.

## Pasos

1. Verificar lint con ruff
```bash
ruff check .
```

2. Verificar formato con ruff
```bash
ruff format --check .
```

3. Ejecutar tests (si existen)
```bash
pytest tests/ -v
```

4. Verificar que la app arranca
```bash
python -c "from app import app; print('✅ App OK')"
```

## Resultado esperado

Todos los comandos deben pasar con código de salida 0.
Si alguno falla, corregir antes de continuar.
