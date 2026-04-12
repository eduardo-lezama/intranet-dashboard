"""
Aplicación principal Flask - Intranet Casa
"""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, render_template

from cache import cache


def _load_environment_file():
    """Carga el archivo .env"""
    env_path = Path(__file__).resolve().parent / ".env"

    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=False)
    else:
        # Fallback para mantener compatibilidad con entornos que inyectan vars
        load_dotenv(override=False)


_load_environment_file()

from config import config


def create_app(config_name="default"):
    """
    Factory function para crear la aplicación Flask

    Args:
        config_name: Nombre de la configuración a usar

    Returns:
        Flask app configurada
    """
    app = Flask(__name__)

    # Cargar configuración
    app.config.from_object(config[config_name])

    # init cache
    cache.init_app(app)

    # Reducir logging en producción (solo WARNING y superiores)
    if not app.debug:
        app.logger.setLevel(logging.WARNING)
        # También reducir logging de werkzeug
        logging.getLogger("werkzeug").setLevel(logging.WARNING)

    # Registrar blueprints
    from blueprints import register_blueprints

    register_blueprints(app)

    # Contexto de plantillas global
    @app.context_processor
    def inject_globals():
        """Inyectar variables globales en todas las plantillas"""
        return {
            "app_name": "Intranet Casa",
            "user_name": app.config["USERS"]["default"]["name"],
            "services": app.config["SERVICES"],
        }

    # Manejador de errores 404
    @app.errorhandler(404)
    def not_found(error):
        return render_template("errors/404.html"), 404

    # Manejador de errores 500
    @app.errorhandler(500)
    def internal_error(error):
        return render_template("errors/500.html"), 500

    return app


# Crear instancia de la app según entorno
env_name = os.environ.get("FLASK_ENV", "development").lower()
config_name = "production" if env_name == "production" else "development"
app = create_app(config_name)


if __name__ == "__main__":
    # Configuración para desarrollo
    app.run(host="0.0.0.0", port=5000, debug=True)
