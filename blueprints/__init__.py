"""
Blueprints Package - Registro centralizado de todos los blueprints
"""


def register_blueprints(app):
    """Registra todos los blueprints en la aplicación Flask."""
    from blueprints.dashboard import dashboard_bp
    from blueprints.api.weather import weather_bp
    from blueprints.api.pihole import pihole_bp
    from blueprints.api.mealie import mealie_bp
    from blueprints.api.energy import energy_bp
    from blueprints.api.settleup import settleup_bp
    from blueprints.api.shopping import shopping_bp
    from blueprints.api.documents import documents_bp
    from blueprints.api.services import services_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(weather_bp)
    app.register_blueprint(pihole_bp)
    app.register_blueprint(mealie_bp)
    app.register_blueprint(energy_bp)
    app.register_blueprint(settleup_bp)
    app.register_blueprint(shopping_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(services_bp)
