import os
from dotenv import load_dotenv

load_dotenv()

# Ruta absoluta a la raíz del proyecto
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-cambiar-en-produccion")

    # Ruta absoluta a la BD — evita errores de directorio relativo
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'biblioauth.db')}"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    MAIL_SERVER   = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT     = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS  = True
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
    MAIL_SENDER   = os.environ.get("MAIL_SENDER", "biblioauth@universidad.edu.co")

    OTP_EXPIRY_MINUTES = 5
    MAX_OTP_ATTEMPTS   = 3