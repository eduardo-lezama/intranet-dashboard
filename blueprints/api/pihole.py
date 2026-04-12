"""
API Pi-hole - Estadísticas de bloqueo DNS via Pi-hole v6
"""

from datetime import datetime

from flask import Blueprint, current_app, jsonify

from blueprints.pihole_auth import PiHoleV6Client
from cache import cache

pihole_bp = Blueprint("api_pihole", __name__)

# Cliente Pi-hole (mantiene SID entre requests dentro del mismo worker)
_pihole_client = None


def _get_pihole_client():
    """Obtener o crear cliente Pi-hole."""
    global _pihole_client

    pihole_url = current_app.config.get("PIHOLE_URL", "")
    pihole_password = current_app.config.get("PIHOLE_PASSWORD", "")

    if not pihole_url or not pihole_password:
        return None

    if _pihole_client is None:
        current_app.logger.info("Inicializando cliente Pi-hole v6...")
        _pihole_client = PiHoleV6Client(pihole_url, pihole_password)

    return _pihole_client


@pihole_bp.route("/api/pihole")
@cache.cached(timeout=300)
def api_pihole():
    """Estadísticas reales de Pi-hole v6 con autenticación SID."""
    global _pihole_client

    pihole_url = current_app.config.get("PIHOLE_URL", "")
    pihole_password = current_app.config.get("PIHOLE_PASSWORD", "")

    if not pihole_url or not pihole_password:
        return jsonify({
            "error": "PIHOLE_URL o PIHOLE_PASSWORD no configurado",
            "solution": "Añadir a .env",
        }), 500

    try:
        client = _get_pihole_client()
        if client is None:
            return jsonify({"error": "No se pudo inicializar cliente Pi-hole"}), 500

        data = client.get_stats()
        if not data:
            return jsonify({
                "error": "No se pudieron obtener datos de Pi-hole",
                "message": "Verifica IP y password",
            }), 503

        queries = data.get("queries", {})
        gravity = data.get("gravity", {})

        return jsonify({
            "ads_blocked_today": queries.get("blocked", 0),
            "ads_percentage_today": round(queries.get("percent_blocked", 0), 1),
            "dns_queries_today": queries.get("total", 0),
            "domains_blocked": gravity.get("domains_being_blocked", 0),
            "clients_unique": data.get("unique_clients", 0),
            "status": "enabled",
            "timestamp": datetime.now().isoformat(),
            "pihole_url": pihole_url,
            "raw_data": data,
        })

    except Exception as e:
        current_app.logger.error(f"Error Pi-hole: {e}")
        _pihole_client = None
        return jsonify({"error": str(e), "retrying": True}), 500
