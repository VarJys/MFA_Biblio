from flask import Flask, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Debes iniciar sesión para acceder."

    from app.routes.auth import auth_bp
    from app.routes.prestamos import prestamos_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(prestamos_bp)
    app.register_blueprint(admin_bp)

    with app.app_context():
        from app import models
        from app.modules import audit
        db.create_all()

    # Ruta raíz
    @app.route("/")
    def index():
        return redirect(url_for("auth.elegir_portal"))

    # Manejadores de error
    @app.errorhandler(404)
    def pagina_no_encontrada(e):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def error_interno(e):
        return render_template("500.html"), 500

    return app