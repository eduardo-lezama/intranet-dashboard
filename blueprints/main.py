import csv
import os
from datetime import datetime
from pathlib import Path

from flask import Blueprint, abort, current_app, jsonify, render_template, request, send_file

from blueprints.energy_client import EnergyClient
from blueprints.mealie_client import MealieClient
from blueprints.pihole_auth import PiHoleV6Client
from blueprints.settleup_client import SettleUpClient
from cache import cache

main_bp = Blueprint("main", __name__)

# Cliente Pi-hole global (mantiene SID entre requests)
pihole_client = None


@main_bp.route("/")
def index():
    context = {"current_time": datetime.now(), "page_title": "Dashboard"}
    return render_template("dashboard.html", **context)


@main_bp.route("/finanzas")
def finanzas():
    context = {"page_title": "Finanzas", "balance": 0.0, "gastos_mes": 0.0, "ahorros": 0.0}
    return render_template("finanzas.html", **context)


@main_bp.route("/api/status")
def api_status():
    return jsonify(
        {
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "services": current_app.config.get("SERVICES", {}),
        }
    )


@main_bp.route("/api/weather")
@cache.cached(timeout=600)  # 10 minutos (clima cambia lento)
def api_weather():
    # Tu código de clima aquí (si ya lo tienes)
    return jsonify({"temp": 15, "description": "Parcialmente nublado", "humidity": 65})


@main_bp.route("/api/pihole")
@cache.cached(timeout=300)  # 5 minutos (stats no cambian rápido)
def api_pihole():
    """
    Endpoint Pi-hole v6 - Estadísticas reales con autenticación SID
    """
    global pihole_client

    pihole_url = current_app.config.get("PIHOLE_URL", "")
    pihole_password = current_app.config.get("PIHOLE_PASSWORD", "")

    if not pihole_url or not pihole_password:
        return jsonify(
            {"error": "PIHOLE_URL o PIHOLE_PASSWORD no configurado", "solution": "Añadir a .env"}
        ), 500

    try:
        # Inicializar cliente si no existe
        if pihole_client is None:
            current_app.logger.info("Inicializando cliente Pi-hole v6...")
            pihole_client = PiHoleV6Client(pihole_url, pihole_password)

        # Obtener datos
        data = pihole_client.get_stats()

        if not data:
            return jsonify(
                {
                    "error": "No se pudieron obtener datos de Pi-hole",
                    "message": "Verifica IP y password",
                }
            ), 503

        # 🔥 MAPEO PARA DASHBOARD: Formato específico para frontend
        queries = data.get("queries", {})
        gravity = data.get("gravity", {})

        result = {
            "ads_blocked_today": queries.get("blocked", 0),
            "ads_percentage_today": round(queries.get("percent_blocked", 0), 1),
            "dns_queries_today": queries.get("total", 0),
            "domains_blocked": gravity.get("domains_being_blocked", 0),
            "clients_unique": data.get("unique_clients", 0),
            "status": "enabled",
            "timestamp": datetime.now().isoformat(),
            "pihole_url": pihole_url,
            "raw_data": data,  # Para debugging
        }

        current_app.logger.info(
            f"Pi-hole stats: {result['ads_blocked_today']} ads bloqueados ({result['ads_percentage_today']}%)"
        )
        return jsonify(result)

    except Exception as e:
        current_app.logger.error(f"Error Pi-hole: {str(e)}")
        pihole_client = None  # Resetear para reintentar
        return jsonify({"error": str(e), "retrying": True}), 500


@main_bp.route("/api/shopping", methods=["GET", "POST", "DELETE"])
def api_shopping():
    shopping_file = os.path.join("data", "shopping.csv")
    os.makedirs(os.path.dirname(shopping_file), exist_ok=True)

    if request.method == "GET":
        # Leer lista
        items = []
        try:
            with open(shopping_file, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                items = list(reader)
        except FileNotFoundError:
            pass
        return jsonify(items)

    elif request.method == "POST":
        # Añadir item
        item = {"text": request.json.get("text", ""), "added": datetime.now().isoformat()}
        with open(shopping_file, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["text", "added"])
            if f.tell() == 0:
                writer.writeheader()
            writer.writerow(item)
        return jsonify(item), 201

    elif request.method == "DELETE":
        # Eliminar item por índice
        index = int(request.json.get("index", 0))
        items = []
        try:
            with open(shopping_file, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                items = list(reader)

            if 0 <= index < len(items):
                del items[index]

                # Reescribir archivo
                with open(shopping_file, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=["text", "added"])
                    writer.writeheader()
                    writer.writerows(items)
                return jsonify({"success": True})
        except Exception as e:
            current_app.logger.error(f"Error eliminando item de shopping: {e}")
        return jsonify({"success": False}), 400


@main_bp.route("/api/settleup")
@cache.cached(timeout=900)  # 15 minutos en lugar de 10
def api_settleup():
    """
    Endpoint Settle Up - visión general del grupo
    """
    email = current_app.config.get("SETTLEUP_EMAIL")
    password = current_app.config.get("SETTLEUP_PASSWORD")
    group_id = current_app.config.get("SETTLEUP_GROUP_ID")
    api_key = current_app.config.get("SETTLEUP_API_KEY")
    env = current_app.config.get("SETTLEUP_ENV", "sandbox")

    if not all([email, password, group_id, api_key]):
        return jsonify(
            {
                "error": "Configuración incompleta",
                "required": [
                    "SETTLEUP_EMAIL",
                    "SETTLEUP_PASSWORD",
                    "SETTLEUP_GROUP_ID",
                    "SETTLEUP_API_KEY",
                ],
            }
        ), 500

    try:
        client = SettleUpClient(
            email=email, password=password, group_id=group_id, api_key=api_key, env=env
        )

        balance_data = client.calculate_group_balance()
        members = balance_data["members"]
        balances = balance_data["balances"]

        # Gastos del mes actual
        monthly_expenses = client.get_monthly_expenses()

        # Encontrar deudor principal y acreedor principal
        sorted_members = sorted(balances.items(), key=lambda x: x[1])
        debtor_id, debtor_balance = sorted_members[0]  # más negativo
        creditor_id, creditor_balance = sorted_members[-1]  # más positivo

        if abs(debtor_balance) < 0.01 and abs(creditor_balance) < 0.01:
            status = "Todo equilibrado ✅"
            main_amount = 0.0
            debtor_name = creditor_name = None
        else:
            main_amount = min(abs(debtor_balance), abs(creditor_balance))
            debtor_name = members[debtor_id]
            creditor_name = members[creditor_id]
            status = f"{debtor_name} debe €{main_amount:.2f} a {creditor_name}"

        return jsonify(
            {
                "status": status,
                "monthly_expenses": monthly_expenses,
                "main_debt_amount": round(main_amount, 2),
                "debtor": debtor_name,
                "creditor": creditor_name,
                "balances": {members[mid]: round(bal, 2) for mid, bal in balances.items()},
            }
        )

    except Exception as e:
        current_app.logger.error(f"Error Settle Up: {str(e)}")
        return jsonify({"error": str(e)}), 500


# Route for debugging settleup differnt ways of payment
@main_bp.route("/api/settleup/debug-transactions")
def api_settleup_debug_transactions():
    email = current_app.config.get("SETTLEUP_EMAIL")
    password = current_app.config.get("SETTLEUP_PASSWORD")
    group_id = current_app.config.get("SETTLEUP_GROUP_ID")
    api_key = current_app.config.get("SETTLEUP_API_KEY")
    env = current_app.config.get("SETTLEUP_ENV")

    client = SettleUpClient(email, password, group_id, api_key, env)
    txs = client.get_group_entries()  # o get_group_transactions
    return jsonify(txs)


@main_bp.route("/api/mealie")
@cache.cached(timeout=600)  # 10 minutos (recetas no cambian frecuentemente)
def api_mealie():
    base_url = current_app.config.get("MEALIE_BASE_URL")
    api_key = current_app.config.get("MEALIE_API_KEY")
    timeout = current_app.config.get("API_TIMEOUT", 15)

    if not base_url or not api_key:
        return jsonify({"error": "MEALIE_BASE_URL o MEALIE_API_KEY no configurados"}), 500

    try:
        client = MealieClient(base_url, api_key, timeout=timeout)
        total_recipes = client.get_recipes_count()
        meals_today = client.get_today_meals()

        # Agrupar por tipo para mostrar bonito
        grouped = {}
        for meal in meals_today:
            t = (meal["type"] or "meal").lower()
            grouped.setdefault(t, []).append(meal["title"])

        return jsonify(
            {
                "total_recipes": total_recipes,
                "meals_today": grouped,  # {"dinner": [...], "lunch": [...], ...}
            }
        )
    except Exception as e:
        current_app.logger.error(f"Error Mealie: {e}")
        return jsonify({"error": str(e)}), 500


@main_bp.route("/api/health")
def api_health():
    """Health check endpoint"""
    return jsonify(
        {"status": "healthy", "timestamp": datetime.now().isoformat(), "version": "1.0.0"}
    )


@main_bp.route("/api/energy")
@cache.cached(timeout=300)  # 5 minutos (consumo actualiza cada poco)
def api_energy():
    """API endpoint para obtener datos de consumo eléctrico"""
    try:
        ha_url = current_app.config.get("HOMEASSISTANT_URL")
        ha_token = current_app.config.get("HOMEASSISTANT_TOKEN")

        if not ha_url:
            return jsonify({"error": "HOMEASSISTANT_URL no configurado"}), 500

        energy_client = EnergyClient(ha_url, ha_token)
        data = energy_client.get_energy_summary()

        return jsonify(data)

    except Exception as e:
        current_app.logger.error(f"Error Energy API: {str(e)}")
        return jsonify({"error": str(e)}), 500


@main_bp.route("/api/devices")
@cache.cached(timeout=60)  # 1 minuto (estados cambian frecuentemente)
def api_devices():
    """API endpoint para obtener estados de dispositivos IoT desde Home Assistant"""
    import requests

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

        devices = []

        # Procesar todas las categorías de dispositivos
        for category, device_list in ha_devices.items():
            for device in device_list:
                entity_id = device.get("entity_id")
                try:
                    url = f"{ha_url.rstrip('/')}/api/states/{entity_id}"
                    response = requests.get(url, headers=headers, timeout=timeout)
                    response.raise_for_status()
                    data = response.json()

                    state = data.get("state", "unknown")
                    device_type = device.get("type", "sensor")

                    # Formatear estado según tipo
                    if device_type == "binary":
                        display_state = (
                            device.get("state_on", "On")
                            if state == "on"
                            else device.get("state_off", "Off")
                        )
                        status = "warning" if state == "on" else "ok"
                    else:
                        # Sensor numérico
                        try:
                            value = float(state.replace(",", "."))
                            unit = device.get("unit", "")
                            display_state = f"{value:.1f} {unit}".strip()
                            status = "ok"
                        except (ValueError, AttributeError):
                            display_state = state
                            status = "unknown" if state in ("unknown", "unavailable") else "ok"

                    devices.append({
                        "name": device.get("name", entity_id),
                        "icon": device.get("icon", "📟"),
                        "state": display_state,
                        "status": status,
                        "category": category,
                        "entity_id": entity_id,
                    })

                except Exception as e:
                    current_app.logger.warning(f"Error obteniendo {entity_id}: {e}")
                    devices.append({
                        "name": device.get("name", entity_id),
                        "icon": device.get("icon", "📟"),
                        "state": "Error",
                        "status": "error",
                        "category": category,
                        "entity_id": entity_id,
                    })

        return jsonify({
            "devices": devices,
            "total": len(devices),
            "timestamp": datetime.now().isoformat(),
        })

    except Exception as e:
        current_app.logger.error(f"Error Devices API: {str(e)}")
        return jsonify({"error": str(e)}), 500


"""
DEBUG para mealie
"""


@main_bp.route("/api/mealie/debug")
def api_mealie_debug():
    base_url = current_app.config.get("MEALIE_BASE_URL")
    api_key = current_app.config.get("MEALIE_API_KEY")

    if not base_url or not api_key:
        return jsonify({"error": "Config missing"}), 500

    import requests

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }

    # 1. Test recipes
    r1 = requests.get(f"{base_url}/api/recipes", headers=headers, params={"perPage": 1, "page": 1})
    recipes_json = r1.json() if r1.ok else {"error": r1.text}

    # 2. Test mealplans/today
    r2 = requests.get(f"{base_url}/api/households/mealplans/today", headers=headers)
    today_json = r2.json() if r2.ok else {"error": r2.text}

    return jsonify(
        {
            "recipes_response": recipes_json,
            "today_response": today_json,
        }
    )


"""
Endpoint para la estructura de documentos easy access
"""


@main_bp.route("/api/docs/structure")
def api_docs_structure():
    """
    Devuelve la estructura de carpetas y archivos PDF del NAS.
    Estructura esperada en disco: /BASE_PATH/Categoria/Archivo.pdf
    Salida JSON: {"Categoria": [{"name": "Archivo", "path": "/docs/Categoria/Archivo.pdf"}, ...]}
    """
    # 1. Obtener la ruta base desde la configuración
    docs_path = current_app.config.get("DOCS_BASE_PATH")

    if not docs_path:
        current_app.logger.error("DOCS_BASE_PATH no está definido en config.py o .env")
        return jsonify({"error": "Configuración incompleta: DOCS_BASE_PATH no definido"}), 500

    base = Path(docs_path)

    # 2. Validar existencia de la ruta (útil para detectar si el volumen de Docker falló)
    if not base.exists():
        current_app.logger.error(f"Ruta NAS no encontrada: {docs_path}")
        return jsonify(
            {
                "error": f"No se puede acceder a la carpeta de documentos ({docs_path}). Verifica el volumen en Docker."
            }
        ), 404

    structure = {}

    try:
        # 3. Iterar sobre las carpetas (Categorías)
        # Usamos sorted() para orden alfabético garantizado
        for folder in sorted(base.iterdir()):
            # Filtros de seguridad y limpieza:
            # - Debe ser directorio
            # - No debe ser carpeta oculta (ej: .DS_Store, @eaDir, .Recycle)
            if not folder.is_dir() or folder.name.startswith("."):
                continue

            folder_name = folder.name
            file_list = []

            # 4. Buscar archivos con múltiples extensiones dentro de la categoría (incluyendo subcarpetas)
            allowed_extensions = [
                "*.pdf",
                "*.jpg",
                "*.jpeg",
                "*.png",
                "*.txt",
                "*.webp",
                "*.heic",
                "*.heif",
            ]
            file_list = []

            for ext in allowed_extensions:
                for file in sorted(folder.rglob(ext)):
                    relative_path = file.relative_to(folder).as_posix()

                    # Ignorar artefactos del NAS/sistema (miniaturas, carpetas ocultas, etc.)
                    path_parts = file.relative_to(folder).parts
                    if any(part.startswith(".") or part.startswith("@") for part in path_parts):
                        continue

                    file_list.append(
                        {
                            "name": relative_path.rsplit(".", 1)[
                                0
                            ],  # incluye subcarpetas en el nombre visible
                            "filename": file.name,  # Ej: "Seguro Hogar.pdf"
                            "type": file.suffix.lower(),  # Ej: ".pdf", ".jpg", ".png", ".txt"
                            # Generamos la URL relativa que apuntará a tu ruta Flask de servir archivos
                            "path": f"/docs/{folder_name}/{relative_path}",
                        }
                    )

            # Solo añadimos la categoría si tiene archivos (opcional: quita el 'if' si quieres ver carpetas vacías)
            if file_list:
                structure[folder_name] = file_list

        return jsonify(structure)

    except PermissionError:
        current_app.logger.error(f"Permiso denegado al leer el NAS en: {base}")
        return jsonify(
            {"error": "Permiso denegado. Revisa permisos de lectura en el volumen Docker"}
        ), 403

    except Exception as e:
        current_app.logger.error(f"Error general leyendo estructura NAS: {e}")
        return jsonify({"error": "Error interno leyendo documentos"}), 500


@main_bp.route("/docs/<categoria>/<path:filename>")
def serve_document(categoria, filename):
    """Sirve el PDF desde el NAS"""

    # 1. Recuperar ruta base de la configuración
    docs_base_str = current_app.config.get("DOCS_BASE_PATH")

    if not docs_base_str:
        # Error de servidor si la config está mal
        abort(500, description="DOCS_BASE_PATH no configurado")

    # Convertimos a rutas absolutas (resolve) para seguridad
    base_path = Path(docs_base_str).resolve()

    # 2. Construir la ruta destino
    # Unimos paths y resolvemos para quitar posibles "../" que haya metido el usuario
    try:
        file_path = (base_path / categoria / filename).resolve()
    except Exception:
        # Si la ruta está mal formada
        abort(404)

    # 3. Validaciones de Seguridad (CRÍTICO)

    # A) Path Traversal: Asegurar que el archivo final sigue estando DENTRO de base_path
    # "base_path in file_path.parents" verifica que base_path es un ancestro
    if base_path not in file_path.parents:
        abort(403)  # Intento de hackeo o acceso fuera de carpeta

    # B) Solo formatos permitidos
    allowed_types = [".pdf", ".jpg", ".jpeg", ".png", ".txt"]
    if file_path.suffix.lower() not in allowed_types:
        abort(403)

    # C) Existencia
    if not file_path.exists() or not file_path.is_file():
        abort(404)

    # 4. Servir archivo con MIME type dinámico
    mime_types = {
        ".pdf": "application/pdf",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".txt": "text/plain",
    }
    mimetype = mime_types.get(file_path.suffix.lower(), "application/octet-stream")

    return send_file(
        file_path,
        mimetype=mimetype,
        as_attachment=False,  # False = Ver en navegador (inline)
        download_name=file_path.name,
    )


@main_bp.route("/api/menu-processor")
@cache.cached(timeout=60)
def api_menu_processor():
    """
    Health check del servicio Menu Processor
    """
    import requests

    menu_url = current_app.config.get("MENU_PROCESSOR_URL")
    if not menu_url:
        return jsonify({"error": "Menu Processor no configurado"}), 500

    try:
        response = requests.get(f"{menu_url}/api/health", timeout=5)
        if response.ok:
            return jsonify({"status": "ok", "service": "menu-processor"})
        return jsonify({"error": f"HTTP {response.status_code}"}), 500
    except requests.RequestException as e:
        current_app.logger.error(f"Menu Processor health check failed: {e}")
        return jsonify({"error": str(e)}), 500


@main_bp.route("/api/dnscrypt")
@cache.cached(timeout=60)
def api_dnscrypt():
    """
    Health check de DNSCrypt-proxy via consulta DNS
    """
    import socket

    dnscrypt_ip = current_app.config.get("DNSCRYPT_IP", "127.0.0.1")
    dnscrypt_port = current_app.config.get("DNSCRYPT_PORT", 5053)

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(3)
        query = b"\x00\x01\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x06google\x03com\x00\x00\x01\x00\x01"
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


# Filtros de template
@main_bp.app_template_filter("datetime_format")
def datetime_format(value, format="%d/%m/%Y %H:%M"):
    if value is None:
        return ""
    return value.strftime(format)


@main_bp.app_template_filter("currency")
def currency_format(value):
    return f"€ {value:,.2f}"
