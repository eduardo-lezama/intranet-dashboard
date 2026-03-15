# app/services/mealie_client.py

import requests


class MealieClient:
    def __init__(self, base_url, api_key, timeout=10):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

    def get_recipes_count(self):
        url = f"{self.base_url}/api/recipes"
        resp = self.session.get(url, params={"perPage": 1, "page": 1}, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()

        # Intentar varias estructuras de respuesta de Mealie v3
        # Opción 1: meta.pagination.total (doc oficial)
        meta = data.get("meta", {})
        pagination = meta.get("pagination", {})
        if "total" in pagination:
            return pagination["total"]

        # Opción 2: total en raíz (algunas instancias)
        if "total" in data:
            return data["total"]

        # Opción 3: contar items (fallback)
        items = data.get("items", []) or data.get("data", [])
        return len(items)

    def get_today_meals(self):
        url = f"{self.base_url}/api/households/mealplans/today"
        try:
            resp = self.session.get(url, timeout=self.timeout)
            resp.raise_for_status()
        except requests.RequestException as e:
            # Si falla, devolver lista vacía en vez de romper
            print(f"Error fetching today meals: {e}")
            return []

        data = resp.json()
        meals_today = []

        # data puede ser lista o dict con "items"
        entries = data if isinstance(data, list) else data.get("items", [])

        for entry in entries:
            # Campos posibles según versión de Mealie
            entry_type = (
                entry.get("entryType")  # v3.x estándar
                or entry.get("entry_type")  # snake_case
                or entry.get("mealType")  # algunas instancias
                or "meal"
            )

            # Receta puede venir como objeto o como slug/id
            recipe_obj = entry.get("recipe")
            if isinstance(recipe_obj, dict):
                title = recipe_obj.get("name") or recipe_obj.get("slug") or "Sin título"
            elif isinstance(recipe_obj, str):
                # Es solo el ID/slug, intenta usar el nombre de la entry
                title = entry.get("title") or entry.get("recipeName") or recipe_obj
            else:
                title = entry.get("title") or entry.get("name") or "Sin título"

            meals_today.append(
                {
                    "type": str(entry_type).lower(),
                    "title": title,
                }
            )

        return meals_today
