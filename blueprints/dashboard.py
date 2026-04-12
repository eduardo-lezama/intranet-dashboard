"""
Dashboard Blueprint - Rutas de renderizado de páginas
"""

from datetime import datetime

from flask import Blueprint, render_template

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def index():
    """Página principal del dashboard."""
    context = {"current_time": datetime.now(), "page_title": "Dashboard"}
    return render_template("dashboard.html", **context)


@dashboard_bp.route("/finanzas")
def finanzas():
    """Página de finanzas."""
    context = {
        "page_title": "Finanzas",
        "balance": 0.0,
        "gastos_mes": 0.0,
        "ahorros": 0.0,
    }
    return render_template("finanzas.html", **context)


# Template filters
@dashboard_bp.app_template_filter("datetime_format")
def datetime_format(value, format="%d/%m/%Y %H:%M"):
    if value is None:
        return ""
    return value.strftime(format)


@dashboard_bp.app_template_filter("currency")
def currency_format(value):
    return f"€ {value:,.2f}"
