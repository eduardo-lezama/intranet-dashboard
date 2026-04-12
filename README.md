| Vista |
|------|
| **Dashboard** |
| <p align="center"><img src="assets/intranet.png" width="80%"></p> |
| **Menu Processor** |
| <p align="center"><img src="assets/menu_processor.png" width="50%"></p> |

# Intranet Casa - Dashboard v2.0

Personal intranet dashboard for home management, deployed on a QNAP TS-264 NAS. Built as a Flask monolith with multiple service integrations, a "Bento 2.0" frontend design, and optimized for low-resource Docker containers.

## Features

- **Bento 2.0 Grid** - Hierarchical card layout with micro-interactions and staggered CSS animations
- **Dark theme** - "Warm Observatory" aesthetic (forest green + amber accents)
- **Pi-hole** - DNS ad-blocking statistics
- **Mealie** - Recipe management and daily meal plans
- **Home Assistant** - Energy consumption (kWh, cost, real-time power) and IoT device states
- **OpenWeatherMap** - Current weather and 5-day forecast (server-side proxy)
- **Settle Up** - Shared finances with group balance
- **Shopping list** - Shared list with SQLite persistence
- **Documents** - NAS-mounted file browser
- **DNSCrypt-proxy** - Encrypted DNS health check
- **Menu Processor** - Weekly menu processing with dynamic service state

## Architecture

```
intranet/
├── app.py                    # Flask factory (create_app)
├── config.py                 # Configuration with env_target() for local/NAS
├── cache.py                  # Flask-Caching (FileSystemCache)
├── blueprints/
│   ├── __init__.py           # Central blueprint registration
│   ├── dashboard.py          # Page rendering (/, /finanzas)
│   ├── api/
│   │   ├── weather.py        # /api/weather (server-side proxy)
│   │   ├── pihole.py         # /api/pihole
│   │   ├── mealie.py         # /api/mealie
│   │   ├── energy.py         # /api/energy, /api/devices
│   │   ├── settleup.py       # /api/settleup
│   │   ├── shopping.py       # /api/shopping (SQLite CRUD)
│   │   ├── documents.py      # /api/docs/*, /docs/*
│   │   └── services.py       # /api/status, /api/health, /api/menu-processor, /api/dnscrypt
│   ├── energy_client.py      # Home Assistant energy client (parallel requests)
│   ├── mealie_client.py      # Mealie API client
│   ├── pihole_auth.py        # Pi-hole v6 authentication
│   └── settleup_client.py    # SettleUp/Firebase client (cached auth token)
├── static/
│   ├── css/                  # Design system: variables, base, components, dashboard
│   └── js/                   # main.js (utils) + dashboard.js (widget controller)
├── templates/                # Jinja2 templates
├── Dockerfile                # Alpine-based, non-root user, healthcheck
└── docker-compose.yml        # Full stack: NPM + Intranet + Mealie
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Flask 3.0 + Gunicorn (1 worker, 4 gthreads) |
| Frontend | Vanilla JS + CSS custom properties (no build step) |
| Caching | Flask-Caching with FileSystemCache |
| Database | SQLite (shopping list) |
| Container | Docker Alpine, non-root, resource-limited |
| Proxy | Nginx Proxy Manager |
| Fonts | Syne (display) + Outfit (body) via Google Fonts |

## Quick Start (Local Development)

```bash
# 1. Clone and setup
cd intranet
python -m venv venv
source venv/bin/activate    # Linux/Mac
venv\Scripts\activate       # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your API keys and service URLs

# 4. Run
python app.py
# Dashboard at http://localhost:5000
```

## Configuration

All secrets are loaded from environment variables. Copy `.env.example` to `.env` and fill in:

| Variable | Required | Description |
|----------|----------|-------------|
| `ENV_TARGET` | Yes | `local` or `nas` (resolves service URLs) |
| `OPENWEATHER_API_KEY` | No | OpenWeatherMap free API key |
| `PIHOLE_URL` | No | Pi-hole admin URL |
| `PIHOLE_PASSWORD` | No | Pi-hole v6 password |
| `HOMEASSISTANT_URL_*` | No | HA URL (local and NAS variants) |
| `HOMEASSISTANT_TOKEN` | No | HA long-lived access token |
| `MEALIE_BASE_URL_*` | No | Mealie URL (local and NAS variants) |
| `MEALIE_API_KEY` | No | Mealie API token |
| `SETTLEUP_*` | No | SettleUp credentials and Firebase API key |
| `DNSCRYPT_IP` | No | DNSCrypt-proxy server IP |

The `env_target()` helper in `config.py` resolves URLs based on `ENV_TARGET`:
- `local` -> uses `*_LOCAL` variant (browser-accessible URLs)
- `nas` -> uses `*_NAS` variant (Docker service-to-service URLs)

## API Endpoints

| Endpoint | Service | Cache | Method |
|----------|---------|-------|--------|
| `/api/weather` | OpenWeatherMap | 10 min | GET |
| `/api/pihole` | Pi-hole v6 | 5 min | GET |
| `/api/mealie` | Mealie | 5 min | GET |
| `/api/energy` | Home Assistant | 5 min | GET |
| `/api/devices` | Home Assistant | 1 min | GET |
| `/api/settleup` | SettleUp/Firebase | 15 min | GET |
| `/api/shopping` | SQLite | - | GET/POST/DELETE |
| `/api/docs/structure` | NAS filesystem | - | GET |
| `/api/menu-processor` | Menu Processor | 5 s | GET |
| `/api/dnscrypt` | DNSCrypt-proxy | 1 min | GET |
| `/api/health` | Internal | - | GET |
| `/api/status` | Internal | - | GET |

## Adding a New Service Integration

The codebase follows a consistent pattern for each service:

### 1. Create the API client (if needed)

```python
# blueprints/myservice_client.py
class MyServiceClient:
    def __init__(self, base_url, api_token):
        self.base_url = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {api_token}"}

    def get_data(self):
        response = requests.get(f"{self.base_url}/api/endpoint",
                                headers=self.headers, timeout=15)
        response.raise_for_status()
        return response.json()
```

### 2. Create the blueprint

```python
# blueprints/api/myservice.py
from flask import Blueprint, current_app, jsonify
from cache import cache

myservice_bp = Blueprint("api_myservice", __name__)

@myservice_bp.route("/api/myservice")
@cache.cached(timeout=300)
def api_myservice():
    # ... fetch and return data
    return jsonify(data)
```

### 3. Register the blueprint

```python
# blueprints/__init__.py — add to register_blueprints()
from blueprints.api.myservice import myservice_bp
app.register_blueprint(myservice_bp)
```

### 4. Add configuration

```python
# config.py — add to Config class
MYSERVICE_URL = env_target("MYSERVICE_URL", "http://localhost:8080", "http://myservice:8080")
MYSERVICE_TOKEN = env_str("MYSERVICE_TOKEN", "")
```

### 5. Add the frontend widget

Add the card HTML to `templates/dashboard.html` and the data-loading method to `static/js/dashboard.js` following the existing pattern.

### 6. Add IoT devices

To add Home Assistant devices, edit `HA_DEVICES` in `config.py`:

```python
HA_DEVICES = {
    "power": [
        {"entity_id": "sensor.xxx", "name": "My Sensor", "icon": "...", "unit": "W"},
    ],
    "sensors": [
        {"entity_id": "binary_sensor.xxx", "name": "My Door", "icon": "...",
         "type": "binary", "state_on": "Open", "state_off": "Closed"},
    ],
}
```

## Docker Deployment

### Container Resources

Optimized for constrained NAS hardware:

| Resource | Limit | Reservation |
|----------|-------|-------------|
| Memory | 384 MB | 192 MB |
| CPU | 0.5 cores | 0.25 cores |

Gunicorn runs with **1 worker + 4 gthreads** — enough for a household dashboard while keeping memory under 100 MB typical.

### Build and Run

```bash
docker compose up -d --build intranet
```

### Persistent Volumes

The application requires persistent storage for:

| Volume | Container path | Purpose |
|--------|---------------|---------|
| App code | `/app` | Application source |
| Cache | `/app/cache` | Flask-Caching FileSystemCache (survives restarts) |
| Data | `/data` | SQLite database (`shopping.db`) |
| Documents | `/mnt/Documentos` | NAS documents (read-only mount) |

### Health Check

```bash
curl http://localhost:5000/api/health
# {"status": "healthy", "timestamp": "...", "version": "2.0.0"}
```

## Performance Notes

- **Parallel HTTP requests**: Energy, weather, and device endpoints use `ThreadPoolExecutor` to run independent API calls concurrently
- **Firebase token caching**: SettleUp client caches the Firebase auth token (1-hour TTL) instead of re-authenticating on each request
- **SQLite for shopping**: Thread-safe, transactional storage replacing the original CSV approach
- **FileSystemCache**: Disk-backed cache that persists across container restarts, reducing API load
- **`@starting-style` CSS animations**: Zero-JS entrance animations using native CSS (no requestAnimationFrame or IntersectionObserver overhead)
- **`prefers-reduced-motion`**: Respects user accessibility settings

## Development Tools

```bash
# Lint and format
ruff check . --fix
ruff format .

# Type of linting rules: see pyproject.toml [tool.ruff]
```

## License

MIT License
