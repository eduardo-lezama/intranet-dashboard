---
trigger: model_decision
description: Aplicar cuando se trabaje en blueprints/, config.py, app.py, o se creen/modifiquen endpoints API y clientes de servicios externos
---

# Backend - Flask y APIs

## Arquitectura de Capas

```
app.py (Factory)
    ↓
config.py (Config classes)
    ↓
blueprints/main.py (Rutas + endpoints)
    ↓
blueprints/*_client.py (Clientes API externos)
    ↓
cache.py (Flask-Caching)
```

## Patrón de Endpoint API

```python
@main_bp.route('/api/[recurso]')
@cache.cached(timeout=180)  # Ajustar según frecuencia de cambio
def api_recurso():
    """Docstring describiendo el endpoint"""
    try:
        # 1. Obtener config
        url = current_app.config.get('SERVICIO_URL')
        token = current_app.config.get('SERVICIO_TOKEN')
        
        if not url:
            return jsonify({'error': 'SERVICIO_URL no configurado'}), 500
        
        # 2. Llamar cliente
        client = ServicioClient(url, token)
        data = client.get_data()
        
        # 3. Retornar JSON
        return jsonify(data)
        
    except Exception as e:
        current_app.logger.error(f"Error [recurso]: {str(e)}")
        return jsonify({'error': str(e)}), 500
```

## Patrón de Cliente API

```python
class ServicioClient:
    """Cliente para API de [Servicio]"""
    
    def __init__(self, base_url, api_token=None, timeout=None):
        self.base_url = base_url.rstrip('/')
        self.api_token = api_token
        self.timeout = timeout or 15
        self.headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json'
        } if self.api_token else {}
    
    def get_data(self):
        """Obtiene datos del servicio"""
        url = f"{self.base_url}/api/endpoint"
        response = requests.get(
            url, 
            headers=self.headers, 
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()
```

## Configuración Multi-Entorno

```python
# En config.py - usar env_target() para URLs que cambian entre local/NAS
SERVICIO_URL = env_target(
    'SERVICIO_URL',
    default_local='http://servicio.local',    # Dominio interno
    default_nas='http://servicio:puerto'       # Docker networking
)
```

## Cache Timeouts Recomendados

| Tipo de dato | Timeout | Ejemplo |
|--------------|---------|---------|
| Tiempo real | 60-180s | Pi-hole stats |
| Semi-estático | 300-600s | Recetas Mealie |
| Estático | 900-3600s | Settle Up balance |

## Rutas de Archivos Clave

- **Nuevo endpoint**: `blueprints/main.py`
- **Nuevo cliente API**: `blueprints/[servicio]_client.py`
- **Nueva config**: `config.py` (clase Config)
- **Nueva variable .env**: `.env` + documentar en README.md
