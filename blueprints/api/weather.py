"""
API Weather - Datos meteorológicos via OpenWeatherMap
"""

from concurrent.futures import ThreadPoolExecutor

import requests
from flask import Blueprint, current_app, jsonify

from cache import cache

weather_bp = Blueprint("api_weather", __name__)


@weather_bp.route("/api/weather")
@cache.cached(timeout=600)
def api_weather():
    """
    Proxy para OpenWeatherMap API.
    Hace las llamadas server-side para no exponer la API key en el frontend.
    Ejecuta current + forecast en paralelo.
    """
    api_key = current_app.config.get("OPENWEATHER_API_KEY", "")
    city = current_app.config.get("WEATHER_CITY", "Manresa")
    country = current_app.config.get("WEATHER_COUNTRY", "ES")
    timeout = current_app.config.get("API_TIMEOUT", 15)

    if not api_key:
        return jsonify({"error": "OPENWEATHER_API_KEY no configurado"}), 500

    base_params = f"q={city},{country}&appid={api_key}&units=metric&lang=es"
    current_url = f"https://api.openweathermap.org/data/2.5/weather?{base_params}"
    forecast_url = f"https://api.openweathermap.org/data/2.5/forecast?{base_params}"

    def fetch(url):
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.json()

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            current_future = executor.submit(fetch, current_url)
            forecast_future = executor.submit(fetch, forecast_url)

        return jsonify({
            "current": current_future.result(),
            "forecast": forecast_future.result(),
        })

    except requests.RequestException as e:
        current_app.logger.error(f"Error Weather API: {e}")
        return jsonify({"error": str(e)}), 500
