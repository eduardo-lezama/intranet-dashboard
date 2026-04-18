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
        Obtiene consumo total del mes actual en kWh (NAS + Workstation)
        """
        try:
            # Entity IDs de ambos sensores de consumo mensual
            entities = [
                "sensor.endoll_ups_nas_router_energy_month",
                "sensor.endoll_workstation_edu_energy_month",
            ]

            total_consumption = 0.0
            last_updated = None
            successful_reads = 0

            for entity_id in entities:
                try:
                    url = f"{self.base_url}/api/states/{entity_id}"
                    response = requests.get(url, headers=self.headers, timeout=self.timeout)
                    response.raise_for_status()

                    data = response.json()
                    consumption = self._to_float_state(data.get("state"), entity_id)
                    total_consumption += consumption
                    successful_reads += 1

                    # Guardar el último timestamp más reciente
                    if last_updated is None:
                        last_updated = data.get("last_updated")

                except Exception as e:
                    logger.warning(f"Error leyendo {entity_id}: {e}")
                    # Continuar con el siguiente sensor

            if successful_reads == 0:
                raise ValueError("No se pudo leer ningún sensor de consumo mensual")

            return {
                "consumption_kwh": round(total_consumption, 2),
                "period": "mes actual",
                "last_updated": last_updated or datetime.now().isoformat(),
                "unit": "kWh",
                "devices_read": successful_reads,
            }

        except Exception as e:
            logger.error(f"Error obteniendo consumo mensual: {e}")
            return {"consumption_kwh": None, "period": "mes actual", "error": str(e)}

    def get_monthly_cost(self):
        """
        Obtiene coste acumulado del mes actual en € (NAS + Workstation)
        Usa los sensores de coste mensual calculados por HA (template + utility_meter)
        """
        try:
            # Entity IDs de ambos sensores de coste mensual
            entities = [
                "sensor.nas_router_ups_coste_mes",
                "sensor.workstation_edu_coste_mes",
            ]

            total_cost = 0.0
            last_updated = None
            successful_reads = 0

            for entity_id in entities:
                try:
                    url = f"{self.base_url}/api/states/{entity_id}"
                    response = requests.get(url, headers=self.headers, timeout=self.timeout)
                    response.raise_for_status()

                    data = response.json()
                    cost = self._to_float_state(data.get("state"), entity_id)
                    total_cost += cost
                    successful_reads += 1

                    # Guardar el último timestamp más reciente
                    if last_updated is None:
                        last_updated = data.get("last_updated")

                except Exception as e:
                    logger.warning(f"Error leyendo {entity_id}: {e}")
                    # Continuar con el siguiente sensor

            if successful_reads == 0:
                raise ValueError("No se pudo leer ningún sensor de coste mensual")

            return {
                "cost_eur": round(total_cost, 2),
                "period": "mes actual",
                "last_updated": last_updated or datetime.now().isoformat(),
                "unit": "€",
                "devices_read": successful_reads,
            }

        except Exception as e:
            logger.error(f"Error obteniendo coste mensual: {e}")
            return {"cost_eur": None, "period": "mes actual", "error": str(e)}

    def get_current_power(self):
        """
        Obtiene consumo instantáneo actual en W (NAS + Workstation)
        """
        try:
            # Entity IDs de ambos sensores de potencia instantánea
            entities = [
                "sensor.endoll_ups_nas_router_power",
                "sensor.endoll_workstation_edu_power",
            ]

            total_power = 0.0
            last_updated = None
            successful_reads = 0

            for entity_id in entities:
                try:
                    url = f"{self.base_url}/api/states/{entity_id}"
                    response = requests.get(url, headers=self.headers, timeout=self.timeout)
                    response.raise_for_status()

                    data = response.json()
                    power = self._to_float_state(data.get("state"), entity_id)
                    total_power += power
                    successful_reads += 1

                    # Guardar el último timestamp más reciente
                    if last_updated is None:
                        last_updated = data.get("last_updated")

                except Exception as e:
                    logger.warning(f"Error leyendo {entity_id}: {e}")
                    # Continuar con el siguiente sensor

            if successful_reads == 0:
                raise ValueError("No se pudo leer ningún sensor de potencia")

            return {
                "power_w": round(total_power, 2),
                "last_updated": last_updated or datetime.now().isoformat(),
                "unit": "W",
                "devices_read": successful_reads,
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
