"""
Cliente para consumir datos de consumo eléctrico desde Home Assistant
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import requests

logger = logging.getLogger(__name__)


class EnergyClient:
    """Cliente para obtener datos de consumo eléctrico de Home Assistant"""

    def __init__(self, base_url, api_token=None, timeout=15):
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.timeout = timeout  # Resolved outside threads — current_app not available inside ThreadPoolExecutor
        self.headers = (
            {"Authorization": f"Bearer {self.api_token}", "Content-Type": "application/json"}
            if self.api_token
            else {}
        )

    @staticmethod
    def _to_float_state(state_value, entity_id):
        """Convert HA sensor state to float, handling common non-numeric states."""
        if state_value is None:
            raise ValueError(f"Estado vacío en {entity_id}")

        state_text = str(state_value).strip().lower()
        if state_text in {"unknown", "unavailable", "none", ""}:
            raise ValueError(f"Estado no numérico en {entity_id}: {state_value}")

        # HA a veces devuelve coma decimal según locale
        normalized = str(state_value).strip().replace(",", ".")
        return float(normalized)

    def get_monthly_consumption(self):
        """
        Obtiene consumo total del mes actual en kWh
        """
        try:
            # Entity ID del sensor de consumo mensual (ya calculado por HA)
            entity_id = "sensor.endoll_ups_nas_router_energy_month"  # Consumo mensual calculado

            url = f"{self.base_url}/api/states/{entity_id}"

            response = requests.get(
                url, headers=self.headers, timeout=self.timeout
            )
            response.raise_for_status()

            data = response.json()
            consumption = self._to_float_state(data.get("state"), entity_id)

            return {
                "consumption_kwh": round(consumption, 2),
                "period": "mes actual",
                "last_updated": data.get("last_updated", datetime.now().isoformat()),
                "unit": "kWh",
            }

        except Exception as e:
            logger.error(f"Error obteniendo consumo mensual: {e}")
            return {"consumption_kwh": None, "period": "mes actual", "error": str(e)}

    def get_monthly_cost(self):
        """
        Obtiene coste acumulado del mes actual en €
        Usa el sensor nas_router_ups_coste_mes que ya calcula el coste mensual correctamente en HA
        """
        try:
            # Entity ID del nuevo sensor de coste mensual (template + utility_meter)
            entity_id = "sensor.nas_router_ups_coste_mes"  # Coste mensual calculado por HA

            url = f"{self.base_url}/api/states/{entity_id}"

            response = requests.get(
                url, headers=self.headers, timeout=self.timeout
            )
            response.raise_for_status()

            data = response.json()
            cost = self._to_float_state(data.get("state"), entity_id)

            # El sensor ya es el coste mensual correcto, sin necesidad de cálculos adicionales
            return {
                "cost_eur": round(cost, 2),
                "period": "mes actual",
                "last_updated": data.get("last_updated", datetime.now().isoformat()),
                "unit": "€",
            }

        except Exception as e:
            logger.error(f"Error obteniendo coste mensual: {e}")
            return {"cost_eur": None, "period": "mes actual", "error": str(e)}

    def get_current_power(self):
        """
        Obtiene consumo instantáneo actual en W
        """
        try:
            entity_id = "sensor.endoll_ups_nas_router_power"  # Potencia actual

            url = f"{self.base_url}/api/states/{entity_id}"

            response = requests.get(
                url, headers=self.headers, timeout=self.timeout
            )
            response.raise_for_status()

            data = response.json()
            power = self._to_float_state(data.get("state"), entity_id)

            return {
                "power_w": round(power, 2),
                "last_updated": data.get("last_updated", datetime.now().isoformat()),
                "unit": "W",
            }

        except Exception as e:
            logger.error(f"Error obteniendo potencia actual: {e}")
            return {"power_w": None, "error": str(e)}

    def get_energy_summary(self):
        """
        Obtiene resumen completo de energía.
        Ejecuta las 3 llamadas a HA en paralelo para reducir latencia.
        """
        results = {}
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(self.get_monthly_consumption): "consumption",
                executor.submit(self.get_monthly_cost): "cost",
                executor.submit(self.get_current_power): "current_power",
            }
            for future in as_completed(futures):
                key = futures[future]
                try:
                    results[key] = future.result()
                except Exception as e:
                    logger.error(f"Error en {key}: {e}")
                    results[key] = {"error": str(e)}

        results["dashboard_url"] = f"{self.base_url}/energy/electricity"
        results["last_updated"] = datetime.now().isoformat()
        return results
