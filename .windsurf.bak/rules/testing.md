---
trigger: model_decision
description: Aplicar al crear o modificar tests, o cuando se pida validar funcionalidad
---

# Testing - pytest

## Configuración

- **Framework**: pytest 8.1.1
- **Config**: `pyproject.toml` sección `[tool.pytest.ini_options]`
- **Carpeta**: `tests/`
- **Comando**: `pytest tests/ -v`

## Estructura de Tests

```
tests/
├── __init__.py
├── conftest.py           # Fixtures compartidos
├── test_app.py           # Tests de la app Flask
├── test_endpoints.py     # Tests de endpoints API
└── test_clients.py       # Tests de clientes externos
```

## Fixture Base (conftest.py)

```python
import pytest
from app import create_app


@pytest.fixture
def app():
    """Crear app en modo testing"""
    app = create_app('development')
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app):
    """Cliente de test Flask"""
    return app.test_client()
```

## Patrón de Test de Endpoint

```python
def test_api_status_returns_ok(client):
    """GET /api/status debe retornar status ok"""
    response = client.get('/api/status')
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'ok'
    assert 'timestamp' in data
```

## Patrón de Test de Cliente

```python
from unittest.mock import patch, Mock

def test_energy_client_handles_timeout():
    """EnergyClient debe manejar timeouts gracefully"""
    with patch('requests.get') as mock_get:
        mock_get.side_effect = requests.Timeout()
        
        client = EnergyClient('http://fake', 'token')
        result = client.get_monthly_consumption()
        
        assert result['consumption_kwh'] is None
        assert 'error' in result
```

## Comandos

```bash
pytest tests/ -v              # Todos los tests
pytest tests/test_app.py -v   # Un archivo
pytest -k "test_api" -v       # Por nombre
pytest --tb=short             # Traceback corto
pytest -x                     # Parar en primer fallo
```

## Convenciones

- Nombres: `test_[qué]_[condición]_[resultado esperado]`
- Un assert principal por test (pueden haber auxiliares)
- Usar fixtures para setup repetitivo
- Mock de APIs externas (nunca llamar a servicios reales)
