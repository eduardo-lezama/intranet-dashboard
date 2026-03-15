"""
Cliente Pi-hole v6 API - Autenticación SID automática
"""

import logging
from datetime import datetime, timedelta

import requests

logger = logging.getLogger(__name__)


class PiHoleV6Client:
    def __init__(self, base_url, password):
        # Normalizar URL: quitar trailing slash
        self.base_url = base_url.rstrip("/")
        self.password = password
        self.sid = None
        self.csrf = None
        self.expires = None

    def authenticate(self):
        """Obtener SID válido (30min)"""
        try:
            url = f"{self.base_url}/api/auth"
            payload = {"password": self.password}

            response = requests.post(url, json=payload, timeout=5, verify=False)
            response.raise_for_status()

            data = response.json()

            if not data.get("session", {}).get("valid"):
                logger.error("Autenticación fallida")
                return False

            session = data["session"]
            self.sid = session["sid"]
            self.csrf = session["csrf"]
            self.expires = datetime.now() + timedelta(
                seconds=session["validity"] - 60
            )  # Renovar 1min antes

            logger.info(f"SID obtenido, válido hasta {self.expires}")
            return True

        except Exception as e:
            logger.error(f"Error autenticando: {e}")
            return False

    def is_valid(self):
        return self.sid and datetime.now() < self.expires

    def get_headers(self):
        if not self.is_valid():
            self.authenticate()

        return {"X-FTL-SID": self.sid, "X-FTL-CSRF": self.csrf, "Content-Type": "application/json"}

    def get_stats(self):
        """Obtener estadísticas principales"""
        headers = self.get_headers()
        url = f"{self.base_url}/api/stats/summary"

        try:
            response = requests.get(url, headers=headers, timeout=5, verify=False)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error stats: {e}")
            return None
