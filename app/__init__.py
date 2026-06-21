from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config

# Instancia global de la base de datos
# Se inicializa aquí pero se asocia a la app en create_app()
db = SQLAlchemy()

# Instancia global del manejador de sesiones de login
login_manager = LoginManager()

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)

    # Asociar extensiones a la app
    db.init_app(app)
    login_manager.init_app(app)

    # Redirigir a login si el usuario no está autenticado
    login_manager.login_view = "auth.elegir_portal"
    login_manager.login_message = "Debes iniciar sesión para acceder."

    # Registrar blueprints (rutas de la aplicación)
    from app.routes.auth import auth_bp
    from app.routes.prestamos import prestamos_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(prestamos_bp)
    app.register_blueprint(admin_bp)

    # Crear las tablas de la BD si no existen
    with app.app_context():
        # Importar modelos para que SQLAlchemy los reconozca
        from app import models
        db.create_all()

    return app