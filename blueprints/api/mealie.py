"""
API Mealie - Recetas y planificación de comidas
"""

from flask import Blueprint, current_app, jsonify

from blueprints.mealie_client import MealieClient
from cache import cache

mealie_bp = Blueprint("api_mealie", __name__)


@mealie_bp.route("/api/mealie")
@cache.cached(timeout=600)
def api_mealie():
    """Resumen de recetas y plan de comidas de hoy."""
    base_url = current_app.config.get("MEALIE_BASE_URL")
    api_key = current_app.config.get("MEALIE_API_KEY")
    timeout = current_app.config.get("API_TIMEOUT", 15)

    if not base_url or not api_key:
        return jsonify({"error": "MEALIE_BASE_URL o MEALIE_API_KEY no configurados"}), 500

    try:
        client = MealieClient(base_url, api_key, timeout=timeout)
        total_recipes = client.get_recipes_count()
        meals_today = client.get_today_meals()

        grouped = {}
        for meal in meals_today:
            t = (meal["type"] or "meal").lower()
            grouped.setdefault(t, []).append(meal["title"])

        return jsonify({
            "total_recipes": total_recipes,
            "meals_today": grouped,
        })

    except Exception as e:
        current_app.logger.error(f"Error Mealie: {e}")
        return jsonify({"error": str(e)}), 500


@mealie_bp.route("/api/mealie/debug")
def api_mealie_debug():
    """Debug endpoint para Mealie API."""
    import requests as req

    base_url = current_app.config.get("MEALIE_BASE_URL")
    api_key = current_app.config.get("MEALIE_API_KEY")

    if not base_url or not api_key:
        return jsonify({"error": "Config missing"}), 500

    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}

    r1 = req.get(
        f"{base_url}/api/recipes", headers=headers, params={"perPage": 1, "page": 1}
    )
    r2 = req.get(f"{base_url}/api/households/mealplans/today", headers=headers)

    return jsonify({
        "recipes_response": r1.json() if r1.ok else {"error": r1.text},
        "today_response": r2.json() if r2.ok else {"error": r2.text},
    })
