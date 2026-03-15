"""
Configuración de la aplicación Flask
"""

import os


def env_str(name, default=""):
    """Get env var as trimmed string (guards against CRLF/trailing spaces)."""
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip()


def env_int(name, default=0):
    """Get env var as integer."""
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value.strip())
    except ValueError:
        return default


def env_target(name, default_local="", default_nas=""):
    """Resolve var by ENV_TARGET (local|nas) using *_LOCAL/*_NAS keys."""
    target = env_str("ENV_TARGET", "local").lower()
    local_key = f"{name}_LOCAL"
    nas_key = f"{name}_NAS"

    if target == "nas":
        return env_str(nas_key) or env_str(name, default_nas)

    return env_str(local_key) or env_str(name, default_local)


class Config:
    """Configuración base"""

    # Secret key para sesiones (cámbiala en producción)
    SECRET_KEY = env_str("SECRET_KEY") or "dev-secret-key-change-in-production"

    # Configuración de la aplicación
    DEBUG = env_str("FLASK_DEBUG", "False").lower() == "true"
    TESTING = False

    # Usuarios (simplificado para demo)
    USERS = {"default": {"name": "Usuario", "partner": "Pareja"}}

    # URLs de servicios (para enlaces en UI, no para llamadas servidor-a-servidor)
    # Nota: Estos enlaces son para el navegador del usuario, no para Docker networking
    # Defaults usan .local (genérico), configurar en .env con dominios reales
    SERVICES = {
        "homeassistant": {
            "name": "Home Assistant",
            "url": env_str("HOMEASSISTANT_URL_LOCAL", "http://ha.local"),
            "description": "Automatización del hogar y sensores IoT",
        },
        "mealie": {
            "name": "Mealie",
            "url": env_str("MEALIE_BASE_URL_LOCAL", "http://mealie.local"),
            "description": "Gestión de recetas y planificación de comidas",
        },
        "pihole": {
            "name": "Pi-hole",
            "url": env_str("PIHOLE_URL", "http://pi.hole/"),
            "description": "Bloqueo de anuncios en red",
        },
        "menu_processor": {
            "name": "Procesador de Menús",
            "url": env_str("MENU_PROCESSOR_URL_UI", "http://menu.local"),
            "description": "Procesador de menús semanales y listas de compra",
        },
    }

    # Cache persistente en disco (sobrevive reinicios del contenedor)
    CACHE_TYPE = "FileSystemCache"
    CACHE_DIR = "/app/cache"
    CACHE_DEFAULT_TIMEOUT = 900  # 15 minutos por defecto
    # API Keys (para futuras integraciones)
    OPENWEATHER_API_KEY = env_str("OPENWEATHER_API_KEY", "")

    # Pi-hole v6 - URL y password desde variables de entorno
    PIHOLE_URL = env_str("PIHOLE_URL", "http://pi.hole")
    PIHOLE_PASSWORD = env_str("PIHOLE_PASSWORD", "")

    # Ubicación para OpenWeather
    WEATHER_CITY = "Manresa"
    WEATHER_COUNTRY = "ES"

    # Configuración de base de datos (para futuro)
    # SQLALCHEMY_DATABASE_URI = 'sqlite:///intranet.db'
    # SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Settle up
    SETTLEUP_EMAIL = env_str("SETTLEUP_EMAIL")
    SETTLEUP_PASSWORD = env_str("SETTLEUP_PASSWORD")
    SETTLEUP_GROUP_ID = env_str("SETTLEUP_GROUP_ID")
    SETTLEUP_API_KEY = env_str("SETTLEUP_API_KEY")
    SETTLEUP_ENV = env_str("SETTLEUP_ENV", "sandbox")

    # Mealie
    MEALIE_BASE_URL = env_target("MEALIE_BASE_URL", "http://mealie.local", "http://mealie:9000")
    MEALIE_API_KEY = env_str("MEALIE_API_KEY")

    # Menu Processor
    MENU_PROCESSOR_URL = env_target(
        "MENU_PROCESSOR_URL", "http://localhost:5001", "http://menu-processor:5001"
    )

    # DNSCrypt-proxy
    DNSCRYPT_IP = env_str("DNSCRYPT_IP", "127.0.0.1")
    DNSCRYPT_PORT = env_int("DNSCRYPT_PORT", 5053)

    # DOC PATH al NAS: Ruta mounted dentro del contenedor de Flask intranet,  #definida en el docker compose
    DOCS_BASE_PATH = "/mnt/Documentos"

    # Home Assistant Energy
    HOMEASSISTANT_URL = env_target(
        "HOMEASSISTANT_URL", "http://ha.local", "http://homeassistant:8123"
    )
    HOMEASSISTANT_TOKEN = env_str("HOMEASSISTANT_TOKEN", "")

    # Timeout configuraciones para APIs externas
    API_TIMEOUT = 30  # segundos (aumentado para NAS)
    MAX_RETRIES = 3  # aumentado retries

    # =========================================================================
    # DISPOSITIVOS IoT - Home Assistant
    # =========================================================================
    # Para añadir un nuevo dispositivo:
    # 1. Buscar entity_id en HA → Configuración → Dispositivos → Entidades
    # 2. Añadir a la categoría correspondiente (ver ejemplos abajo)
    #
    # Categorías disponibles:
    #   - "power": sensores numéricos (W, kWh, °C, %)
    #   - "sensors": binarios (on/off, abierto/cerrado, detectado/ok)
    #   - "switches": interruptores controlables (futuro)
    #   - "lights": luces (futuro)
    #
    # Campos obligatorios:
    #   - entity_id: ID exacto de Home Assistant
    #   - name: nombre a mostrar en el dashboard
    #   - icon: emoji para el icono
    #
    # Campos según tipo:
    #   - Numéricos: unit (unidad: "W", "kWh", "°C", "%")
    #   - Binarios: type="binary", state_on, state_off (textos a mostrar)
    # =========================================================================
    HA_DEVICES = {
        "power": [
            {
                "entity_id": "sensor.endoll_ups_nas_router_power",
                "name": "NAS + UPS + Router",
                "icon": "⚡",
                "unit": "W",
            },
        ],
        "sensors": [
            {
                "entity_id": "binary_sensor.detector_gas_safareig_gas",
                "name": "Detector Gas",
                "icon": "🔥",
                "type": "binary",
                "state_on": "¡Gas detectado!",
                "state_off": "OK",
            },
            {
                "entity_id": "binary_sensor.sensor_puerta_arago5_contact",
                "name": "Puerta Aragó",
                "icon": "🚪",
                "type": "binary",
                "state_on": "Abierta",
                "state_off": "Cerrada",
            },
        ],
        # Futuro: añadir más categorías
        # "switches": [],
        # "lights": [],
    }


class DevelopmentConfig(Config):
    """Configuración para desarrollo"""

    DEBUG = True


class ProductionConfig(Config):
    """Configuración para producción"""

    DEBUG = False
    # En producción, SECRET_KEY debe venir de variable de entorno
    SECRET_KEY = env_str("SECRET_KEY")
    if not SECRET_KEY:
        SECRET_KEY = "dev-secret-key-change-in-production"  # Temporal para desarrollo


# Diccionario de configuraciones
config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
