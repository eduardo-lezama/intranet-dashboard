"""
API Services - Health checks y status de servicios auxiliares
"""

import socket
from datetime import datetime

import requests
from flask import Blueprint, current_app, jsonify

from cache import cache

services_bp = Blueprint("api_services", __name__)


@services_bp.route("/api/status")
def api_status():
    """Status general de la aplicación."""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "services": current_app.config.get("SERVICES", {}),
    })


@services_bp.route("/api/health")
def api_health():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
    })


@services_bp.route("/api/menu-processor")
@cache.cached(timeout=5)
def api_menu_processor():
    """Health check del servicio Menu Processor."""
    menu_url = current_app.config.get("MENU_PROCESSOR_URL")
    if not menu_url:
        return jsonify({"error": "Menu Processor no configurado"}), 500

    try:
        response = requests.get(f"{menu_url}/api/health", timeout=5)
        if response.ok:
            return jsonify({"status": "up", "service": "menu-processor"})
        return jsonify({
            "status": "down",
            "service": "menu-processor",
            "error": f"HTTP {response.status_code}",
        }), 503
    except requests.RequestException as e:
        current_app.logger.error(f"Menu Processor health check failed: {e}")
        return jsonify({"status": "down", "service": "menu-processor", "error": str(e)}), 503


@services_bp.route("/api/dnscrypt")
@cache.cached(timeout=60)
def api_dnscrypt():
    """Health check de DNSCrypt-proxy via consulta DNS."""
    dnscrypt_ip = current_app.config.get("DNSCRYPT_IP", "127.0.0.1")
    dnscrypt_port = current_app.config.get("DNSCRYPT_PORT", 5053)

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(3)
        query = (
            b"\x00\x01\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00"
            b"\x06google\x03com\x00\x00\x01\x00\x01"
        )
        sock.sendto(query, (dnscrypt_ip, dnscrypt_port))
        data, _ = sock.recvfrom(512)
        sock.close()

        if data and len(data) > 12:
            return jsonify({"status": "ok", "service": "dnscrypt-proxy"})
        return jsonify({"error": "Respuesta DNS inválida"}), 500

    except TimeoutError:
        current_app.logger.error("DNSCrypt health check timeout")
        return jsonify({"error": "Timeout"}), 500
    except Exception as e:
        current_app.logger.error(f"DNSCrypt health check failed: {e}")
        return jsonify({"error": str(e)}), 500
