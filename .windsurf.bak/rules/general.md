---
trigger: always_on
---

# General - Stack y Convenciones

## Infraestructura de Despliegue

| Componente | Especificación |
|------------|----------------|
| **NAS** | QNAP TS-264 |
| **RAM** | 8 GB |
| **OS** | QTS 5.2.8.x |
| **Container** | Container Station (Docker) |
| **Proxy** | Nginx Proxy Manager |
| **Red** | 192.168.1.x (intranet_net, ha_net) |

**Límites de recursos del contenedor intranet (optimizado):**
- CPU: 0.5 cores (límite), 0.25 cores (reserva)
- RAM: 384 MB (límite), 192 MB (reserva)
- Workers Gunicorn: 1 worker, 4 threads (gthread)
- Cache: FileSystemCache persistente en /app/cache

## Stack Técnico Detallado

<stack>
| Capa | Tecnología | Versión |
|------|------------|---------|
| Runtime | Python | 3.11 |
| Framework | Flask | 3.0.2 |
| WSGI | Gunicorn | 21.2.0 |
| Cache | Flask-Caching | 2.3.1 (FileSystemCache) |
| HTTP Client | Requests | 2.31.0 |
| Env | python-dotenv | 1.0.1 |
| Linter | ruff | 0.3.4 |
| Tests | pytest | 8.1.1 |
| Frontend | JavaScript ES6+ | Vanilla |
| CSS | Variables + BEM | Dark theme |
| Icons | Bootstrap Icons | 1.11.0 (CDN) |
</stack>

## Estructura de Carpetas

```
intranet/
├── app.py              # Factory: create_app()
├── config.py           # Config classes + env_target()
├── cache.py            # Flask-Caching singleton
├── blueprints/         # Rutas + clientes API
│   ├── main.py         # Blueprint principal
│   ├── energy_client.py
│   ├── mealie_client.py
│   ├── pihole_auth.py
│   └── settleup_client.py
├── templates/          # Jinja2
│   ├── base.html
│   ├── dashboard.html
│   └── errors/
├── static/
│   ├── css/            # variables.css, base.css, components.css
│   └── js/             # main.js (utils), dashboard.js (clase)
├── tests/              # pytest (crear si no existe)
├── pyproject.toml      # Config ruff + pytest
└── requirements.txt
```

## Naming Conventions

<naming>
**Python:**
- Clases: `PascalCase` → `EnergyClient`, `MealieClient`
- Funciones/métodos: `snake_case` → `get_monthly_cost`
- Variables: `snake_case` → `base_url`, `api_token`
- Constantes config: `SCREAMING_SNAKE` → `API_TIMEOUT`

**JavaScript:**
- Clases: `PascalCase` → `class Dashboard`
- Funciones/métodos: `camelCase` → `loadWeatherData`
- Variables: `camelCase` → `weatherWidget`

**CSS:**
- BEM: `block__element--modifier`
- Variables: `--kebab-case` → `--color-bg-primary`
</naming>

## Antipatrones (NO hacer)

<antipatrones>
❌ Imports desordenados - usar ruff para ordenar (I rules)
❌ `print()` para debug - usar `current_app.logger`
❌ Catch genérico sin logging - siempre loguear errores
❌ Hardcodear URLs - usar `current_app.config.get()`
❌ Modificar estado global en endpoints - usar patrón cliente
</antipatrones>

## Patrón de Imports Correcto

```python
# 1. Stdlib
import os
from datetime import datetime
from pathlib import Path

# 2. Third-party
import requests
from flask import Blueprint, jsonify, current_app

# 3. Local
from blueprints.energy_client import EnergyClient
from cache import cache
```
