"""
API SettleUp - Finanzas compartidas via Firebase/SettleUp
"""

from flask import Blueprint, current_app, jsonify

from blueprints.settleup_client import SettleUpClient
from cache import cache

settleup_bp = Blueprint("api_settleup", __name__)


def _get_settleup_config():
    """Obtener y validar configuración de SettleUp."""
    email = current_app.config.get("SETTLEUP_EMAIL")
    password = current_app.config.get("SETTLEUP_PASSWORD")
    group_id = current_app.config.get("SETTLEUP_GROUP_ID")
    api_key = current_app.config.get("SETTLEUP_API_KEY")
    env = current_app.config.get("SETTLEUP_ENV", "sandbox")

    if not all([email, password, group_id, api_key]):
        return None

    return {
        "email": email,
        "password": password,
        "group_id": group_id,
        "api_key": api_key,
        "env": env,
    }


@settleup_bp.route("/api/settleup")
@cache.cached(timeout=900)
def api_settleup():
    """Visión general del grupo - balance y gastos del mes."""
    config = _get_settleup_config()
    if not config:
        return jsonify({
            "error": "Configuración incompleta",
            "required": [
                "SETTLEUP_EMAIL", "SETTLEUP_PASSWORD",
                "SETTLEUP_GROUP_ID", "SETTLEUP_API_KEY",
            ],
        }), 500

    try:
        client = SettleUpClient(**config)
        balance_data = client.calculate_group_balance()
        members = balance_data["members"]
        balances = balance_data["balances"]

        monthly_expenses = client.get_monthly_expenses()

        sorted_members = sorted(balances.items(), key=lambda x: x[1])
        debtor_id, debtor_balance = sorted_members[0]
        creditor_id, creditor_balance = sorted_members[-1]

        if abs(debtor_balance) < 0.01 and abs(creditor_balance) < 0.01:
            status = "Todo equilibrado ✅"
            main_amount = 0.0
            debtor_name = creditor_name = None
        else:
            main_amount = min(abs(debtor_balance), abs(creditor_balance))
            debtor_name = members[debtor_id]
            creditor_name = members[creditor_id]
            status = f"{debtor_name} debe €{main_amount:.2f} a {creditor_name}"

        return jsonify({
            "status": status,
            "monthly_expenses": monthly_expenses,
            "main_debt_amount": round(main_amount, 2),
            "debtor": debtor_name,
            "creditor": creditor_name,
            "balances": {members[mid]: round(bal, 2) for mid, bal in balances.items()},
        })

    except Exception as e:
        current_app.logger.error(f"Error Settle Up: {e}")
        return jsonify({"error": str(e)}), 500


@settleup_bp.route("/api/settleup/debug-transactions")
def api_settleup_debug_transactions():
    """Debug: ver transacciones raw de SettleUp."""
    config = _get_settleup_config()
    if not config:
        return jsonify({"error": "Config incompleta"}), 500

    client = SettleUpClient(**config)
    txs = client.get_group_entries()
    return jsonify(txs)
