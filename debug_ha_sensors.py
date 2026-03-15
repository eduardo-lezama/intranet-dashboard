import os

import requests

# Leer token del .env actual con override forzado
from dotenv import load_dotenv

load_dotenv(override=True)

# Leer token del entorno
token = os.environ.get("HOMEASSISTANT_TOKEN")
if not token:
    print("❌ ERROR: HOMEASSISTANT_TOKEN no encontrado en .env")
    exit(1)

print(f"🔑 Token (primeros 20 chars): {token[:20]}...")
print(f"🔑 Token (últimos 10 chars): ...{token[-10:]}")
headers = {"Authorization": f"Bearer {token}"}

# Determinar URL según entorno
env_target = os.environ.get("ENV_TARGET", "local")
if env_target == "nas":
    base_url = os.environ.get("HOMEASSISTANT_URL_NAS", "http://homeassistant:8123")
else:
    base_url = os.environ.get("HOMEASSISTANT_URL_LOCAL", "http://ha.local")

# Sensores a testear
sensors = [
    ("Energía TOTAL acumulada", "sensor.endoll_ups_nas_router_energy"),
    ("Consumo Mensual", "sensor.endoll_ups_nas_router_energy_month"),
    ("Coste Energía (antiguo)", "sensor.endoll_ups_nas_router_energy_cost"),
    ("Coste Total (template)", "sensor.nas_router_ups_coste_total"),
    ("Coste Mensual (utility)", "sensor.nas_router_ups_coste_mes"),
    ("Precio Electricidad", "input_number.precio_electricidad_fijo"),
    ("Potencia Actual", "sensor.endoll_ups_nas_router_power"),
]

print("🔍 Test de sensores Home Assistant")
print("=" * 50)

for name, entity_id in sensors:
    print(f"\n📊 {name}: {entity_id}")

    try:
        response = requests.get(f"{base_url}/api/states/{entity_id}", headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            state = data.get("state", "N/A")
            unit = data["attributes"].get("unit_of_measurement", "N/A")
            friendly = data["attributes"].get("friendly_name", "N/A")
            last_updated = data.get("last_updated", "N/A")

            print(f"  ✅ State: {state} {unit}")
            print(f"  📝 Friendly: {friendly}")
            print(f"  ⏰ Updated: {last_updated}")

            # Debug extra para sensor de coste
            if entity_id == "sensor.endoll_ups_nas_router_energy_cost":
                print("  🔍 Atributos completos:")
                for k, v in data.get("attributes", {}).items():
                    print(f"    - {k}: {v}")

        else:
            print(f"  ❌ Error {response.status_code}: {response.text[:100]}")

    except Exception as e:
        print(f"  ❌ Exception: {e}")

print("\n" + "=" * 50)
print("🎯 Análisis de resultados:")
print("• Consumo mensual: Debe estar en kWh")
print("• Coste energía: Puede ser € total o €/kWh")
print("• Potencia actual: Debe estar en W")
