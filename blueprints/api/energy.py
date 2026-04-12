"""
API Energy & Devices - Consumo eléctrico y dispositivos IoT via Home Assistant
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import requests
from flask import Blueprint, current_app, jsonify

from blueprints.energy_client import EnergyClient
from cache import cache

energy_bp = Blueprint("api_energy", __name__)


@energy_bp.route("/api/energy")
@cache.cached(timeout=300)
def api_energy():
    """Resumen de consumo eléctrico desde Home Assistant."""
    try:
        ha_url = current_app.config.get("HOMEASSISTANT_URL")
        ha_token = current_app.config.get("HOMEASSISTANT_TOKEN")

        if not ha_url:
            return jsonify({"error": "HOMEASSISTANT_URL no configurado"}), 500

        timeout = current_app.config.get("API_TIMEOUT", 15)
        energy_client = EnergyClient(ha_url, ha_token, timeout=timeout)
        data = energy_client.get_energy_summary()
        return jsonify(data)

    except Exception as e:
        current_app.logger.error(f"Error Energy API: {e}")
        return jsonify({"error": str(e)}), 500


def _fetch_device_state(ha_url, headers, device, category, timeout):
    """Fetch a single device state from HA. Runs in thread pool."""
    entity_id = device.get("entity_id")
    try:
        url = f"{ha_url.rstrip('/')}/api/states/{entity_id}"
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        data = response.json()

        state = data.get("state", "unknown")
        device_type = device.get("type", "sensor")

        if device_type == "binary":
            display_state = (
                device.get("state_on", "On")
                if state == "on"
                else device.get("state_off", "Off")
            )
            status = "warning" if state == "on" else "ok"
        else:
            try:
                value = float(state.replace(",", "."))
                unit = device.get("unit", "")
                display_state = f"{value:.1f} {unit}".strip()
                status = "ok"
            except (ValueError, AttributeError):
                display_state = state
                status = "unknown" if state in ("unknown", "unavailable") else "ok"

        return {
            "name": device.get("name", entity_id),
            "icon": device.get("icon", "\U0001f4df"),
            "state": display_state,
            "status": status,
            "category": category,
            "entity_id": entity_id,
        }

    except Exception:
        return {
            "name": device.get("name", entity_id),
            "icon": device.get("icon", "\U0001f4df"),
            "state": "Error",
            "status": "error",
            "category": category,
            "entity_id": entity_id,
        }


@energy_bp.route("/api/devices")
@cache.cached(timeout=60)
def api_devices():
    """Estados de dispositivos IoT desde Home Assistant (parallelized)."""
    try:
        ha_url = current_app.config.get("HOMEASSISTANT_URL")
        ha_token = current_app.config.get("HOMEASSISTANT_TOKEN")
        ha_devices = current_app.config.get("HA_DEVICES", {})
        timeout = current_app.config.get("API_TIMEOUT", 15)

        if not ha_url or not ha_token:
            return jsonify({"error": "HOMEASSISTANT_URL o TOKEN no configurado"}), 500

        headers = {
            "Authorization": f"Bearer {ha_token}",
            "Content-Type": "application/json",
        }

        # Flatten device list with categories
        all_devices = [
            (device, category)
            for category, device_list in ha_devices.items()
            for device in device_list
        ]

        devices = []
        with ThreadPoolExecutor(max_workers=min(len(all_devices), 8)) as executor:
            futures = {
                executor.submit(
                    _fetch_device_state, ha_url, headers, device, category, timeout
                ): i
                for i, (device, category) in enumerate(all_devices)
            }
            # Collect results preserving original order
            results = [None] * len(all_devices)
            for future in as_completed(futures):
                idx = futures[future]
                results[idx] = future.result()
            devices = [r for r in results if r is not None]

        return jsonify({
            "devices": devices,
            "total": len(devices),
            "timestamp": datetime.now().isoformat(),
        })

    except Exception as e:
        current_app.logger.error(f"Error Devices API: {e}")
        return jsonify({"error": str(e)}), 500
